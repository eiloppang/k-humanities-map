# -*- coding: utf-8 -*-
"""article 페이지에서 cret/citation 관련 링크·함수를 모두 추출해 연구자페이지 경로 파악."""
import sys, io, re, pandas as pd, httpx, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
ARTI_VIEW = BASE + "/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId="
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
r = df[(df.authors_ko.map(len) == 1) & (df.crt_id.astype(str).str.startswith("CRT"))].iloc[0]
print(f"art={r.article_id} crt_id={r.crt_id} 저자={r.authors_ko}\n")

client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
html = client.get(ARTI_VIEW + r.article_id).text
client.close()

# cret 관련 토큰 주변 추출
for kw in ["cretId", "Cret", "citationBean", "Citation", "RschrRegNo", "rschr", "Rschr", "kri", "author", "authViewPop", "MemberView"]:
    idxs = [m.start() for m in re.finditer(re.escape(kw), html)]
    if idxs:
        print(f"[{kw}] {len(idxs)}회 — 첫 등장 주변:")
        s = max(0, idxs[0]-80); print("   ...", html[s:idxs[0]+120].replace("\n"," ").replace("\t"," "), "...")
    else:
        print(f"[{kw}] 없음")
