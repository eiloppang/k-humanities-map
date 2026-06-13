# -*- coding: utf-8 -*-
"""
KCI 학술지 연구분야 / 연관 연구분야 스크래퍼

- 입력 : Data/250519_journal_counts.csv (journal-name 열)
- 출력 : Data/kci_research_fields.csv
- 방식 : 순수 HTTP(httpx) + BeautifulSoup. Selenium 불필요(정적 HTML).
- 속도 : I/O 바운드이므로 ThreadPoolExecutor로 동시 요청(기본 8). GPU/멀티프로세싱 불필요.
"""
import csv
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.kci.go.kr"
SEARCH_PAGE = BASE + "/kciportal/po/search/poSereSear.kci"
SEARCH_POST = BASE + "/kciportal/po/search/poSereSearList.kci"

IN_CSV = "Data/250519_journal_counts.csv"
OUT_CSV = "Data/kci_research_fields.csv"

MAX_WORKERS = 8
RETRIES = 3
TIMEOUT = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

_norm_re = re.compile(r"\s+")


def norm(s: str) -> str:
    """공백 제거 후 비교용 정규화."""
    return _norm_re.sub("", s or "").lower()


def make_client() -> httpx.Client:
    c = httpx.Client(timeout=TIMEOUT, verify=False, headers=HEADERS, follow_redirects=True)
    # 세션 쿠키 확보
    try:
        c.get(SEARCH_PAGE)
    except Exception:
        pass
    return c


def search_journal(client: httpx.Client, name: str):
    """학술지명으로 검색 → (matched_title, href) 목록 반환."""
    data = {
        "poSearchBean.searType": "journal",
        "poSearchBean.conditionList": "SERE_NM",
        "poSearchBean.keywordList": name,
        "poSearchBean.startPg": "1",
        "poSearchBean.docsCount": "10",
    }
    r = client.post(SEARCH_POST, data=data)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "lxml")
    results = []
    for a in soup.find_all("a", href=True):
        if "ciSereInfoView" in a["href"]:
            results.append((a.get_text(strip=True), a["href"]))
    return results


def rank_candidates(name: str, results):
    """이름 일치도 순으로 후보 정렬(가장 잘 맞는 것부터)."""
    if not results:
        return []
    target = norm(name)

    def score(item):
        title = item[0]
        kor = norm(title.split("(")[0])
        full = norm(title)
        if kor == target:
            return 0           # 한글명 완전 일치
        if kor.startswith(target) or target in kor:
            return 1           # 한글명 포함
        if target in full:
            return 2           # 전체 제목 포함
        return 3

    return sorted(results, key=score)


def parse_main_field(ds: BeautifulSoup):
    for strong in ds.find_all("strong"):
        if strong.get_text(" ", strip=True).replace(" ", "") == "연구분야":
            span = strong.find_next_sibling("span")
            if not span:
                return None
            cats = [a.get_text(strip=True) for a in span.find_all("a", class_="colorBlue")]
            return " > ".join(cats) if cats else None
    return None


def parse_related(ds: BeautifulSoup):
    for strong in ds.find_all("strong"):
        if strong.get_text(" ", strip=True).replace(" ", "").startswith("연관연구분야"):
            ul = strong.find_next_sibling("ul") or strong.find_next("ul")
            if not ul:
                return []
            items = []
            for li in ul.find_all("li"):
                txt = _norm_re.sub(" ", li.get_text(" ", strip=True)).strip()
                if txt:
                    items.append(txt)
            return items
    return []


def fetch_detail(client: httpx.Client, href: str):
    r = client.get(BASE + href)
    r.encoding = "utf-8"
    ds = BeautifulSoup(r.text, "lxml")
    return parse_main_field(ds), parse_related(ds)


_local = threading.local()


def get_client() -> httpx.Client:
    if not hasattr(_local, "client"):
        _local.client = make_client()
    return _local.client


def process(rank, name):
    """한 저널 처리. 실패 시 재시도."""
    last_err = None
    for attempt in range(RETRIES):
        try:
            client = get_client()
            results = search_journal(client, name)
            cands = rank_candidates(name, results)
            if not cands:
                return {"rank": rank, "journal-name": name, "matched-title": "",
                        "연구분야": "", "연관연구분야": "", "status": "NO_MATCH",
                        "n_results": len(results)}
            # 동명 학술지가 여러 개일 수 있으므로, 연구분야가 실제로 채워진
            # 후보를 우선 선택(최대 상위 4개 확인). 모두 비어 있으면 1순위 사용.
            fallback = None
            for title, href in cands[:4]:
                main, related = fetch_detail(client, href)
                if fallback is None:
                    fallback = (title, main, related)
                if main:
                    return {"rank": rank, "journal-name": name, "matched-title": title,
                            "연구분야": main, "연관연구분야": " | ".join(related),
                            "status": "OK", "n_results": len(results)}
            title, main, related = fallback
            return {"rank": rank, "journal-name": name, "matched-title": title,
                    "연구분야": main or "", "연관연구분야": " | ".join(related),
                    "status": "OK_NO_FIELD" if not main else "OK", "n_results": len(results)}
        except Exception as e:
            last_err = e
            time.sleep(1.0 + attempt)
    return {"rank": rank, "journal-name": name, "matched-title": "",
            "연구분야": "", "연관연구분야": "", "status": f"ERROR: {last_err}", "n_results": 0}


def main():
    rows = []
    with open(IN_CSV, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append((row["rank"], row["journal-name"].strip()))

    print(f"총 {len(rows)}개 학술지, 동시 {MAX_WORKERS} 스레드로 스크래핑 시작...")
    t0 = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(process, rk, nm): rk for rk, nm in rows}
        done = 0
        for fut in as_completed(futs):
            res = fut.result()
            results[res["rank"]] = res
            done += 1
            print(f"[{done}/{len(rows)}] {res['status']:>8} | {res['journal-name']} -> {res['연구분야']}")

    ordered = [results[rk] for rk, _ in rows]
    fields = ["rank", "journal-name", "matched-title", "연구분야", "연관연구분야", "status", "n_results"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(ordered)

    ok = sum(1 for r in ordered if r["status"] == "OK")
    print(f"\n완료: {ok}/{len(rows)} 성공, {time.time()-t0:.1f}초 소요")
    print(f"저장: {OUT_CSV}")
    fails = [r for r in ordered if r["status"] != "OK"]
    if fails:
        print("실패/미매칭:")
        for r in fails:
            print(f"  - {r['journal-name']}: {r['status']}")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
