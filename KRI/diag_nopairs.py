# -*- coding: utf-8 -*-
"""onclick 없는(60KB) 실패 페이지에서 kri_num 단서 탐색."""
import sys, io, re, json, httpx, urllib3, pandas as pd
sys.path.insert(0, ".")
import scrape_korlit as sk
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
CRET = BASE + "/kciportal/po/citationindex/poCretDetail.kci?citationBean.cretId={crt}&citationBean.artiId={art}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
art_of = {str(r.crt_id): r.article_id for r in df.itertuples(index=False) if str(r.crt_id).startswith("CRT")}

# 실패 cret 3개
fails = []
for l in open("KRI/_krinum_cache.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if not r.get("ok"): fails.append(r["cret"])
    if len(fails) >= 3: break

print("로그인..."); cookies = sk.selenium_login()
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for k, v in cookies.items(): client.cookies.set(k, v, domain="www.kci.go.kr")

cret = fails[0]; art = art_of.get(cret, "")
html = client.get(CRET.format(crt=cret, art=art)).text
open("KRI/_nopairs_dump.html", "w", encoding="utf-8").write(html)
print(f"cret={cret} art={art} bytes={len(html):,} -> KRI/_nopairs_dump.html\n")

# 단서 탐색
for kw in ["fncArti", "RschrRegNo", "rschrRegNo", "cretId", "fncCret", "fnc", "H지수", "연구자", "동명", "정보가 없", "검색되지", "비공개", "미등록"]:
    cnt = html.count(kw)
    if cnt:
        i = html.find(kw); s = max(0, i-60)
        print(f"[{kw}] {cnt}회: ...{re.sub(chr(10),' ',html[s:i+90])}...")
    else:
        print(f"[{kw}] 없음")

# 모든 fnc 함수 호출 패턴
print("\n=== onclick fnc 호출 패턴(상위) ===")
for m in sorted(set(re.findall(r"(fnc\w+\([^)]{0,40}\))", html)))[:15]:
    print("  ", m)
client.close()
