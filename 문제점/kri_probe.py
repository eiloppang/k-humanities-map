# -*- coding: utf-8 -*-
"""우리 데이터의 crt_id -> kri_num 매핑 경로 검증.
단일저자 논문 몇 개의 KCI 상세페이지를 받아 fncArtiSelectCitationIdx(CRT, kri) 패턴을 찾고,
우리 데이터의 crt_id 와 대조한다. (로그인 불필요)
"""
import sys, io, re, pandas as pd, httpx, urllib3
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
ARTI_VIEW = BASE + "/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId="
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
# 단일저자 + crt_id 있는 논문 5개
samp = df[(df.authors_ko.map(len) == 1) & (df.crt_id.astype(str).str.startswith("CRT"))].head(5)

pat = re.compile(r"fncArtiSelectCitationIdx\('(CRT\d+)','(\d+)'")
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for r in samp.itertuples(index=False):
    html = client.get(ARTI_VIEW + r.article_id).text
    pairs = pat.findall(html)
    has_fnc = "fncArtiSelectCitationIdx" in html
    has_reg = "RschrRegNo" in html
    print(f"\n=== {r.article_id} | 우리 crt_id={r.crt_id} | 저자={r.authors_ko} ===")
    print(f"  페이지에 fncArtiSelectCitationIdx: {has_fnc} | RschrRegNo 문자열: {has_reg}")
    print(f"  추출된 (crtId, kri_num) 쌍: {pairs[:6]}")
    if pairs:
        match = [k for c, k in pairs if c == r.crt_id]
        print(f"  >> 우리 crt_id 와 일치하는 kri_num: {match if match else '없음(불일치)'}")
client.close()
