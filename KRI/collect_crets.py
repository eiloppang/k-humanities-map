# -*- coding: utf-8 -*-
"""Stage 1a: 다저자 논문 article 페이지에서 전 저자 cretId 수집 (로그인 불필요).

단일저자 논문은 우리 데이터의 crt_id 가 곧 유일 저자의 cretId 이므로 조회 불필요.
다저자(>=2) 논문만 article 페이지를 받아 div.author 의 cretId 를 순서대로 추출.

출력: KRI/_paper_crets.jsonl  (article_id 당 1줄, 재개 가능)
      {article_id, authors_ko, crets:[CRT..., ...]}
"""
import sys, io, os, re, json, time, threading, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd, httpx, urllib3
from bs4 import BeautifulSoup
from tqdm import tqdm
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
ARTI_VIEW = BASE + "/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId="
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PKL = "Data/한국어와문학_결과2/korlit_2008_2024.pkl"
OUT = "KRI/_paper_crets.jsonl"
WORKERS, RETRIES, TIMEOUT = 8, 4, 60
cret_pat = re.compile(r"citationBean\.cretId=(CRT\d+)")
_lock = threading.Lock()

def load_done():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(line)["article_id"])
            except Exception: pass
    return done

def append(rec):
    with _lock:
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def fetch(client, art, authors):
    for i in range(RETRIES):
        try:
            r = client.get(ARTI_VIEW + art, timeout=TIMEOUT)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                adiv = soup.find("div", class_="author")
                crets = []
                if adiv:
                    for a in adiv.find_all("a", href=re.compile("poCretDetail")):
                        m = cret_pat.search(a["href"])
                        if m and m.group(1) not in crets:
                            crets.append(m.group(1))
                return {"article_id": art, "authors_ko": authors, "crets": crets, "ok": True}
        except Exception:
            pass
        time.sleep(1.0 + i)
    return {"article_id": art, "authors_ko": authors, "crets": [], "ok": False}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    df = pd.read_pickle(PKL)
    multi = df[df.authors_ko.map(len) >= 2][["article_id", "authors_ko"]]
    done = load_done()
    todo = [(r.article_id, list(r.authors_ko)) for r in multi.itertuples(index=False)
            if r.article_id not in done]
    if args.limit: todo = todo[:args.limit]
    print(f"다저자 논문 {len(multi):,} / 완료 {len(done):,} / 이번 {len(todo):,}")
    if not todo: print("처리할 항목 없음."); return
    client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=TIMEOUT)
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, client, a, au): a for a, au in todo}
        bar = tqdm(total=len(todo), desc="공저자cret", unit="건", smoothing=0.05)
        for fut in as_completed(futs):
            rec = fut.result(); append(rec)
            ok += rec["ok"]; fail += (not rec["ok"])
            bar.set_postfix_str(f"ok {ok} fail {fail}"); bar.update(1)
        bar.close()
    client.close()
    print(f"완료: ok {ok:,} / fail {fail:,}")

if __name__ == "__main__":
    main()
