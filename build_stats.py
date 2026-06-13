# -*- coding: utf-8 -*-
"""최종 데이터(korlit_2008_2024.pkl)의 종합 통계 산출.
출력: Data/한국어와문학_결과2/통계/  (각종 CSV + README.md)
"""
import os, sys, io, json, csv, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import Counter, defaultdict
import pandas as pd

BASE = "Data/한국어와문학_결과2"
OUT = f"{BASE}/통계"
os.makedirs(OUT, exist_ok=True)
df = pd.read_pickle(f"{BASE}/korlit_2008_2024.pkl")
N = len(df)
L = lambda x: len(x) if isinstance(x, list) else 0
cc = pd.to_numeric(df["cited_count"], errors="coerce").fillna(0)
citing = pd.to_numeric(df["citing_count"], errors="coerce").fillna(0)
yr = pd.to_numeric(df["pub_year"], errors="coerce")
refL = df["references"].apply(L)
cbL = df["cited_by"].apply(L)
ref_internal = df["references"].apply(
    lambda v: sum(1 for r in v if isinstance(r, dict) and r.get("art_id")) if isinstance(v, list) else 0)


def wcsv(name, rows, fields):
    with open(f"{OUT}/{name}", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


# 01 연도별
y01 = []
for y in sorted(yr.dropna().unique()):
    if 2008 <= y <= 2024:
        m = df[yr == y]
        ccy = pd.to_numeric(m["cited_count"], errors="coerce").fillna(0)
        y01.append({"연도": int(y), "논문수": len(m), "피인용합": int(ccy.sum()),
                    "논문당평균피인용": round(float(ccy.mean()), 2)})
wcsv("01_연도별.csv", y01, ["연도", "논문수", "피인용합", "논문당평균피인용"])

# 02 학술지별 (sere_id 기준, 이름 부착)
jname = {}
if os.path.exists(f"{BASE}/journals_a11.csv"):
    jname = {r["sere_id"]: r["name"] for r in csv.DictReader(open(f"{BASE}/journals_a11.csv", encoding="utf-8-sig"))}
y02 = []
for sid, g in df.groupby("sere_id"):
    ccx = pd.to_numeric(g["cited_count"], errors="coerce").fillna(0)
    nm = jname.get(sid) or (g["journal_ko"].mode().iloc[0] if len(g) else sid)
    y02.append({"학술지": nm, "sere_id": sid, "논문수": len(g), "피인용합": int(ccx.sum()),
                "논문당평균피인용": round(float(ccx.mean()), 2),
                "참고문헌합": int(g["references"].apply(L).sum())})
y02.sort(key=lambda r: -r["논문수"])
wcsv("02_학술지별.csv", y02, ["학술지", "sere_id", "논문수", "피인용합", "논문당평균피인용", "참고문헌합"])

# 03 피인용 분포 (구간 + 백분위)
buckets = [(0, 0), (1, 1), (2, 4), (5, 9), (10, 19), (20, 49), (50, 99), (100, 10**9)]
blab = ["0", "1", "2-4", "5-9", "10-19", "20-49", "50-99", "100+"]
y03 = []
for (lo, hi), lab in zip(buckets, blab):
    n = int(((cc >= lo) & (cc <= hi)).sum())
    y03.append({"피인용구간": lab, "논문수": n, "비율(%)": round(100*n/N, 1)})
wcsv("03_피인용분포.csv", y03, ["피인용구간", "논문수", "비율(%)"])
pct = {f"p{p}": float(cc.quantile(p/100)) for p in [50, 75, 90, 95, 99]}

# 04 최다 피인용 Top50
t = df.assign(_c=cc).sort_values("_c", ascending=False).head(50)
y04 = [{"순위": i+1, "피인용": int(r["_c"]), "연도": r["pub_year"], "학술지": r["journal_ko"],
        "제목": (r["title_ko"] or r["title_en"]), "저자": ", ".join(r["authors_ko"]) if isinstance(r["authors_ko"], list) else "",
        "DOI": r["doi"], "article_id": r["article_id"]} for i, (_, r) in enumerate(t.iterrows())]
wcsv("04_최다피인용_Top50.csv", y04, ["순위", "피인용", "연도", "학술지", "제목", "저자", "DOI", "article_id"])

# (저자별 통계는 동명이인 구분 불가(KRI 저자ID 미수집)로 제외 — 09 저자수분포만 제공)

# 06 키워드 Top150 (국문) — 띄어쓰기 변형 합산(예: '한국어교육'+'한국어 교육')
raw = Counter()
for v in df["keywords_ko"]:
    if isinstance(v, list):
        for k in v:
            k = (k or "").strip()
            if k:
                raw[k] += 1
groups = defaultdict(Counter)                 # 공백제거 키 -> {표기: 빈도}
for k, n in raw.items():
    groups[re.sub(r"\s+", "", k)][k] += n
merged = [(vs.most_common(1)[0][0], sum(vs.values())) for vs in groups.values()]
merged.sort(key=lambda x: -x[1])
y06 = [{"키워드": d, "빈도": n} for d, n in merged[:150]]
wcsv("06_키워드_Top150.csv", y06, ["키워드", "빈도"])

# 07 연구분야(세부분류) 분포
fc = Counter((r or "").strip() for r in df["research_field"] if (r or "").strip())
y07 = [{"연구분야": k, "논문수": n, "비율(%)": round(100*n/N, 1)} for k, n in fc.most_common(40)]
wcsv("07_연구분야분포.csv", y07, ["연구분야", "논문수", "비율(%)"])

# 08 데이터 품질(보유율)
def cov(col, islist=False):
    if islist:
        return round(100*(df[col].apply(L) > 0).mean(), 1)
    return round(100*df[col].astype(str).str.strip().replace("nan", "").ne("").mean(), 1)
y08 = [
    {"항목": "제목(국문) title_ko", "보유율(%)": cov("title_ko")},
    {"항목": "제목(영문) title_en", "보유율(%)": cov("title_en")},
    {"항목": "초록(국문) abstract_ko", "보유율(%)": cov("abstract_ko")},
    {"항목": "초록(영문) abstract_en", "보유율(%)": cov("abstract_en")},
    {"항목": "키워드(국문) keywords_ko", "보유율(%)": cov("keywords_ko", True)},
    {"항목": "키워드(영문) keywords_en", "보유율(%)": cov("keywords_en", True)},
    {"항목": "DOI", "보유율(%)": cov("doi")},
    {"항목": "발행기관 publisher_ko", "보유율(%)": cov("publisher_ko")},
    {"항목": "저자(국문) authors_ko", "보유율(%)": cov("authors_ko", True)},
    {"항목": "참고문헌 references", "보유율(%)": cov("references", True)},
    {"항목": "피인용목록 cited_by", "보유율(%)": cov("cited_by", True)},
]
wcsv("08_데이터품질.csv", y08, ["항목", "보유율(%)"])

# 09 저자 수 분포(단독/공저)
na = df["authors_ko"].apply(L)
y09 = [{"저자수": k, "논문수": int((na == k).sum()),
        "비율(%)": round(100*int((na == k).sum())/N, 1)} for k in range(0, 6)]
y09.append({"저자수": "6+", "논문수": int((na >= 6).sum()), "비율(%)": round(100*int((na >= 6).sum())/N, 1)})
wcsv("09_저자수분포.csv", y09, ["저자수", "논문수", "비율(%)"])

# 00 요약
summary = {
    "총_논문수": N,
    "학술지수_journals_a11": len(jname) or None,
    "학술지수_journal_ko표기": int(df["journal_ko"].nunique()),
    "발행연도_범위": f"{int(yr.min())}~{int(yr.max())} (대부분 2008~2024)",
    "피인용": {"합계": int(cc.sum()), "평균": round(float(cc.mean()), 2),
              "중앙값": float(cc.median()), "최대": int(cc.max()),
              "1회이상_피인용_논문수": int((cc > 0).sum()),
              "백분위": {k: round(v, 1) for k, v in pct.items()}},
    "참고문헌": {"총항목": int(refL.sum()), "논문당평균": round(float(refL.mean()), 1),
               "KCI내부_artid보유": int(ref_internal.sum())},
    "피인용목록_cited_by": {"총항목": int(cbL.sum()), "논문당평균": round(float(cbL.mean()), 1)},
    "인용네트워크_엣지_추정": int(ref_internal.sum()) + int(cbL.sum()),
    "공저_논문비율(%)": round(100*float((na >= 2).mean()), 1),
    "단독저자_비율(%)": round(100*float((na == 1).mean()), 1),
}
json.dump(summary, open(f"{OUT}/00_요약.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# README
readme = f"""# 한국어와문학 데이터셋 — 통계 (2008~2024)

대상: `../korlit_2008_2024.pkl` (= `../korlit_2008_2024.csv`), **총 {N:,}편**, 한국어와문학(A11) 115개 학술지.
산출일 기준 스냅샷. 모든 표는 UTF-8(BOM) CSV.

## 핵심 수치
- **총 논문 수**: {N:,}편 ({summary['발행연도_범위']})
- **학술지**: A11 분류 115종 (데이터상 journal_ko 표기 {summary['학술지수_journal_ko표기']}종 — 학술대회 자료 등 포함)
- **피인용**: 합계 {summary['피인용']['합계']:,}회 · 평균 {summary['피인용']['평균']} · 중앙값 {summary['피인용']['중앙값']:.0f} · 최대 {summary['피인용']['최대']} · 1회 이상 피인용 {summary['피인용']['1회이상_피인용_논문수']:,}편
- **참고문헌**: 총 {summary['참고문헌']['총항목']:,}건 (논문당 평균 {summary['참고문헌']['논문당평균']}건, 그중 KCI 등재논문 {summary['참고문헌']['KCI내부_artid보유']:,}건)
- **피인용 목록**: 총 {summary['피인용목록_cited_by']['총항목']:,}건 (논문당 평균 {summary['피인용목록_cited_by']['논문당평균']}건)
- **인용 네트워크 엣지(추정)**: 약 {summary['인용네트워크_엣지_추정']:,}개 (참고문헌 내 KCI논문 + 피인용목록)
- **공저 논문 비율**: {summary['공저_논문비율(%)']}% (단독저자 {summary['단독저자_비율(%)']}%)

## 파일 설명
| 파일 | 내용 |
|---|---|
| `00_요약.json` | 위 핵심 수치의 기계가독 버전 |
| `01_연도별.csv` | 연도별 논문수 · 피인용합 · 논문당 평균 피인용 |
| `02_학술지별.csv` | 학술지(sere_id)별 논문수 · 피인용합 · 평균 · 참고문헌합 |
| `03_피인용분포.csv` | 피인용 횟수 구간(0,1,2-4,…,100+)별 논문수·비율 |
| `04_최다피인용_Top50.csv` | 가장 많이 인용된 논문 Top50 (제목·저자·DOI·article_id) |
| `06_키워드_Top150.csv` | 국문 키워드 빈도 Top150 |
| `07_연구분야분포.csv` | 논문 세부 연구분야(예: 현대소설(국문학)) 분포 |
| `08_데이터품질.csv` | 항목별 보유율(초록·키워드·DOI 등) |
| `09_저자수분포.csv` | 논문당 저자 수 분포(단독/공저) |

## 주의
- **저자별 통계 미제공**: 데이터에 저자 이름만 있고 KCI 저자 고유번호(KRI)가 없어, 동명이인이 한 명으로 합쳐짐(예: '김영주' 187편 = 소속 42개 = 여러 명). 정확한 저자별 집계는 KRI ID 재수집 후에만 가능. (논문당 저자 '수' 분포는 `09_저자수분포.csv` 참고.)
- **피인용/참고문헌**은 수집 시점 KCI 기준. 최근 논문은 피인용 목록이 미확정일 수 있음(횟수 > 목록).
- **DOI 미보유**(구논문)는 빈 값 — 결측 아님.
- 피인용 백분위(p50~p99): {summary['피인용']['백분위']}
- 자세한 컬럼 정의는 `../COLUMNS.md` 참고.
"""
open(f"{OUT}/README.md", "w", encoding="utf-8").write(readme)

print("통계 산출 완료 →", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f)
print(f"\n총 {N:,}편 | 피인용합 {int(cc.sum()):,} | 참고문헌 {int(refL.sum()):,} | 공저 {summary['공저_논문비율(%)']}%")
