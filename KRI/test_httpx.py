# -*- coding: utf-8 -*-
"""httpx 로 PG-RP-102 를 받을 수 있는지 테스트(서버렌더 여부 + 비공개 처리).
프로파일에서 쿠키를 뽑아 httpx 로 공개/비공개 연구자 각각 조회."""
import sys, io, os, time, httpx, urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

PROFILE = os.path.abspath("KRI/_chrome_profile")
BASE = "https://www.kri.go.kr"
URL = BASE + "/kri/rp/rschachv/PG-RP-102-02jr.jsp?txtRschrRegNo={kri}"
PUBLIC = "10026059"   # 김정숙 (검증서 공개 확인됨)
PRIVATE = "10001921"  # 비공개 확인됨

# 1) 프로파일에서 쿠키 추출
opts = Options()
opts.add_argument(f"--user-data-dir={PROFILE}")
opts.add_argument("--headless=new")
opts.add_argument("--log-level=3")
opts.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Chrome(options=opts)
driver.get(BASE + "/kri2"); time.sleep(2)
cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
driver.quit()
print("쿠키:", list(cookies.keys()))

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True, timeout=60)
for k, v in cookies.items(): client.cookies.set(k, v, domain="www.kri.go.kr")

for label, kri in [("공개", PUBLIC), ("비공개", PRIVATE)]:
    html = client.get(URL.format(kri=kri)).text
    soup = BeautifulSoup(html, "lxml")
    rowtexts = []
    for tr in soup.find_all("tr"):
        t = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        t = [x for x in t if x]
        if t: rowtexts.append(" | ".join(t))
    has_name = any("성명" in r for r in rowtexts)
    has_alert = "비공개" in html or "alert(" in html
    print(f"\n=== [{label}] kri={kri} bytes={len(html):,} ===")
    print(f"  성명행 존재(서버렌더?): {has_name} | 비공개/alert 흔적: {has_alert}")
    print("  표 행(앞6):")
    for r in rowtexts[:6]:
        print("    ", r[:90])
client.close()
