# -*- coding: utf-8 -*-
"""Stage 2 탐색: KRI 로그인(2FA 수동) 후 연구자정보 그리드 '구조'를 덤프.
추출 로직을 확정하기 전에, 7개 필드(성명·성별·소속·직급·전공분야·출신학교·취득학위)가
실제로 어느 셀에 들어있는지 눈으로 확인하기 위함.

- 보이는 크롬(non-headless) + 전용 프로파일(2FA 1회). 로그인은 사용자가 창에서 직접.
- 스크립트는 '로그아웃' 문구가 보일 때까지 폴링(최대 8분)하며 대기.
- 로그인 후 성명검색 그리드에서 kri_num 검색 → 모든 셀(class, text) 덤프.
"""
import sys, io, os, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROFILE = os.path.abspath("KRI/_chrome_profile")
DUMP = "KRI/_kri_grid_dump.html"
# 검증용 kri_num: Stage 1b 캐시에서 앞쪽 일부 사용
def sample_kris(n=3):
    ks = []
    if os.path.exists("KRI/_krinum_cache.jsonl"):
        for l in open("KRI/_krinum_cache.jsonl", encoding="utf-8"):
            r = json.loads(l)
            if r.get("ok") and r.get("kri_num"):
                ks.append(r["kri_num"])
            if len(ks) >= n:
                break
    return ks or ["11507194"]

def make_driver():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE}")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_experimental_option("detach", True)   # 스크립트 끝나도 창 유지(세션 보존)
    return webdriver.Chrome(options=opts)

def wait_login(driver, minutes=6):
    print(">> 열린 크롬 창에서 직접 로그인 + 2차인증을 완료하세요. (대기 중...)")
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        src = driver.page_source
        if "로그아웃" in src or "logout" in src.lower():
            print(">> 로그인 감지됨. 계속 진행합니다.")
            return True
        time.sleep(3)
    print("!! 로그인 대기 시간 초과")
    return False

def main():
    kris = sample_kris(3)
    print("탐색 대상 kri_num:", kris)
    driver = make_driver()
    driver.get("https://www.kri.go.kr/kri2")
    time.sleep(3)
    if "로그아웃" not in driver.page_source:
        if not wait_login(driver):
            driver.quit(); return
    else:
        print(">> 이미 로그인된 세션(프로파일 재사용).")

    # 성명검색 화면 진입
    try:
        driver.find_element(By.XPATH, "//*[@class='dep1-item ico-search']").click(); time.sleep(1)
        driver.find_element(By.XPATH, "//*[@class='MNU_1103']").click(); time.sleep(2)
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            driver.switch_to.frame(iframes[0])
    except Exception as e:
        print("검색화면 진입 실패(구조 변경 가능):", e)

    kri = kris[0]
    try:
        box = driver.find_element(By.XPATH, '//*[@id="txtSearchRschrRegNo"]')
        box.clear(); box.send_keys(kri); time.sleep(0.3)
        driver.execute_script("doAction('SEARCH');")
        time.sleep(5)
    except Exception as e:
        print("검색 실행 실패:", e)

    html = driver.page_source
    open(DUMP, "w", encoding="utf-8").write(html)
    print(f"\n그리드 HTML 덤프 저장: {DUMP} ({len(html):,} bytes)")

    # 모든 td 의 (class, text) 출력 — 헤더/데이터 구분 파악용
    soup = BeautifulSoup(html, "lxml")
    tds = soup.find_all("td")
    print(f"\n=== td 총 {len(tds)}개 중 텍스트 있는 셀 (class | text) ===")
    shown = 0
    for td in tds:
        txt = td.get_text(strip=True)
        if txt:
            cls = " ".join(td.get("class") or [])
            print(f"  [{cls}] {txt[:40]}")
            shown += 1
            if shown >= 80:
                print("  ... (이하 생략)")
                break
    print("\n>> 덤프 완료. 크롬 창은 열린 채로 둡니다(세션 유지).")

if __name__ == "__main__":
    main()
