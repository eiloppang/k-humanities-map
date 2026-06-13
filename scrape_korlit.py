# -*- coding: utf-8 -*-
"""
KCI '인문학 > 한국어와문학' 논문 수집기 (2008~2024)
==================================================

연구분야가 "인문학 > 한국어와문학"인 학술지를 모두 골라, 2008~2024년 논문의
서지정보 + 초록 + 키워드 + **인용현황(피인용 목록 + 참고문헌)** 을 수집한다.
인용현황은 한국문학의 '지평도(인용 네트워크)'를 그리기 위한 핵심 데이터다.

수집 컬럼
---------
  article_id        KCI 논문 ID (ART...)
  crt_id            KCI 인용 보고서 ID (CRT...)   - 인용현황 상세 조회 키
  sere_id           학술지 ID (SER...)
  title_ko/title_en 제목(국문/영문)
  journal_ko/_en    학술지명(국문/영문)
  publisher_ko/_en  발행기관(국문/영문)
  pub_year          발행연도
  pub_date          발행연월 (YYYY.MM)
  volume / issue    권 / 호
  page_start/end / pages   시작/끝 페이지, 원문표기
  doi / issn        DOI / ISSN
  research_field    연구분야(논문 세부분류, 예: 현대소설(국문학))
  journal_field     학술지 대분류(= 인문학 > 한국어와문학)
  authors_ko/_en    저자(국문/영문, 리스트)
  affiliations      저자 소속(리스트)
  abstract_ko/_en   초록(국문/영문)
  keywords_ko/_en   키워드(국문/영문, 리스트)
  cited_count       KCI 피인용 횟수
  fwci              FWCI(정규화 인용지수)
  view_count        열람수
  ref_count         참고문헌 수
  citing_count      피인용(이 논문을 인용한 논문) 수
  references        참고문헌 리스트 [{n, type, art_id, text}]
  cited_by          피인용 리스트 [{art_id, crt_id, title, authors, pub_date,
                                    journal, volume, issue, pages, cited_count}]

방식
----
  1. Selenium 으로 KCI 에 **1회 로그인** → 세션 쿠키 추출 (참고문헌/피인용 목록은
     로그인 후에만 HTML 에 인라인으로 노출됨).
  2. 그 쿠키로 httpx + ThreadPoolExecutor 멀티스레드 고속 스크래핑.
     (네트워크 I/O 바운드라 멀티프로세싱보다 스레드풀이 정석. GIL 은 네트워크 대기
      중 풀린다.)
  3. 진행상황은 tqdm 진행바로 표시. 완료 레코드는 JSONL 체크포인트에 즉시 적재해
     중단되어도 이어서 재개(resume) 가능.
  4. 세션이 끊기면(로그아웃 감지) 자동 재로그인.

출력 (Data/한국어와문학/)
  korlit_2008_2024.csv      - 사람이 보기 좋은 CSV (중첩 데이터는 JSON 문자열)
  korlit_2008_2024.pkl      - pandas pickle (중첩 데이터는 파이썬 객체 그대로)
  _checkpoint.jsonl         - 진행 체크포인트 (재개용)
  _journals.csv             - 수집 대상 학술지 목록
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import pandas as pd
import urllib3
from bs4 import BeautifulSoup
from tqdm import tqdm

urllib3.disable_warnings()

# ----------------------------------------------------------------------------
# 설정
# ----------------------------------------------------------------------------
try:
    from kci_config import KCI_ID, KCI_PW
except ImportError:
    KCI_ID = os.environ.get("KCI_ID", "")
    KCI_PW = os.environ.get("KCI_PW", "")

BASE = "https://www.kci.go.kr"
SEARCH_JOURNAL_PAGE = BASE + "/kciportal/po/search/poSereSear.kci"
SEARCH_JOURNAL_POST = BASE + "/kciportal/po/search/poSereSearList.kci"
SEARCH_ARTI_PAGE = BASE + "/kciportal/po/search/poArtiSear.kci"
SEARCH_ARTI_POST = BASE + "/kciportal/po/search/poArtiSearList.kci"
ARTI_VIEW = BASE + "/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId="
LOGIN_PAGE = BASE + "/kciportal/check/login.jsp"

IN_FIELDS_CSV = "Data/kci_research_fields.csv"
TARGET_FIELD = "인문학 > 한국어와문학"
START_YEAR = 2008
END_YEAR = 2024

OUT_DIR = os.path.join("Data", "한국어와문학_결과2")
OUT_CSV = os.path.join(OUT_DIR, "korlit_2008_2024.csv")
OUT_PKL = os.path.join(OUT_DIR, "korlit_2008_2024.pkl")
CKPT = os.path.join(OUT_DIR, "_checkpoint.jsonl")
JOURNALS_CSV = os.path.join(OUT_DIR, "_journals.csv")
# 한국어와문학(분야코드 A11) 전체 학술지 목록 (KCI 분류검색 ciSereClasList 에서 추출, 115종)
A11_CSV = os.path.join(OUT_DIR, "journals_a11.csv")

# 샘플(스모크 테스트) 출력 - 처음 N편만 뽑아 바로 눈으로 확인
SAMPLE_CSV = os.path.join(OUT_DIR, "_sample.csv")
SAMPLE_PKL = os.path.join(OUT_DIR, "_sample.pkl")
SAMPLE_CKPT = os.path.join(OUT_DIR, "_sample_checkpoint.jsonl")

MAX_WORKERS = 12          # 동시 스레드 (서버 부담/속도 균형). 막히면 8로 낮출 것.
DOCS_PER_PAGE = 300       # 검색 페이지당 논문 수 (KCI 최대 300)
RETRIES = 4
TIMEOUT = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

_ws = re.compile(r"\s+")
_norm = re.compile(r"\s+")


def clean(s: str | None) -> str:
    return _ws.sub(" ", (s or "").replace("\xa0", " ")).strip()


def norm(s: str) -> str:
    return _norm.sub("", (s or "")).lower()


_kw_content = re.compile(r"[가-힣A-Za-z0-9一-鿿]")


def _kw_ok(s: str) -> bool:
    """키워드 유효성: 비거나 구두점만 있는 것(예: KCI '키워드 없음' placeholder '.') 제외."""
    s = clean(s)
    return bool(s) and bool(_kw_content.search(s))


# ----------------------------------------------------------------------------
# 1. 로그인 (Selenium 1회) → 쿠키
# ----------------------------------------------------------------------------
_cookie_lock = threading.Lock()


def _login_once() -> dict:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,1000")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(TIMEOUT)
    try:
        driver.get(LOGIN_PAGE)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "uid")))
        driver.find_element(By.ID, "uid").clear()
        driver.find_element(By.ID, "uid").send_keys(KCI_ID)
        driver.find_element(By.ID, "upw").clear()
        driver.find_element(By.ID, "upw").send_keys(KCI_PW)
        # 폼의 jQuery onsubmit 핸들러가 secrNo/membId 를 채우고 login.kci 로 POST.
        driver.execute_script("$('#loginForm').submit();")
        time.sleep(5)
        # 쿠키 안착을 위해 메인 페이지 한 번 더 방문
        try:
            driver.get(BASE + "/kciportal/main.kci")
            time.sleep(2)
        except Exception:  # noqa
            pass
        return {c["name"]: c["value"] for c in driver.get_cookies()}
    finally:
        driver.quit()


def selenium_login() -> dict:
    """셀레늄으로 KCI 로그인 후 세션 쿠키 dict 반환 (재시도 포함)."""
    last = {}
    for attempt in range(3):
        try:
            cookies = _login_once()
        except Exception as e:  # noqa
            print(f"  로그인 시도 {attempt+1} 오류: {e}")
            cookies = {}
        last = cookies
        if "JSESSIONID" in cookies:
            return cookies
        print(f"  로그인 시도 {attempt+1} 실패(쿠키: {list(cookies.keys())}), 재시도...")
        time.sleep(3)
    raise RuntimeError(f"로그인 실패: JSESSIONID 미획득 (마지막 쿠키: {list(last.keys())})")


def apply_cookies(client: httpx.Client, cookies: dict):
    for k, v in cookies.items():
        client.cookies.set(k, v, domain="www.kci.go.kr")


def relogin(client: httpx.Client):
    """세션 만료 시 재로그인 (스레드 안전)."""
    with _cookie_lock:
        tqdm.write("  [세션 만료 감지] 재로그인 중...")
        cookies = selenium_login()
        client.cookies.clear()
        apply_cookies(client, cookies)
        tqdm.write("  [재로그인 완료]")


# ----------------------------------------------------------------------------
# HTTP 헬퍼 (재시도)
# ----------------------------------------------------------------------------
def http_get(client: httpx.Client, url: str, tries: int = RETRIES):
    last = None
    for i in range(tries):
        try:
            r = client.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(1.0 + i)
    raise RuntimeError(f"GET 실패 {url}: {last}")


def http_post(client: httpx.Client, url: str, data: dict, tries: int = RETRIES):
    last = None
    for i in range(tries):
        try:
            r = client.post(url, data=data, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(1.0 + i)
    raise RuntimeError(f"POST 실패 {url}: {last}")


# ----------------------------------------------------------------------------
# 2. 학술지 해석: 연구분야=한국어와문학 인 학술지 → (이름, sereId)
# ----------------------------------------------------------------------------
# 학술지 검색은 짧은 시간에 여러 번 치면 KCI 가 결과를 빈/부분으로 깎는다(IP 레이트리밋).
# 실측: 6연속은 OK, 40연속(빠르게)은 깎임. → 검색 간 일정 간격(STEP_DELAY)으로 임계 아래 유지.
STEP_DELAY = 3.0       # 검색 간 간격(초)
ROUND_COOLDOWN = 15.0  # 재시도 라운드 사이 휴지(초)
RESOLVE_ROUNDS = 4


def journal_display(matched_title: str) -> str:
    """matched_title 에서 영문/로마자 번역 괄호만 제거한 '논문검색 표시명'.
    (라틴문자만 든 괄호=영문번역 → 제거, 한자/한글 든 괄호는 유지.
     예: '어문연구(語文硏究) (The Society...)' → '어문연구(語文硏究)',
         '어문연구(EOMUNYEONGU)' → '어문연구')
    동명이저널(어문연구 2종)을 이 표시명으로 구분한다."""
    def repl(m):
        inner = m.group(1)
        if re.search(r"[A-Za-z]", inner) and not re.search(r"[가-힣]", inner):
            return ""
        return m.group(0)
    s = clean(re.sub(r"\s*\(([^()]*)\)", repl, matched_title))
    # 중복 괄호 'X(X)' → 'X' (예: '사이間SAI(사이間SAI)')
    mm = re.match(r"^(.*?)\((.*)\)$", s)
    while mm and norm(mm.group(1)) == norm(mm.group(2)):
        s = clean(mm.group(1))
        mm = re.match(r"^(.*?)\((.*)\)$", s)
    return s


def _load_targets() -> list[dict]:
    """한국어와문학(A11) 전체 학술지 목록을 journals_a11.csv 에서 로드(115종).
    각 항목: name(검색어 겸 표시), sere_id(논문 정밀필터용 = 논문검색행 sereId 와 일치),
    insi_id(발행기관 id). sereId 가 논문검색 결과행의 sereId 와 동일함을 검증함."""
    if not os.path.exists(A11_CSV):
        sys.exit(f"학술지 목록이 없습니다: {A11_CSV}\n"
                 f"(KCI 분류검색 ciSereClasList 의 한국어와문학(A11) 목록을 먼저 저장하세요.)")
    rows = list(csv.DictReader(open(A11_CSV, "r", encoding="utf-8-sig")))
    return [{"name": clean(r["name"]), "query": clean(r["name"]),
             "sere_id": clean(r["sere_id"]), "insi_id": clean(r.get("insi_id", ""))}
            for r in rows if r.get("sere_id")]


def resolve_journals(client: httpx.Client, max_journals: int | None = None) -> list[dict]:
    """수집 대상 학술지 목록(한국어와문학 A11 전체 115종) 반환.
    논문은 학술지명으로 검색한 뒤 행의 sereId 가 목표 sereId 와 일치하는 것만 취한다
    (sereId 가 유일 식별자이므로 동명이저널/이름변형 문제 없음).
    max_journals 지정 시 앞에서 그 수만큼만(샘플용)."""
    journals = _load_targets()
    if max_journals:
        journals = journals[:max_journals]
    if not max_journals:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(JOURNALS_CSV, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["name", "sere_id", "insi_id"])
            w.writeheader()
            w.writerows([{k: j[k] for k in ("name", "sere_id", "insi_id")} for j in journals])
    return journals


# ----------------------------------------------------------------------------
# 3. 논문 열거: 학술지명 + 연도범위로 검색, sereId 로 정밀 필터
# ----------------------------------------------------------------------------
_total_re = re.compile(r"/\s*([\d,]+)\s*건")


def parse_search_rows(html: str, target: dict) -> list[dict]:
    """검색 결과 행에서 논문 추출 - 행의 sereId 가 target['sere_id'] 와 일치하는 행만.

    sereId 는 학술지 유일 식별자이고, 분류검색(ciSereClasList)에서 얻은 sereId 가 논문검색
    결과행의 sereId 와 동일함을 검증했다. 학술지명(SERE_NM) 검색은 유사명 저널을 함께
    반환하므로 sereId 로 정밀 필터한다(동명이저널·이름변형 모두 정확히 구분됨).
    """
    tsid = target["sere_id"]
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for subj in soup.select("a.subject[href*='artiId=ART']"):
        m = re.search(r"artiId=(ART\d+)", subj["href"])
        if not m:
            continue
        art_id = m.group(1)
        row = subj
        for _ in range(6):
            row = row.parent
            if row is None:
                break
            if row.find("a", href=re.compile("ciSereInfoView")):
                break
        if row is None:
            continue
        jl = row.find("a", href=re.compile("ciSereInfoView"))
        sid = re.search(r"sereSearBean\.sereId=([0-9A-Za-z]+)", jl["href"]) if jl else None
        if not sid or sid.group(1) != tsid:
            continue
        crt = re.search(r"cretId=(CRT\d+)", str(row))
        pl = row.find("a", href=re.compile("poInsiSearSoceView"))
        rows.append({"art_id": art_id,
                     "crt_id": crt.group(1) if crt else "",
                     "sere_id": tsid,
                     "publisher_ko": clean(pl.get_text()) if pl else ""})
    return rows


MAX_ENUM_PAGES = 60   # 안전 상한


def enumerate_articles(client: httpx.Client, journal: dict) -> list[dict]:
    """한 학술지의 2008~2024 논문 전체 열거.

    KCI 학술지명(SERE_NM) 검색은 유사명 저널까지 잡는 퍼지매칭이라 결과에 다른 저널이
    섞이고 총건수가 부풀려진다. 행의 표시명(display)으로 목표 저널만 골라낸다.
    목표 저널 논문은 보통 앞쪽에 연속 배치되지만, 동명이저널이 앞블록을 차지하면
    뒤에 올 수도 있으므로 '목표 블록을 찾은 뒤(got_any) 매칭이 끊기면' 중단한다.
    """
    def page(pg):
        data = {
            "poSearchBean.searType": "thesis",
            "poSearchBean.conditionList": "SERE_NM",
            "poSearchBean.keywordList": journal["name"],
            "poSearchBean.pubiStYr": str(START_YEAR),
            "poSearchBean.pubiEndYr": str(END_YEAR),
            "poSearchBean.startPg": str(pg),
            "poSearchBean.docsCount": str(DOCS_PER_PAGE),
        }
        return http_post(client, SEARCH_ARTI_POST, data)

    rows, seen = [], set()
    got_any = False
    for pg in range(1, MAX_ENUM_PAGES + 1):
        html = page(pg).text
        n_subjects = html.count('class="subject"')
        matched = parse_search_rows(html, journal)
        for x in matched:
            if x["art_id"] not in seen:
                seen.add(x["art_id"])
                rows.append(x)

        if matched:
            got_any = True
        elif got_any:
            break                        # 목표 블록을 지나침 → 종료
        if n_subjects < DOCS_PER_PAGE:   # 검색결과의 마지막 페이지(빈 페이지 포함)
            break
        time.sleep(0.4)                  # 페이지 간 간격(throttle 완화)
    return rows


# ----------------------------------------------------------------------------
# 4. 상세 페이지 파서
# ----------------------------------------------------------------------------
def _meta(soup, name):
    el = soup.find("meta", attrs={"name": name})
    return clean(el["content"]) if el and el.get("content") else ""


def _section(soup, h2_id):
    """h2#id 가 속한 section 의 innerBox 반환."""
    h2 = soup.find("h2", id=h2_id)
    if not h2:
        return None, False
    logged_out = "hidden-list" in (h2.get("class") or [])
    sec = h2.find_parent("section")
    return sec, logged_out


