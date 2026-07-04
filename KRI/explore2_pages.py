# -*- coding: utf-8 -*-
"""로그인된 프로파일로 연구자 직접 URL 후보들을 열어 7개 필드 위치 탐색."""
import sys, io, os, re, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROFILE = os.path.abspath("KRI/_chrome_profile")
FIELDS = ["성명", "성별", "소속", "직급", "전공", "출신", "학위", "생년", "국가연구자번호", "연구자번호"]

def sample_kris(n=2):
    ks = []
    for l in open("KRI/_krinum_cache.jsonl", encoding="utf-8"):
        r = json.loads(l)
        if r.get("ok") and r.get("kri_num"):
            ks.append(r["kri_num"])
        if len(ks) >= n: break
    return ks

kri = sample_kris(1)[0]
print("탐색 kri_num:", kri)

CANDS = [
    f"/kri/rp/rschachv/PG-RP-108-01jl.jsp?txtRschrRegNo={kri}",
    f"/kri/rp/rschachv/PG-RP-101-01jl.jsp?txtRschrRegNo={kri}",
    f"/kri/rp/rschachv/PG-RP-102-02jr.jsp?txtRschrRegNo={kri}",
    f"/kri/rp/rschachv/PG-RP-103-01jl.jsp?txtRschrRegNo={kri}",
]

opts = Options()
opts.add_argument(f"--user-data-dir={PROFILE}")
opts.add_argument("--window-size=1400,1000")
opts.add_argument("--log-level=3")
opts.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Chrome(options=opts)

BASE = "https://www.kri.go.kr"
for path in CANDS:
    try:
        driver.get(BASE + path)
        time.sleep(4)
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else ""
        present = [f for f in FIELDS if f in html]
        tds = [td.get_text(strip=True) for td in soup.find_all("td") if td.get_text(strip=True)]
        fname = "KRI/_dump_" + re.search(r"PG-RP-[\w-]+", path).group() + ".html"
        open(fname, "w", encoding="utf-8").write(html)
        print(f"\n=== {path} ===")
        print(f"  title={title[:45]} | bytes={len(html):,} | td(텍스트)={len(tds)}")
        print(f"  필드라벨 존재: {present}")
        print(f"  td 샘플(앞15): {tds[:15]}")
        print(f"  저장: {fname}")
    except Exception as e:
        print(f"\n=== {path} ===\n  실패: {e}")

print("\n>> 완료. 브라우저 종료(세션은 프로파일에 보존).")
driver.quit()
