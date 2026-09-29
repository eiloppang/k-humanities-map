# -*- coding: utf-8 -*-
"""Stage 1b: 고유 cretId -> kri_num 수확 (KCI 로그인 세션).

cretId 집합 = 단일저자 crt_id(pkl) ∪ 다저자 전 저자 cret(_paper_crets.jsonl).
각 cretId 는 등장 article_id 하나와 짝지어 poCretDetail 조회 →
fncArtiSelectCitationIdx('<cret>','<kri_num>') 에서 kri_num 추출.

세션 견고화:
  - 연구자 페이지엔 항상 본인 H지수 onclick(fncArtiSelectCitationIdx)이 있으므로,
    pairs 가 0이면 = 로그아웃(또는 깨짐)으로 판정.
  - generation 가드: 세션 만료 시 여러 스레드가 동시에 감지해도 '재로그인 1회'만 수행
    (이미 갱신됐으면 그냥 재시도). 쿠키 헝클임/중복 Selenium 로그인 방지.
  - 재개: 캐시의 '성공(ok:true)'만 완료로 처리 → 실패건은 재실행 시 재시도.

사용: python KRI/harvest_krinum.py [--limit N]
"""
import sys, io, os, re, json, time, threading, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd, httpx, urllib3
from tqdm import tqdm
_CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # Scraping-Code
sys.path.insert(0, _CODE)
sys.path.insert(0, os.path.join(_CODE, "kci"))                         # scrape_korlit (KCI 로그인 재사용)
import config
import scrape_korlit as sk
D = config.ACTIVE
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
CRET = BASE + "/kciportal/po/citationindex/poCretDetail.kci?citationBean.cretId={crt}&citationBean.artiId={art}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PKL = D.pkl
PAPER_CRETS = D.paper_crets
CACHE = D.krinum_cache
WORKERS, RETRIES, TIMEOUT = 6, 5, 60
pat = re.compile(r"fncArtiSelectCitationIdx\('(CRT\d+)','(\d+)'")
_write_lock = threading.Lock()


class Session:
    """공유 httpx 클라이언트 + generation 가드 재로그인."""
    def __init__(self):
        self.client = httpx.Client(verify=False, headers=HEADERS,
                                   follow_redirects=True, timeout=TIMEOUT)
        self.gen = 0
        self.lock = threading.Lock()
        self._login()

    def _login(self):
        cookies = sk.selenium_login()
        self.client.cookies.clear()
        for k, v in cookies.items():
            self.client.cookies.set(k, v, domain="www.kci.go.kr")

    def relogin_if_stale(self, seen_gen):
        """이 스레드가 본 generation 이후 아무도 재로그인 안 했으면 1회 재로그인."""
        with self.lock:
            if self.gen == seen_gen:
                tqdm.write(f"  [세션 만료 감지 gen{self.gen}] 재로그인...")
                self._login()
                self.gen += 1
                tqdm.write(f"  [재로그인 완료 -> gen{self.gen}]")
            return self.gen


def build_cret_article_map():
    df = pd.read_pickle(PKL)
    m = {}
    for r in df.itertuples(index=False):
        c = str(r.crt_id)
        if c.startswith("CRT") and c not in m:
            m[c] = r.article_id
    if os.path.exists(PAPER_CRETS):
        for line in open(PAPER_CRETS, encoding="utf-8"):
            try: rec = json.loads(line)
            except Exception: continue
            for c in rec.get("crets", []):
                if c not in m:
                    m[c] = rec["article_id"]
    return m


def load_done():
    """종결(ok:true) cret 만 완료로 간주: 성공(kri_num) + no_kri(kri 없는 연구자).
    진짜 오류(ok:false)만 재시도 대상으로 남긴다."""
    done = set()
    if os.path.exists(CACHE):
        for line in open(CACHE, encoding="utf-8"):
            try: r = json.loads(line)
            except Exception: continue
            if r.get("ok"):
                done.add(r["cret"])
    return done


def append(rec):
    with _write_lock:
        with open(CACHE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


LOGOUT_SIZE = 30000   # 로그아웃 셸 ~11KB vs 정상 페이지 ~60KB

def harvest(sess, cret, art):
    for i in range(RETRIES):
        gen = sess.gen
        try:
            html = sess.client.get(CRET.format(crt=cret, art=art), timeout=TIMEOUT).text
            if len(html) < LOGOUT_SIZE:                 # 로그아웃 셸 → 재로그인 후 재시도
                sess.relogin_if_stale(gen)
                time.sleep(0.3)
                continue
            pairs = pat.findall(html)
            if pairs:                                   # 성공: H지수 onclick 에서 kri_num
                kri = next((k for c, k in pairs if c == cret), pairs[0][1])
                return {"cret": cret, "kri_num": kri, "ok": True, "status": "ok"}
            # 정상 페이지인데 onclick 없음 = kri_num 미보유 연구자 (재시도 안 함)
            return {"cret": cret, "kri_num": None, "ok": True, "status": "no_kri"}
        except Exception:
            pass
        time.sleep(0.6 + i)
    return {"cret": cret, "kri_num": None, "ok": False, "status": "error"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    cmap = build_cret_article_map()
    print(f"고유 cretId: {len(cmap):,}")
    done = load_done()
    todo = [(c, a) for c, a in cmap.items() if c not in done]
    if args.limit: todo = todo[:args.limit]
    print(f"성공 완료 {len(done):,} / 이번 처리(미완+재시도) {len(todo):,}")
    if not todo:
        print("처리할 항목 없음."); return

    print("KCI 로그인...")
    sess = Session()
    got = nokri = err = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(harvest, sess, c, a): c for c, a in todo}
        bar = tqdm(total=len(todo), desc="kri_num", unit="건", smoothing=0.05)
        for fut in as_completed(futs):
            rec = fut.result(); append(rec)
            st = rec.get("status")
            if st == "ok": got += 1
            elif st == "no_kri": nokri += 1
            else: err += 1
            bar.set_postfix_str(f"kri {got} no_kri {nokri} err {err} gen{sess.gen}"); bar.update(1)
        bar.close()
    sess.client.close()
    print(f"완료: kri_num {got:,} / no_kri {nokri:,} / 오류 {err:,} / 재로그인 {sess.gen}회")

if __name__ == "__main__":
    main()
