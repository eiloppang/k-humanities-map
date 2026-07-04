# -*- coding: utf-8 -*-
"""다저자 논문 article 페이지의 div.author 에서 모든 저자 cretId 추출되는지 검증 (로그인 불필요)."""
import sys, io, re, pandas as pd, httpx, urllib3
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
ARTI_VIEW = BASE + "/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId="
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
samp = df[df.authors_ko.map(len) >= 3].head(3)   # 저자 3명 이상

cret_pat = re.compile(r"citationBean\.cretId=(CRT\d+)")
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for r in samp.itertuples(index=False):
    html = client.get(ARTI_VIEW + r.article_id).text
    soup = BeautifulSoup(html, "lxml")
    adiv = soup.find("div", class_="author")
    crets, names = [], []
    if adiv:
        for a in adiv.find_all("a", href=re.compile("poCretDetail")):
            m = cret_pat.search(a["href"])
            if m:
                crets.append(m.group(1)); names.append(a.get_text(strip=True))
    print(f"\n=== {r.article_id} | 저자수={len(r.authors_ko)} | 우리 crt_id={r.crt_id} ===")
    print(f"  authors_ko: {r.authors_ko}")
    print(f"  div.author cretId: {crets}")
    print(f"  링크 저자명: {names}")
    print(f"  우리 crt_id 포함? {r.crt_id in crets}")
client.close()