def parse_references(soup) -> list[dict]:
    sec, _ = _section(soup, "refeList")
    out = []
    if not sec:
        return out
    for i, p in enumerate(sec.select("p.ref"), 1):
        text = clean(p.get_text(" "))
        # 선행 번호 제거
        text = re.sub(r"^\d+\.\s*", "", text)
        typ = ""
        st = p.find("strong")
        if st:
            mt = re.search(r"\[([^\]]+)\]", st.get_text())
            if mt:
                typ = mt.group(1)
        art = ""
        a = p.find("a", href=re.compile(r"artiId=ART"))
        if a:
            ma = re.search(r"artiId=(ART\d+)", a["href"])
            art = ma.group(1) if ma else ""
        out.append({"n": i, "type": typ, "art_id": art, "text": text})
    return out


def parse_cited_by(soup) -> list[dict]:
    sec, _ = _section(soup, "listCita")
    out = []
    if not sec:
        return out
    for subj in sec.select("a.subject"):
        title = clean(subj.get_text())
        # 행 컨테이너
        row = subj
        for _ in range(5):
            row = row.parent
            if row and row.find("a", href=re.compile(r"cretId=CRT")):
                break
        block = str(row) if row else ""
        art = re.search(r"artiId=(ART\d+)", block)
        crt = re.search(r"cretId=(CRT\d+)", block)
        rowtext = clean(row.get_text(" | ")) if row else ""
        # 메타: 발행연월, 페이지, 피인용수
        date = re.search(r"(\d{4}\.\d{2})", rowtext)
        pages = re.search(r"(\d+)\s*~\s*(\d+)", rowtext)
        cc = re.search(r"피인용횟수\s*:?\s*\|?\s*(\d+)", rowtext)
        # 저자/저널: 제목 다음 a 들
        anchors = [clean(a.get_text()) for a in row.find_all("a")
                   if clean(a.get_text()) and "subject" not in (a.get("class") or [])] if row else []
        out.append({
            "art_id": art.group(1) if art else "",
            "crt_id": crt.group(1) if crt else "",
            "title": title,
            "authors": anchors[:1],
            "journal": anchors[1] if len(anchors) > 1 else "",
            "pub_date": date.group(1) if date else "",
            "pages": f"{pages.group(1)}~{pages.group(2)}" if pages else "",
            "cited_count": int(cc.group(1)) if cc else 0,
        })
    return out


