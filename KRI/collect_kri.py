# -*- coding: utf-8 -*-
"""Stage 2 본수집: 고유 연구자(unique_kri.txt)의 7개 필드를 PG-RP-102 에서 httpx 병렬 수집.

- 프로파일 세션 쿠키로 httpx 병렬(로그인 1회로 충분, 2FA 불필요)
- 공개: 성명행 파싱 → 7필드. 비공개: 성명행 없음+비공개 마커 → status=private.
- 캐시/재개: KRI/_kri_cache.jsonl (kri 당 1줄). 세션오류만 재시도 대상.

사용: python KRI/collect_kri.py [--limit N]
"""
import sys, io, os, re, json, time, threading, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx, urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

PROFILE = os.path.abspath("KRI/_chrome_profile")
BASE = "https://www.kri.go.kr"
URL = BASE + "/kri/rp/rschachv/PG-RP-102-02jr.jsp?txtRschrRegNo={kri}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
WORKLIST = "KRI/unique_kri.txt"
CACHE = "KRI/_kri_cache.jsonl"
WORKERS, RETRIES, TIMEOUT = 8, 4, 60

LABELS = {
    "한글": "성명", "한자": "성명_한자", "영문": "성명_영문",
    "성별": "성별", "출생년도": "출생년도",
    "기관": "소속대학기관", "직급": "직급", "재직여부": "재직여부",
    "연구분야": "전공분야", "세부전공명": "세부전공명",
    "취득학위": "취득학위", "수여대학": "출신학교_학위수여대학",
}
KNOWN = set(LABELS)
_lock = threading.Lock()

def get_cookies():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE}")
    opts.add_argument("--headless=new")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    d = webdriver.Chrome(options=opts)
    d.get(BASE + "/kri2"); time.sleep(2)
    ck = {c["name"]: c["value"] for c in d.get_cookies()}
    d.quit()
    return ck

def extract(html):
    soup = BeautifulSoup(html, "lxml")
    cells = [c.get_text(" ", strip=True) for c in soup.find_all(["th", "td"])]
    out = {}
    for i, t in enumerate(cells):
        if t in LABELS and i + 1 < len(cells):
            nxt = cells[i + 1]
            out[LABELS[t]] = "" if nxt in KNOWN else nxt
    return out

def load_done():
    done = set()
    if os.path.exists(CACHE):
        for l in open(CACHE, encoding="utf-8"):
            try: r = json.loads(l)
            except Exception: continue
            if r.get("status") in ("ok", "private"):
                done.add(r["kri_num"])
    return done

def append(rec):
    with _lock:
        with open(CACHE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def fetch(client, kri):
    for i in range(RETRIES):
        try:
            html = client.get(URL.format(kri=kri), timeout=TIMEOUT).text
            if "성명" in html and "한글" in html:           # 공개: 데이터 존재
                d = extract(html)
                if d.get("성명"):
                    d.update({"kri_num": kri, "status": "ok"})
                    return d
            if "비공개" in html or "볼수없" in html:          # 비공개 마커
                return {"kri_num": kri, "status": "private"}
        except Exception:
            pass
        time.sleep(0.6 + i)
    return {"kri_num": kri, "status": "error"}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    kris = [l.strip() for l in open(WORKLIST, encoding="utf-8") if l.strip()]
    done = load_done()
    todo = [k for k in kris if k not in done]
    if args.limit: todo = todo[:args.limit]
    print(f"전체 {len(kris):,} / 완료 {len(done):,} / 이번 {len(todo):,}")
    if not todo: print("처리할 항목 없음."); return

    print("쿠키 추출(프로파일 세션)...")
    ck = get_cookies(); print("쿠키:", list(ck.keys()))
    client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=TIMEOUT)
    for k, v in ck.items(): client.cookies.set(k, v, domain="www.kri.go.kr")

    ok = priv = err = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, client, k): k for k in todo}
        bar = tqdm(total=len(todo), desc="KRI수집", unit="명", smoothing=0.05)
        for fut in as_completed(futs):
            rec = fut.result(); append(rec)
            st = rec["status"]
            ok += st == "ok"; priv += st == "private"; err += st == "error"
            bar.set_postfix_str(f"ok {ok} priv {priv} err {err}"); bar.update(1)
        bar.close()
    client.close()
    print(f"완료: ok {ok:,} / 비공개 {priv:,} / 오류 {err:,}")

if __name__ == "__main__":
    main()
