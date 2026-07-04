# -*- coding: utf-8 -*-
"""Stage 2 검증: PG-RP-102-02jr(기본정보 조회)에서 7개 필드를 '실제 값'으로 추출.
로그인된 프로파일 재사용(2FA 불필요). 기본 10명 출력.

7개 필드: 성명·성별·소속대학기관·직급·전공분야(세부전공명)·출신학교·취득학위
"""
import sys, io, os, re, time, json, argparse, csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROFILE = os.path.abspath("KRI/_chrome_profile")
BASE = "https://www.kri.go.kr"
URL = BASE + "/kri/rp/rschachv/PG-RP-102-02jr.jsp?txtRschrRegNo={kri}"

# 라벨(셀) -> 필드. 표가 라벨/값 교대 구조라 '라벨 셀 다음 셀'이 값.
LABELS = {
    "한글": "성명", "한자": "성명_한자", "영문": "성명_영문",
    "성별": "성별", "출생년도": "출생년도",
    "기관": "소속대학기관", "직급": "직급", "재직여부": "재직여부",
    "연구분야": "전공분야", "세부전공명": "세부전공명",
    "취득학위": "취득학위", "수여대학": "출신학교_학위수여대학",
}
KNOWN = set(LABELS)

def extract(html):
    soup = BeautifulSoup(html, "lxml")
    cells = [c.get_text(" ", strip=True) for c in soup.find_all(["th", "td"])]
    out = {}
    for i, t in enumerate(cells):
        if t in LABELS and i + 1 < len(cells):
            nxt = cells[i + 1]
            out[LABELS[t]] = "" if nxt in KNOWN else nxt   # 값 비면 빈칸
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()
    allk = [l.strip() for l in open("KRI/unique_kri.txt", encoding="utf-8") if l.strip()]
    # 목록 전체에서 고르게 샘플(쏠림 방지)
    step = max(1, len(allk) // args.n)
    kris = allk[::step][:args.n]
    print(f"검증 대상 {len(kris)}명 (전체 {len(allk):,}명에서 균등 샘플)\n")

    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE}")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=opts)

    rows = []
    cols = ["성명", "성별", "소속대학기관", "직급", "전공분야", "세부전공명",
            "출신학교_학위수여대학", "취득학위"]
    for kri in kris:
        try:
            driver.get(URL.format(kri=kri))
        except UnexpectedAlertPresentException:
            pass
        time.sleep(2.0)
        # 비공개 연구자: JS alert 처리
        private, msg = False, ""
        try:
            al = driver.switch_to.alert; msg = al.text; al.accept(); private = True; time.sleep(0.3)
        except NoAlertPresentException:
            pass
        if private:
            d = {"비공개": msg}
            rows.append({**d, "kri_num": kri})
            print(f"=== kri {kri} : [비공개] {msg[:40]} ===\n")
            continue
        d = extract(driver.page_source)
        d["kri_num"] = kri
        rows.append(d)
        print(f"=== kri {kri} : {d.get('성명','(없음)')} ===")
        for c in cols:
            print(f"    {c:14s}: {d.get(c,'') or '(빈칸)'}")
        print()
    driver.quit()

    with open("KRI/_verify10.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["kri_num"] + cols + ["성명_한자", "성명_영문", "출생년도", "재직여부"])
        w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in w.fieldnames})
    print("저장: KRI/_verify10.csv")

if __name__ == "__main__":
    main()
