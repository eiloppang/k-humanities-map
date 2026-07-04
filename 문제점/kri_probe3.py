# -*- coding: utf-8 -*-
"""poCretDetail.kci (인용보고서/연구자 페이지)에서 kri_num 추출 검증.
우리 crt_id + article_id 로 직접 접근."""
import sys, io, re, pandas as pd, httpx, urllib3
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
CRET = BASE + "/kciportal/po/citationindex/poCretDetail.kci?citationBean.cretId={crt}&citationBean.artiId={art}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
samp = df[(df.authors_ko.map(len) == 1) & (df.crt_id.astype(str).str.startswith("CRT"))].head(4)

pat = re.compile(r"fncArtiSelectCitationIdx\('(CRT\d+)','(\d+)'")
patreg = re.compile(r"RschrRegNo['\"=]+(\d+)")
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for r in samp.itertuples(index=False):
    url = CRET.format(crt=r.crt_id, art=r.article_id)
    html = client.get(url).text
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    pairs = pat.findall(html)
    regs = patreg.findall(html)
    print(f"\n=== {r.article_id} | crt_id={r.crt_id} | 저자={r.authors_ko} ===")
    print(f"  URL: {url}")
    print(f"  page title: {title[:50]} | bytes: {len(html):,}")
    print(f"  fncArtiSelectCitationIdx 쌍: {pairs[:4]}")
    print(f"  RschrRegNo 숫자: {regs[:4]}")
    kri = None
    for c, k in pairs:
        if c == r.crt_id: kri = k
    print(f"  >> 우리 crt_id 매칭 kri_num: {kri or (regs[0] if regs else '미발견')}")
client.close()
