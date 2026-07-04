# -*- coding: utf-8 -*-
"""poCretDetail 껍데기에서 데이터 로딩(AJAX) 엔드포인트·파라미터 파악."""
import sys, io, re, pandas as pd, httpx, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
df = pd.read_pickle("Data/한국어와문학_결과2/korlit_2008_2024.pkl")
r = df[(df.authors_ko.map(len) == 1) & (df.crt_id.astype(str).str.startswith("CRT"))].iloc[0]
url = f"{BASE}/kciportal/po/citationindex/poCretDetail.kci?citationBean.cretId={r.crt_id}&citationBean.artiId={r.article_id}"
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
html = client.get(url).text
client.close()
print(f"crt_id={r.crt_id} art={r.article_id}  shell {len(html):,} bytes\n")

# script src
print("=== <script src> ===")
for m in re.findall(r'<script[^>]+src="([^"]+)"', html): print("  ", m)
# .kci 엔드포인트 / ajax url 후보
print("\n=== .kci / ajax / List / json URL 후보 ===")
for m in sorted(set(re.findall(r'["\'](/[^"\']*?(?:\.kci|List|ajax|json|Cret|Rschr)[^"\']*)["\']', html))):
    print("  ", m)
# 함수명 정의
print("\n=== fnc/function 정의 후보 ===")
for m in sorted(set(re.findall(r'function\s+(\w+)', html)))[:30]: print("  ", m)
# body 영역 텍스트 일부
print("\n=== body 앞 600자 ===")
b = re.search(r'<body[^>]*>(.*)', html, re.S)
if b: print(re.sub(r'\s+', ' ', b.group(1))[:600])