def parse_detail(html: str, base: dict) -> dict:
    soup = BeautifulSoup(html, "lxml")
    rec = dict(base)

    # --- 영문 메타 (구조화·신뢰도 높음) ---
    rec["title_en"] = _meta(soup, "citation_title")
    rec["journal_en"] = _meta(soup, "citation_journal_title")
    rec["publisher_en"] = _meta(soup, "citation_publisher")
    rec["doi"] = _meta(soup, "citation_doi")
    rec["issn"] = _meta(soup, "citation_issn")
    rec["volume"] = _meta(soup, "citation_volume")
    rec["issue"] = _meta(soup, "citation_issue")
    rec["page_start"] = _meta(soup, "citation_firstpage")
    rec["page_end"] = _meta(soup, "citation_lastpage")
    rec["pub_year"] = _meta(soup, "citation_publication_date")
    kw_en = _meta(soup, "citation_keywords")
    rec["keywords_en"] = [clean(k) for k in kw_en.split(";") if _kw_ok(k)]
    rec["authors_en"] = [clean(m["content"]) for m in
                         soup.find_all("meta", attrs={"name": "citation_author"})
                         if m.get("content")]

    # --- 국문 본문 ---
    at = soup.find(id="artiTitle")
    rec["title_ko"] = clean(at.get_text()) if at else (
        clean(soup.title.get_text()) if soup.title else "")
    ka = soup.find(id="korAbst")
    rec["abstract_ko"] = clean(ka.get_text()) if ka else ""
    ea = soup.find(id="engAbst")
    rec["abstract_en"] = clean(ea.get_text()) if ea else ""

    pj = soup.find("p", class_="jounal")           # (KCI 오타: jounal)
    rec["journal_ko"] = clean(pj.get_text()) if pj else ""
    pp = soup.find("p", class_="pub")
    rec["publisher_ko"] = clean(re.sub(r"^발행기관\s*:?\s*", "", pp.get_text())) if pp else ""
    pv = soup.find("p", class_="vol")
    rec["pub_vol_raw"] = clean(pv.get_text()) if pv else ""

    # 저자(국문) — div.author 의 저자 링크("최창헌 /Choi, Chang-Heon" → 국문부)
    authors_ko = []
    adiv = soup.find("div", class_="author")
    if adiv:
        for a in adiv.find_all("a"):
            t = clean(a.get_text())
            if not t or re.search(r"orcid|바로가기|바로보기", t, re.I):
                continue   # ORCID 등 저자 아닌 링크 제외
            ko = clean(t.split("/")[0])
            if ko:
                authors_ko.append(ko)
    rec["authors_ko"] = authors_ko

    # 소속 — div.attach. "1 상지대학교" 또는 공저 "1 부경대학교 2 한림대학교".
    # 번호 마커(앞/중간) 기준으로 분리하고 중복 제거.
    affils = []
    for at_div in soup.find_all("div", class_="attach"):
        raw = clean(at_div.get_text(" "))
        for part in re.split(r"\s*\b\d+\s+", raw):   # 선행/중간 번호로 분할
            t = clean(part)
            if t and t not in affils:
                affils.append(t)
    rec["affiliations"] = affils

    # 연구분야(논문 세부분류)
    sub = soup.find("div", class_="subject")
    if sub:
        ft = re.sub(r"^연구분야\s*:?\s*", "", clean(sub.get_text(" ")))
        ft = re.sub(r"이 분야로[^>]*", "", ft)
        rec["research_field"] = clean(re.sub(r"\s*>\s*", " > ", ft)).strip(" >")
    else:
        rec["research_field"] = ""

    # 키워드(국문): 각 키워드는 <a id="keywd">...</a> (도우미 링크 ico_* 는 별도).
    rec["keywords_ko"] = [clean(a.get_text()) for a in soup.find_all("a", id="keywd")
                          if _kw_ok(a.get_text())]

    # 피인용/FWCI/열람수
    cited = fwci = ""
    view = ""
    for li in soup.select("div.numbox li"):
        strong = li.find("strong")
        cnt = li.find("span", class_="right-count")
        if not strong or not cnt:
            continue
        label = clean(strong.get_text())
        val = clean(cnt.get_text())
        if label == "KCI":
            mm = re.search(r"(\d+)", val)
            cited = mm.group(1) if mm else ""
        elif label == "FWCI":
            mm = re.search(r"([\d.]+)\s*$", val)
            fwci = mm.group(1) if mm else ""
    mv = soup.find("span", class_="colorRed")
    if mv:
        mm = re.search(r"([\d,]+)", mv.get_text())
        view = mm.group(1).replace(",", "") if mm else ""
    rec["cited_count"] = int(cited) if cited.isdigit() else 0
    rec["fwci"] = fwci
    rec["view_count"] = int(view) if view.isdigit() else 0

    # crt_id (자기 자신) - 검색 단계 값이 없으면 본문에서 보강
    if not rec.get("crt_id"):
        mc = re.search(rf"cretId=(CRT\d+)&citationBean.artiId={rec['art_id']}", html)
        rec["crt_id"] = mc.group(1) if mc else ""

    # 인용현황
    rec["references"] = parse_references(soup)
    rec["cited_by"] = parse_cited_by(soup)
    rec["ref_count"] = len(rec["references"])
    rec["citing_count"] = len(rec["cited_by"])
    rec["pages"] = (f"{rec['page_start']}~{rec['page_end']}"
                    if rec["page_start"] and rec["page_end"] else "")
    return rec


