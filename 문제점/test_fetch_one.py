# -*- coding: utf-8 -*-
"""Phase 3 검증: 외부 art_id 를 로그인 없이 GET 해서 저널/발행기관이 파싱되는지 확인."""
import sys, io, re, httpx, urllib3
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

BASE = "https://www.kci.go.kr"
ARTI_VIEW = BASE + "/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId="
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

def clean(s): return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()
def meta(soup, n):
    el = soup.find("meta", attrs={"name": n}); return clean(el["content"]) if el and el.get("content") else ""

ids = [l.strip() for l in open("문제점/_external_artids.txt", encoding="utf-8") if l.strip()][:3]
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for aid in ids:
    r = client.get(ARTI_VIEW + aid)
    soup = BeautifulSoup(r.text, "lxml")
    pj = soup.find("p", class_="jounal")     # KCI 오타: jounal
    pp = soup.find("p", class_="pub")
    print(f"\n=== {aid}  (HTTP {r.status_code}, {len(r.text):,} bytes) ===")
    print("  title_en      :", meta(soup, "citation_title")[:60])
    print("  journal_en    :", meta(soup, "citation_journal_title"))
    print("  journal_ko(p) :", clean(pj.get_text()) if pj else "(없음)")
    print("  publisher_en  :", meta(soup, "citation_publisher"))
    print("  publisher_ko  :", clean(re.sub(r'^발행기관\s*:?\s*','',pp.get_text())) if pp else "(없음)")
    print("  pub_year      :", meta(soup, "citation_publication_date"))
client.close()
