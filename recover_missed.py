# -*- coding: utf-8 -*-
"""누락 학술지 복구.

학술지명(SERE_NM) 검색은 등재명이 한자/영문이면 0건을 반환해, 國語學(국어학)·
漢字漢文敎育 등 일부 학술지가 누락됐다. 이들은 KCI 분류검색의 sereId 기반(이름 무관)
3단계 열거로 복구한다:
    ciSereYrClasList(insiId,sereId)            -> 연도(pubiYr)
    ciSereVolIsseClasList(insiId,sereId,year)  -> 호(volIsseId)
    poSereArtiList(sereId, volIsseId)          -> 논문(artiId)
얻은 art_id 를 기존 파이프라인(process_article)으로 상세수집해 같은 체크포인트에 적재한 뒤
결과물(csv/pkl/건수표)을 재생성한다.
"""
import re, time, json, csv as _csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import scrape_korlit as sk
from tqdm import tqdm

CLAS = "https://www.kci.go.kr/kciportal/ci/clasSearch/"
YR = CLAS + "ciSereYrClasList.kci?clasSearchBean.insiId=%s&clasSearchBean.sereId=%s"
ISSUE = CLAS + "ciSereVolIsseClasList.kci?clasSearchBean.insiId=%s&clasSearchBean.sereId=%s&clasSearchBean.pubiYr=%s"
ARTI = sk.BASE + "/kciportal/po/search/poSereArtiList.kci?sereId=%s&volIsseId=%s"

# sereId 기반으로 확인된 누락 학술지(2008~2024 논문 보유)
MISSED = [
    {"name": "국어학",          "sere_id": "000064",       "insi_id": "INS000001359"},
    {"name": "한자한문교육",     "sere_id": "001732",       "insi_id": "INS000000945"},
    {"name": "한국어와 문화",    "sere_id": "SER000014361", "insi_id": "INS000004785"},
]


def enum_by_sereid(client, j):
    """sereId 기반 3단계 열거로 2008~2024 art_id 목록 반환."""
    insi, sere = j["insi_id"], j["sere_id"]
    yrs = re.findall(r"pubiYr'><!\[CDATA\[(\d{4})", sk.http_get(client, YR % (insi, sere)).text)
    yrs = sorted({y for y in yrs if sk.START_YEAR <= int(y) <= sk.END_YEAR})
    art_ids, crt = [], {}
    for y in yrs:
        vt = sk.http_get(client, ISSUE % (insi, sere, y)).text
        for vol in dict.fromkeys(re.findall(r"(VOL\d+)", vt)):
            at = sk.http_get(client, ARTI % (sere, vol)).text
            soup = sk.BeautifulSoup(at, "lxml")
            for a in soup.select("a[href*='artiId=ART']"):
                m = re.search(r"artiId=(ART\d+)", a["href"])
                if not m:
                    continue
                aid = m.group(1)
                if aid not in crt:
                    crt[aid] = ""
                    art_ids.append(aid)
            # crt_id 보강: poCretDetail 링크
            for m in re.finditer(r"cretId=(CRT\d+)&[^\"']*artiId=(ART\d+)", at):
                crt[m.group(2)] = m.group(1)
            time.sleep(0.3)
    return [{"art_id": a, "crt_id": crt.get(a, ""), "sere_id": sere} for a in art_ids]


def main():
    print("누락 학술지 복구 시작...")
    cookies = sk.selenium_login()
    client = sk.httpx.Client(verify=False, headers=sk.HEADERS, follow_redirects=True,
                             timeout=sk.TIMEOUT)
    sk.apply_cookies(client, cookies)
    try:
        client.get(sk.SEARCH_ARTI_PAGE, timeout=sk.TIMEOUT)
    except Exception:
        pass

    done = sk.load_done(sk.CKPT)
    todo = []
    for j in MISSED:
        arts = enum_by_sereid(client, j)
        new = [a for a in arts if a["art_id"] not in done]
        for a in new:
            a["journal_field"] = sk.TARGET_FIELD
            a["journal_name"] = j["name"]
        todo += new
        print(f"  {j['name']}: 열거 {len(arts)}건 / 신규 {len(new)}건")
    print(f"복구 대상 총 {len(todo)}건 상세수집...")

    with ThreadPoolExecutor(max_workers=sk.MAX_WORKERS) as ex:
        futs = {ex.submit(sk.process_article, client,
                          {"art_id": a["art_id"], "crt_id": a.get("crt_id", ""),
                           "sere_id": a["sere_id"], "journal_field": a["journal_field"]}): a
                for a in todo}
        bar = tqdm(total=len(todo), desc="복구 상세", unit="편")
        err = 0
        for fut in as_completed(futs):
            try:
                rec = fut.result()
                rec["article_id"] = rec.pop("art_id")
                sk.append_ckpt(rec, sk.CKPT)
            except Exception as e:  # noqa
                err += 1
                tqdm.write(f"  [실패] {futs[fut]['art_id']}: {e}")
            bar.update(1)
        bar.close()
    client.close()
    print(f"복구 상세수집 완료(실패 {err}). 결과물 재생성...")
    sk.save_outputs(sk.CKPT, sk.OUT_CSV, sk.OUT_PKL)


if __name__ == "__main__":
    main()
