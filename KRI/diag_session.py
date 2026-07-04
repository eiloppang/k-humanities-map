# -*- coding: utf-8 -*-
"""세션 진단: 단일 로그인 후 (이전 성공 cret) vs (지금 실패 cret) 페이지 비교."""
import sys, io, re, json, httpx, urllib3
sys.path.insert(0, ".")
import scrape_korlit as sk
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
CRET = BASE + "/kciportal/po/citationindex/poCretDetail.kci?citationBean.cretId={crt}&citationBean.artiId={art}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
pat = re.compile(r"fncArtiSelectCitationIdx\('(CRT\d+)','(\d+)'")

import pandas as pd
df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
art_of = {}
for r in df.itertuples(index=False):
    c = str(r.crt_id)
    if c.startswith("CRT"): art_of.setdefault(c, r.article_id)

# 이전 성공 cret (캐시 ok:true 첫 건)
succ = None
for l in open("KRI/_krinum_cache.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if r.get("ok") and r.get("kri_num"): succ = r["cret"]; break
# 지금 실패 cret (캐시 ok:false 첫 건)
failc = None
for l in open("KRI/_krinum_cache.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if not r.get("ok"): failc = r["cret"]; break

print("이전 성공 cret:", succ, "| 실패 cret:", failc)
print("로그인...")
cookies = sk.selenium_login()
print("쿠키:", list(cookies.keys()))
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for k, v in cookies.items(): client.cookies.set(k, v, domain="www.kci.go.kr")

for label, cret in [("이전성공", succ), ("실패", failc)]:
    art = art_of.get(cret, "ART003131535")
    html = client.get(CRET.format(crt=cret, art=art)).text
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    pairs = pat.findall(html)
    print(f"\n=== [{label}] cret={cret} art={art} ===")
    print(f"  bytes={len(html):,} | title={title[:50]}")
    print(f"  fncArtiSelectCitationIdx 쌍: {pairs[:3]}")
    print(f"  'loginForm' 포함: {'loginForm' in html} | '로그인' 포함: {'로그인' in html}")
    print(f"  '차단'/'제한'/'오류' 포함: {any(w in html for w in ['차단','제한','일시','오류','blocked'])}")
client.close()
