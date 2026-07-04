# -*- coding: utf-8 -*-
"""Stage 2 본수집(밤샘 안전판): KRI PG-RP-102 에서 7개 필드를 Selenium 으로 수집.

밤샘 안전장치:
  - 절전 방지: SetThreadExecutionState (PC/디스플레이 sleep 차단 → idle 로그아웃 예방)
  - 연속 활동: 쉼 없이 페이지 이동(세션 idle 타임아웃 회피)
  - 체크포인트/재개: KRI/_kri_cache.jsonl (kri 당 1줄), 종결건만 skip
  - 세션 만료('로그인 시간 초과') 감지 시: 창에서 재로그인 될 때까지 대기 후 자동 재개
  - 비공개('정보 비공개') alert 처리

처음 실행 시: 뜨는 창에서 직접 로그인+2FA. (이미 로그인돼 있으면 바로 진행)
사용: python KRI/collect_kri_overnight.py
"""
import sys, io, os, re, json, time, ctypes, argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (UnexpectedAlertPresentException,
                                         NoAlertPresentException, TimeoutException,
                                         WebDriverException)
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROFILE = os.path.abspath("KRI/_chrome_profile")
BASE = "https://www.kri.go.kr"
URL = BASE + "/kri/rp/rschachv/PG-RP-102-02jr.jsp?txtRschrRegNo={kri}"
LOGIN_URL = BASE + "/kri2"
TEST_KRI = "10026059"   # 공개 연구자(검증됨) — 로그인 판정용
WORKLIST = "KRI/unique_kri.txt"
CACHE = "KRI/_kri_cache.jsonl"
PAGE_WAIT = 1.3

LABELS = {"한글": "성명", "한자": "성명_한자", "영문": "성명_영문",
          "성별": "성별", "출생년도": "출생년도", "기관": "소속대학기관",
          "직급": "직급", "재직여부": "재직여부", "연구분야": "전공분야",
          "세부전공명": "세부전공명", "취득학위": "취득학위", "수여대학": "출신학교_학위수여대학"}
KNOWN = set(LABELS)

# --- 절전 방지 ---
ES_CONTINUOUS = 0x80000000; ES_SYSTEM_REQUIRED = 0x00000001; ES_DISPLAY_REQUIRED = 0x00000002
def keep_awake():
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
def allow_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

def extract(html):
    cells = [c.get_text(" ", strip=True) for c in BeautifulSoup(html, "lxml").find_all(["th", "td"])]
    out = {}
    for i, t in enumerate(cells):
        if t in LABELS and i + 1 < len(cells):
            nxt = cells[i + 1]
            out[LABELS[t]] = "" if nxt in KNOWN else nxt
    return out

def get_alert(driver):
    try:
        a = driver.switch_to.alert; t = a.text; a.accept(); return t
    except NoAlertPresentException:
        return None

def load_done():
    done = set()
    if os.path.exists(CACHE):
        for l in open(CACHE, encoding="utf-8"):
            try: r = json.loads(l)
            except Exception: continue
            if r.get("status") in ("ok", "private"):
                done.add(r["kri_num"])
    return done

def append(rec):
    with open(CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def logged_in(driver):
    """TEST_KRI 페이지가 데이터로 뜨면 로그인 상태."""
    try:
        driver.get(URL.format(kri=TEST_KRI)); time.sleep(PAGE_WAIT)
    except UnexpectedAlertPresentException:
        pass
    al = get_alert(driver)
    if al and ("시간" in al or "로그인" in al):
        return False
    return "성명" in driver.page_source and "한글" in driver.page_source

def wait_login(driver, minutes=180):
    print(">> 창에서 직접 로그인+2FA 해주세요. (대기 중 — 최대 %d분)" % minutes, flush=True)
    driver.get(LOGIN_URL); time.sleep(3)
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if logged_in(driver):
            print(">> 로그인 확인. 수집 시작/재개.", flush=True); return True
        time.sleep(10)
    return False

def make_driver():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE}")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(30)        # 페이지 멈춤 시 30초 후 TimeoutException(전체 멈춤 방지)
    return d

def fetch_one(driver, kri):
    try:
        driver.get(URL.format(kri=kri))
    except UnexpectedAlertPresentException:
        pass
    except TimeoutException:
        pass                           # 부분 로드라도 진행
    time.sleep(PAGE_WAIT)
    al = get_alert(driver)
    if al:
        if "시간" in al or "다시 로그인" in al:
            return {"kri_num": kri, "status": "expired"}
        return {"kri_num": kri, "status": "private"}   # 정보 비공개
    html = driver.page_source
    if "성명" in html and "한글" in html:
        d = extract(html)
        if d.get("성명"):
            d.update({"kri_num": kri, "status": "ok"}); return d
    return {"kri_num": kri, "status": "error"}

def main():
    keep_awake()
    kris = [l.strip() for l in open(WORKLIST, encoding="utf-8") if l.strip()]
    done = load_done()
    todo = [k for k in kris if k not in done]
    print(f"전체 {len(kris):,} / 완료 {len(done):,} / 남은 {len(todo):,}", flush=True)
    if not todo:
        print("처리할 항목 없음."); allow_sleep(); return

    driver = make_driver()

    if not logged_in(driver):
        if not wait_login(driver):
            print("!! 로그인 대기 초과. 종료."); driver.quit(); allow_sleep(); return

    ok = priv = err = 0
    t0 = time.time()
    for i, kri in enumerate(todo, 1):
        try:
            rec = fetch_one(driver, kri)
        except Exception as e:                      # 드라이버/통신 장애 → 재시작 후 1회 재시도
            print(f"\n[예외 @ {kri}] {type(e).__name__} — 드라이버 재시작", flush=True)
            try: driver.quit()
            except Exception: pass
            try: driver = make_driver()
            except Exception:
                time.sleep(10); driver = make_driver()
            if not logged_in(driver):
                if not wait_login(driver):
                    print("!! 재로그인 대기 초과. 중단(재개 가능)."); break
            try:
                rec = fetch_one(driver, kri)
            except Exception:
                rec = {"kri_num": kri, "status": "error"}
        if rec["status"] == "expired":
            print(f"\n[세션 만료 @ {kri}] 재로그인 대기...", flush=True)
            if not wait_login(driver):
                print("!! 재로그인 대기 초과. 중단(여기까지 저장됨, 나중에 재개 가능)."); break
            rec = fetch_one(driver, kri)            # 재시도
            if rec["status"] == "expired":
                append({"kri_num": kri, "status": "error"}); continue
        append(rec)
        ok += rec["status"] == "ok"; priv += rec["status"] == "private"; err += rec["status"] == "error"
        if i % 50 == 0 or i == len(todo):
            rate = i / max(1e-9, time.time() - t0)
            eta = (len(todo) - i) / max(1e-9, rate) / 60
            print(f"  {i}/{len(todo)}  ok {ok} priv {priv} err {err}  "
                  f"{rate:.1f}/s ETA {eta:.0f}분", flush=True)
    driver.quit(); allow_sleep()
    print(f"\n완료: ok {ok:,} / 비공개 {priv:,} / 오류 {err:,}", flush=True)

if __name__ == "__main__":
    main()
