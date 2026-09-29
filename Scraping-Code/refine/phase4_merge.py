# -*- coding: utf-8 -*-
"""Phase 4: cited_by 의 journal/분과를 art_id 기준으로 재구축 + 분과 매핑.

입력:
  - korlit_2008_2024.pkl                (원본)
  - 문제점/_internal_resolved.json       (내부 A11 art_id -> 저널정보)
  - 문제점/_external_cache.jsonl         (외부 art_id -> KCI 조회 저널정보)
  - 학술지종수.xls                       (저널명/ISSN -> 대분류·중분류)

처리:
  각 cited_by 항목에 신설 필드를 추가(원본 journal 보존):
    journal_clean   정제 저널명 (art_id 기준 재도출)
    field_major     대분류 (분과)
    field_minor     중분류
    resolve_src     internal | external | external_nojournal | external_fail | no_artid

출력:
  Data/한국어와문학_결과2/korlit_2008_2024_clean.pkl / .csv  (gitignore 대상)
"""
import sys, io, os, re, json, pandas as pd
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
D = config.ACTIVE

PKL = D.pkl
OUT_PKL = D.clean_pkl
OUT_CSV = D.clean_csv
XLS = config.JOURNAL_FIELD_XLS
INTERNAL = D.internal_resolved
EXT_CACHE = D.ext_cache
HOME_MINOR = D.name          # home 분과(중분류) = 현재 분과. 영향수출 = home 밖 인용

_nm = lambda s: re.sub(r"\s+", "", str(s or "")).lower()
def strip_pub(s):  # '발행기관 : X' / '발행기관：X' -> 'X'
    return re.sub(r"^발행기관\s*[:：]?\s*", "", str(s or "")).strip()

# --- 1) 학술지종수.xls -> 분과 매핑 (한글명/영문명/ISSN 다중키) ---
print("학술지종수.xls 로드...")
xls = pd.read_excel(XLS, header=None, engine="xlrd").iloc[2:]
by_name, by_issn = {}, {}
for x in xls.itertuples(index=False):
    major, minor = str(x[8]).strip(), str(x[9]).strip()
    if not major or major == "nan":
        continue
    fld = (major, minor)
    for nm in (_nm(x[4]), _nm(x[5])):          # 한글명, 영문명
        if nm and nm != "nan":
            by_name.setdefault(nm, fld)
    for iss in (str(x[6]).strip(), str(x[7]).strip()):  # P-ISSN, E-ISSN
        if iss and iss != "nan":
            by_issn.setdefault(iss, fld)
print(f"  분과맵: 이름 {len(by_name):,}키 / ISSN {len(by_issn):,}키")

def map_field(journal_ko, journal_en=""):
    for nm in (_nm(journal_ko), _nm(journal_en)):
        if nm and nm in by_name:
            return by_name[nm]
    return ("", "")

# --- 2) 내부/외부 해소 맵 ---
internal = json.load(open(INTERNAL, encoding="utf-8"))
print(f"내부 맵: {len(internal):,}")
ext = {}
n_extfail = 0
with open(EXT_CACHE, encoding="utf-8") as f:
    for line in f:
        try: r = json.loads(line)
        except Exception: continue
        ext[r["art_id"]] = r
        if not r.get("ok"): n_extfail += 1
print(f"외부 캐시: {len(ext):,}  (fail {n_extfail:,})")

# --- 3) cited_by 재구축 ---
df = pd.read_pickle(PKL)
src_cnt = Counter()
ext_matched = ext_unmatched = 0
for cb in df.cited_by:
    if not isinstance(cb, (list, tuple)):
        continue
    for c in cb:
        if not isinstance(c, dict):
            continue
        aid = str(c.get("art_id") or "").strip()
        jk = je = ""
        major = minor = ""
        if not aid:
            src = "no_artid"
        elif aid in internal:
            info = internal[aid]
            jk = info["journal_ko"]
            jf = info.get("journal_field", "")              # "인문학 > 한국어와문학"
            parts = [p.strip() for p in jf.split(">")]
            major = parts[0] if parts else "인문학"
            minor = parts[1] if len(parts) > 1 else HOME_MINOR
            src = "internal"
        elif aid in ext and ext[aid].get("ok"):
            r = ext[aid]
            jk, je = r.get("journal_ko", ""), r.get("journal_en", "")
            if not (jk or je):
                src = "external_nojournal"
            else:
                major, minor = map_field(jk, je)
                if major:
                    src = "external"; ext_matched += 1
                else:
                    src = "external_nomatch"; ext_unmatched += 1
        else:
            src = "external_fail"
        c["journal_clean"] = jk or je
        c["field_major"] = major
        c["field_minor"] = minor
        c["resolve_src"] = src
        src_cnt[src] += 1

print("\n=== cited_by 항목 해소 출처 ===")
tot = sum(src_cnt.values())
for k, n in src_cnt.most_common():
    print(f"  {k:20s} {n:>8,} ({n/tot*100:4.1f}%)")
ext_tot = ext_matched + ext_unmatched
if ext_tot:
    print(f"  └ 외부 분과매칭률: {ext_matched/ext_tot*100:.1f}% ({ext_matched:,}/{ext_tot:,})")

# --- 4) 영향수출(외부 피인용) 재집계: 중분류 != 한국어와문학 ---
ext_cite_papers = set()      # 외부분과가 인용한 A11 논문(article_id)
ext_by_field = Counter()
for r in df.itertuples(index=False):
    for c in (r.cited_by or []):
        if not isinstance(c, dict):
            continue
        minor = c.get("field_minor", "")
        major = c.get("field_major", "")
        if major and minor != HOME_MINOR:        # 분과 식별됐고 home 밖
            ext_cite_papers.add(r.article_id)
            ext_by_field[f"{major} > {minor}"] += 1
print(f"\n=== 영향수출(외부 피인용) 재집계 ===")
print(f"외부분과에 인용된 {D.name} 논문 수: {len(ext_cite_papers):,}")
print("외부 피인용 상위 분과(중분류 기준, 인용 건수):")
for f, n in ext_by_field.most_common(12):
    print(f"  {n:>6,}  {f}")

# --- 5) 저장 ---
print("\n저장 중...")
os.makedirs(D.out_dir, exist_ok=True)
df.to_pickle(OUT_PKL)
LIST_COLS = ["authors_ko","authors_en","affiliations","keywords_ko","keywords_en","references","cited_by"]
dfc = df.copy()
for col in LIST_COLS:
    if col in dfc.columns:
        dfc[col] = dfc[col].apply(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v,(list,dict)) else v)
dfc.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
print(f"  PKL: {OUT_PKL}")
print(f"  CSV: {OUT_CSV}")
