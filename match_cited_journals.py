# -*- coding: utf-8 -*-
"""학술지종수.xls(KCI 전체 학술지 6,339종 + 분과)와 우리 인용 데이터를 매칭.
'우리 데이터의 인용 네트워크에 등장한 학술지'가 xls 목록의 어느 것이고, 분과가 뭔지 집계.
  - 피인용(incoming): cited_by.journal — 우리 논문을 인용한 학술지
  - 참고문헌(outgoing): references(학술지형) text 에서 추출 — 우리 논문이 인용한 학술지
출력: Data/한국어와문학_결과2/통계/10_인용학술지_분과매칭.csv
"""
import sys, io, csv, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import Counter
import pandas as pd

BASE = "Data/한국어와문학_결과2"
PKL = f"{BASE}/korlit_2008_2024.pkl"
XLS = "학술지종수.xls"
OUT = f"{BASE}/통계/10_인용학술지_분과매칭.csv"
_cut = re.compile(r"\s*[\d０-９(（].*$")
_nm = lambda s: re.sub(r"\s+", "", str(s or "")).lower()


def ref_journal(text):
    seg = text.split(" / ")[-1].split(" : ")[0]
    return _cut.sub("", seg).strip()


# --- 우리 인용 데이터의 학술지 등장 횟수 ---
df = pd.read_pickle(PKL)
inc, out = Counter(), Counter()
for _, r in df.iterrows():
    for cb in (r["cited_by"] or []):
        j = (cb.get("journal") or "").strip()
        if j:
            inc[j] += 1
    for ref in (r["references"] or []):
        if "학술지" in (ref.get("type") or ""):
            j = ref_journal(ref.get("text", ""))
            if j and len(j) >= 2:
                out[j] += 1
# 정규화 이름 -> (피인용합, 참고문헌합)
cited_norm = Counter()
for j, n in inc.items():
    cited_norm[_nm(j)] += 0  # ensure key
inc_n, out_n = Counter(), Counter()
for j, n in inc.items():
    inc_n[_nm(j)] += n
for j, n in out.items():
    out_n[_nm(j)] += n
print(f"인용 데이터 등장 학술지(정규화): 피인용 {len(inc_n)}종 / 참고문헌 {len(out_n)}종")

# --- xls: KCI 전체 학술지 목록 + 분과 ---
xls = pd.read_excel(XLS, header=None, engine="xlrd")
xls = xls.iloc[2:]                                   # 0=주석, 1=헤더 제외
rows, seen = [], set()
for _, x in xls.iterrows():
    name = str(x[4]).strip()
    if not name or name == "nan":
        continue
    key = _nm(name)
    if key in seen:
        continue
    seen.add(key)
    i, o = inc_n.get(key, 0), out_n.get(key, 0)
    if i + o == 0:
        continue                                     # 인용 안 된 학술지는 제외
    rows.append({"학술지명": name, "대분류": str(x[8]).strip(), "중분류": str(x[9]).strip(),
                 "P-ISSN": str(x[6]).strip(), "피인용(우리논문을_인용)": i,
                 "참고문헌(우리논문이_인용)": o, "인용합계": i + o})
rows.sort(key=lambda r: -r["인용합계"])

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["학술지명", "대분류", "중분류", "P-ISSN",
                                      "피인용(우리논문을_인용)", "참고문헌(우리논문이_인용)", "인용합계"])
    w.writeheader(); w.writerows(rows)

# --- 요약 ---
total_xls = len(seen)
print(f"xls 전체 학술지(중복제거): {total_xls:,}종")
print(f"그중 우리 인용 데이터에 등장: {len(rows):,}종 ({100*len(rows)/total_xls:.1f}%)")
print(f"저장: {OUT}")
# 분과(대분류) 분포
maj = Counter()
for r in rows:
    maj[r["대분류"]] += r["인용합계"]
print("\n[인용된 학술지의 대분류 분포 — 인용합계 기준]")
for m, c in maj.most_common(12):
    print(f"  {c:>7,}  {m}")
print("\n[인용 합계 Top 15 학술지]")
for r in rows[:15]:
    print(f"  {r['인용합계']:>5}  {r['학술지명'][:22]:24s} [{r['대분류']}>{r['중분류']}]")
