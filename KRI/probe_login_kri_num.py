# -*- coding: utf-8 -*-
"""KCI 로그인 세션으로 poCretDetail(연구자정보) 페이지를 받아 crt_id -> kri_num 추출 검증.
우리 데이터의 crt_id + article_id 사용. (KCI 로그인 = scrape_korlit.selenium_login 재사용)
"""
import sys, io, re, pandas as pd, httpx, urllib3
from bs4 import BeautifulSoup
sys.path.insert(0, ".")
import scrape_korlit as sk
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
CRET = BASE + "/kciportal/po/citationindex/poCretDetail.kci?citationBean.cretId={crt}&citationBean.artiId={art}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
samp = df[(df.authors_ko.map(len) == 1) & (df.crt_id.astype(str).str.startswith("CRT"))].head(4)

print("[1] KCI 로그인...")
cookies = sk.selenium_login()
print("  쿠키:", list(cookies.keys()))

client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for k, v in cookies.items():
    client.cookies.set(k, v, domain="www.kci.go.kr")

pat = re.compile(r"fncArtiSelectCitationIdx\('(CRT\d+)','(\d+)'")
print("\n[2] poCretDetail 조회")
for r in samp.itertuples(index=False):
    html = client.get(CRET.format(crt=r.crt_id, art=r.article_id)).text
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    pairs = pat.findall(html)
    kri = next((k for c, k in pairs if c == r.crt_id), None)
    print(f"\n  {r.article_id} | crt_id={r.crt_id} | 저자={r.authors_ko}")
    print(f"    bytes={len(html):,} title={title[:40]}")
    print(f"    fncArtiSelectCitationIdx 쌍: {pairs[:4]}")
    print(f"    >> 우리 crt_id 매칭 kri_num: {kri or '미발견'}")
client.close()