def is_logged_out(html: str) -> bool:
    """피인용 횟수가 있는데 인용 섹션이 잠겨(hidden-list) 있으면 로그아웃."""
    soup = BeautifulSoup(html, "lxml")
    h2 = soup.find("h2", id="refeList")
    if h2 is None:
        return False
    return "hidden-list" in (h2.get("class") or [])


# ----------------------------------------------------------------------------
# 5. 한 논문 처리
# ----------------------------------------------------------------------------
def process_article(client: httpx.Client, base: dict) -> dict:
    art_id = base["art_id"]
    for attempt in range(2):
        r = http_get(client, ARTI_VIEW + art_id)
        if is_logged_out(r.text) and attempt == 0:
            relogin(client)
            continue
        return parse_detail(r.text, base)
    return parse_detail(r.text, base)


# ----------------------------------------------------------------------------
# 체크포인트
# ----------------------------------------------------------------------------
_ckpt_lock = threading.Lock()


def load_done(ckpt: str) -> set:
    done = set()
    if os.path.exists(ckpt):
        with open(ckpt, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["article_id"])
                except Exception:  # noqa
                    pass
    return done


def append_ckpt(rec: dict, ckpt: str):
    with _ckpt_lock:
        with open(ckpt, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------
# 저장
# ----------------------------------------------------------------------------
LIST_COLS = ["authors_ko", "authors_en", "affiliations", "keywords_ko",
             "keywords_en", "references", "cited_by"]
COL_ORDER = [
    "article_id", "crt_id", "sere_id",
    "title_ko", "title_en", "journal_ko", "journal_en",
    "publisher_ko", "publisher_en", "pub_year", "pub_date",
    "volume", "issue", "pages", "page_start", "page_end",
    "doi", "issn", "research_field", "journal_field",
    "authors_ko", "authors_en", "affiliations",
    "abstract_ko", "abstract_en", "keywords_ko", "keywords_en",
    "cited_count", "fwci", "view_count", "ref_count", "citing_count",
    "references", "cited_by",
]


def save_outputs(ckpt: str, out_csv: str, out_pkl: str):
    if not os.path.exists(ckpt):
        print("저장할 레코드 없음(체크포인트 파일 없음).")
        return
    records = []
    with open(ckpt, "r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:  # noqa
                pass
    if not records:
        print("저장할 레코드 없음.")
        return
    df = pd.DataFrame(records)
    # 컬럼 순서 정리
    cols = [c for c in COL_ORDER if c in df.columns] + \
           [c for c in df.columns if c not in COL_ORDER]
    df = df[cols]
    # pickle: 객체 그대로
    df.to_pickle(out_pkl)
    # CSV: 중첩 데이터는 JSON 문자열로
    dfc = df.copy()
    for c in LIST_COLS:
        if c in dfc.columns:
            dfc[c] = dfc[c].apply(lambda v: json.dumps(v, ensure_ascii=False)
                                  if isinstance(v, (list, dict)) else v)
    dfc.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {len(df):,}건")
    print(f"  CSV : {out_csv}")
    print(f"  PKL : {out_pkl}")


# ----------------------------------------------------------------------------
# 메인
# ----------------------------------------------------------------------------
def run(limit: int = 0):
    """limit>0 이면 처음 limit 편만 수집해 _sample.csv 생성(스모크 테스트)."""
    sample = limit > 0
    ckpt = SAMPLE_CKPT if sample else CKPT
    out_csv, out_pkl = (SAMPLE_CSV, SAMPLE_PKL) if sample else (OUT_CSV, OUT_PKL)

    if not KCI_ID or not KCI_PW:
        sys.exit("KCI 자격증명이 없습니다. kci_config.py 를 확인하세요.")
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 60)
    print("KCI 한국어와문학 논문 수집기 (2008~2024)" +
          (f"  [샘플 {limit}편]" if sample else ""))
    print("=" * 60)
    if sample and os.path.exists(ckpt):
        os.remove(ckpt)  # 샘플은 매번 새로

    # 1) 로그인
    print("\n[1/5] Selenium 로그인...")
    cookies = selenium_login()
    print(f"  로그인 성공. 쿠키: {list(cookies.keys())}")

    client = httpx.Client(verify=False, headers=HEADERS, follow_redirects=True,
                          timeout=TIMEOUT)
    apply_cookies(client, cookies)
    try:
        client.get(SEARCH_ARTI_PAGE, timeout=TIMEOUT)  # 세션 워밍업
    except Exception:  # noqa
        pass

    # 2) 학술지 해석  (샘플은 앞쪽 몇 개만 해석해 빠르게)
    print("\n[2/5] 한국어와문학 학술지 해석...")
    journals = resolve_journals(client, max_journals=3 if sample else None)
    print(f"  대상 학술지: {len(journals)}개" + ("" if sample else f"  (목록: {JOURNALS_CSV})"))

    # 3) 논문 열거 (샘플이면 limit 채우는 즉시 중단)
    print("\n[3/5] 학술지별 논문 열거...")
    all_articles = []
    for j in tqdm(journals, desc="논문 열거", unit="저널"):
        try:
            arts = enumerate_articles(client, j)
        except Exception as e:  # noqa
            tqdm.write(f"  [경고] {j['name']} 열거 실패: {e}")
            continue
        for a in arts:
            a["journal_field"] = TARGET_FIELD
            a["journal_name"] = j["name"]
        all_articles.extend(arts)
        tqdm.write(f"  {j['name']}: {len(arts):,}건")
        if sample and len(all_articles) >= limit:
            break
    if sample:
        # 검색은 최신순이므로 끝쪽(가장 오래된) limit 편을 샘플로 → 인용현황이 확정돼
        # cited_by 가 채워진 대표성 있는 데이터를 확인할 수 있음.
        all_articles = all_articles[-limit:]
    print(f"  총 논문: {len(all_articles):,}건")

    # 4) 상세 수집 (resume)
    done = load_done(ckpt)
    todo = [a for a in all_articles if a["art_id"] not in done]
    print(f"\n[4/5] 상세 수집  (전체 {len(all_articles):,} / 완료 {len(done):,} / "
          f"잔여 {len(todo):,})")

    workers = min(MAX_WORKERS, max(1, len(todo))) if sample else MAX_WORKERS
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(process_article, client,
                          {"art_id": a["art_id"], "crt_id": a.get("crt_id", ""),
                           "sere_id": a["sere_id"],
                           "journal_field": a["journal_field"]}): a
                for a in todo}
        bar = tqdm(total=len(todo), desc="논문 상세", unit="편", smoothing=0.05)
        errors = 0
        for fut in as_completed(futs):
            a = futs[fut]
            try:
                rec = fut.result()
                rec["article_id"] = rec.pop("art_id")
                append_ckpt(rec, ckpt)
                bar.set_postfix_str(f"{a['journal_name'][:10]} | err {errors}")
            except Exception as e:  # noqa
                errors += 1
                tqdm.write(f"  [실패] {a['art_id']}: {e}")
            bar.update(1)
        bar.close()
    print(f"  완료. 실패 {errors}건")

    # 5) 저장
    print("\n[5/5] CSV / pickle 저장...")
    client.close()
    save_outputs(ckpt, out_csv, out_pkl)
    if sample:
        print(f"\n>> 샘플을 확인하세요: {out_csv}")
        print("   확인 후 전체 실행:  python scrape_korlit.py")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="KCI 한국어와문학 논문 수집기")
    ap.add_argument("--limit", type=int, default=0,
                    help="처음 N편만 수집해 _sample.csv 생성(스모크 테스트). 예: --limit 10")
    args = ap.parse_args()
    run(limit=args.limit)


if __name__ == "__main__":
    main()
