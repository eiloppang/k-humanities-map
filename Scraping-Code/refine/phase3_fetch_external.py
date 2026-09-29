# -*- coding: utf-8 -*-
"""Phase 3: 외부 art_id 의 저널/발행기관을 KCI 상세페이지에서 조회 (로그인 불필요).

- 입력 : 문제점/_external_artids.txt  (고유 외부 art_id)
- 캐시 : 문제점/_external_cache.jsonl (art_id 당 1줄, 재개 가능)
- 멀티스레드 + 재시도 + 페이지간 소폭 지연으로 KCI 부하 완화

사용:
  python 문제점/phase3_fetch_external.py --limit 30   # 스모크
  python 문제점/phase3_fetch_external.py               # 전체(재개)
"""
import sys, io, os, re, json, time, threading, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx, urllib3
from bs4 import BeautifulSoup
from tqdm import tqdm

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
D = config.ACTIVE

BASE = "https://www.kci.go.kr"
ARTI_VIEW = BASE + "/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId="
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
WORKLIST = D.ext_worklist
CACHE = D.ext_cache
WORKERS = 8
RETRIES = 4
TIMEOUT = 60

def clean(s): return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()
def meta(soup, n):
    el = soup.find("meta", attrs={"name": n}); return clean(el["content"]) if el and el.get("content") else ""

_lock = threading.Lock()

def load_done():
    done = set()
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            for line in f:
                try: done.add(json.loads(line)["art_id"])
                except Exception: pass
    return done

def append(rec):
    with _lock:
        with open(CACHE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def fetch(client, aid):
    last = None
    for i in range(RETRIES):
        try:
            r = client.get(ARTI_VIEW + aid, timeout=TIMEOUT)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                pj = soup.find("p", class_="jounal")     # KCI 오타: jounal
                pp = soup.find("p", class_="pub")
                return {
                    "art_id": aid, "ok": True,
                    "journal_ko": clean(pj.get_text()) if pj else "",
                    "journal_en": meta(soup, "citation_journal_title"),
                    "publisher_ko": clean(re.sub(r"^발행기관\s*:?\s*", "", pp.get_text())) if pp else "",
                    "publisher_en": meta(soup, "citation_publisher"),
                    "pub_year": meta(soup, "citation_publication_date"),
                }
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = repr(e)
        time.sleep(1.0 + i)
    return {"art_id": aid, "ok": False, "err": last}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="처음 N개만(스모크)")
    args = ap.parse_args()

    ids = [l.strip() for l in open(WORKLIST, encoding="utf-8") if l.strip()]
    done = load_done()
    todo = [a for a in ids if a not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"전체 {len(ids):,} / 완료 {len(done):,} / 이번 처리 {len(todo):,}")
    if not todo:
        print("처리할 항목 없음 (전부 캐시됨).")
        return

    client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=TIMEOUT)
    t0 = time.time(); ok = fail = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, client, a): a for a in todo}
        bar = tqdm(total=len(todo), desc="외부조회", unit="건", smoothing=0.05)
        for fut in as_completed(futs):
            rec = fut.result()
            append(rec)
            if rec["ok"]: ok += 1
            else: fail += 1
            bar.set_postfix_str(f"ok {ok} fail {fail}")
            bar.update(1)
        bar.close()
    client.close()
    dt = time.time() - t0
    print(f"\n완료: ok {ok:,} / fail {fail:,} / {dt:.0f}s "
          f"({len(todo)/dt:.1f}건/s)" if dt else "")

if __name__ == "__main__":
    main()
