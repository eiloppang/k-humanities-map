# -*- coding: utf-8 -*-
"""분과 학술지 목록 자동 추출 — KCI 분류검색(ciSereClasList)에서 해당 분과의
학술지(name, sere_id, insi_id)를 긁어 config.ACTIVE.journals_csv 로 저장.

scrape_korlit 의 입력이 되는 '분과별 학술지 목록'을 만드는 단계(과거엔 수동).
분과코드는 config 의 Discipline.code (KCI 대분류 코드, 예: A03=철학, A11=한국어와문학).

사용:
  python fetch_journals.py                       # config.ACTIVE 분과
  python fetch_journals.py --discipline PHILOSOPHY  # 특정 Discipline
"""
import sys, os, io, re, csv, html, argparse
import httpx, urllib3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Scraping-Code
import config
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
urllib3.disable_warnings()

URL = "https://www.kci.go.kr/kciportal/ci/clasSearch/ciSereClasList.kci"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
# 각 학술지: onclick="fncGoLevel2List('<sereId>','<insiId>')" ... <em> N. 이름 ... </em>
# sereId 는 SER형식(SER000...) 또는 레거시 숫자형식(001490) 둘 다 존재.
PAT = re.compile(r"fncGoLevel2List\('([^']+)','(INS\d+)'\)[^>]*>\s*<em>(.*?)</em>", re.S)


def clean_name(raw):
    t = html.unescape(re.sub(r"<[^>]+>", " ", raw))     # 태그 제거(상태아이콘 span 등)
    t = re.sub(r"^\s*\d+\.\s*", "", t)                   # 앞 순번 "N."
    t = re.split(r"\s+KCI\s*(?:등재후보|등재|후보)", t)[0]   # 'KCI 등재' 라벨 이후 절단
    t = re.sub(r"\s*-\s*[^-]*\(총[^)]*\)\s*$", "", t)     # ' - 기관 (총 N 개)'
    t = re.sub(r"\s*\(총\s*[\d,]+\s*개\)\s*$", "", t)      # 잔여 '(총 N 개)'
    return re.sub(r"\s+", " ", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discipline", help="config 의 Discipline 이름(예: PHILOSOPHY). 미지정 시 ACTIVE")
    args = ap.parse_args()
    D = getattr(config, args.discipline) if args.discipline else config.ACTIVE

    print(f"분과: {D.name} (KCI 분야코드 {D.code}) → {D.journals_csv}")
    c = httpx.Client(verify=False, follow_redirects=True, timeout=60, headers=HEADERS)
    data = {"clasSearchBean.middMajorCd": D.code,
            "clasSearchBean.jaum": "", "clasSearchBean.jaum2": ""}
    h = c.post(URL, data=data).text
    c.close()

    rows, seen = [], set()
    for m in PAT.finditer(h):
        sere, insi, em = m.group(1), m.group(2), m.group(3)
        if sere in seen:
            continue
        seen.add(sere)
        rows.append({"name": clean_name(em), "sere_id": sere, "insi_id": insi})

    if not rows:
        sys.exit("학술지를 못 찾음 — 분야코드/응답 구조 확인 필요.")

    os.makedirs(D.out_dir, exist_ok=True)
    with open(D.journals_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "sere_id", "insi_id"])
        w.writeheader(); w.writerows(rows)

    leg = sum(1 for r in rows if not r["sere_id"].startswith("SER"))
    print(f"저장 완료: {len(rows)}종 (SER형식 {len(rows)-leg} / 레거시 숫자형식 {leg})")
    print("샘플:", ", ".join(r["name"] for r in rows[:6]))


if __name__ == "__main__":
    main()
