# -*- coding: utf-8 -*-
"""한 학술지의 피인용/참고문헌 인용 통계 (분과 포함).
사용: python build_journal_citation_stats.py <sereId>   (기본 000769 = 상허학보)
  - 피인용(incoming): 그 학술지를 인용한 학술지들 (cited_by.journal)
  - 참고문헌(outgoing): 그 학술지가 인용한 학술지들 (references 학술지형 text)
  - 학술지종수.xls 의 대분류/중분류(분과) 부착
출력: Data/한국어와문학_결과2/통계/<학술지>_인용통계/
  이웃학술지.csv (학술지별 피인용·참고문헌·합계·분과)
  분과별요약.csv (대분류별 피인용 vs 참고문헌)
  README.md (요약 수치)
"""
import sys, io, os, csv, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import Counter
import pandas as pd

BASE = "Data/한국어와문학_결과2"
SERE_ID = sys.argv[1] if len(sys.argv) > 1 else "000769"
_cut = re.compile(r"\s*[\d０-９(（].*$")
_nm = lambda s: re.sub(r"\s+", "", str(s or "")).lower()
ref_journal = lambda t: _cut.sub("", t.split(" / ")[-1].split(" : ")[0]).strip()

# 분과 맵 (xls) — 한글명(col4)·외국어명(col5)·괄호앞부분('X(구 Y)'→'X')으로 색인해
# 구표기/병기 차이로 빠지던 KCI 학술지(예: 한민족어문학·사회와역사)를 회복.
disc = {}
xls = pd.read_excel("학술지종수.xls", header=None, engine="xlrd").iloc[2:]
for _, x in xls.iterrows():
    d = (str(x[8]).strip(), str(x[9]).strip())
    keys = {_nm(x[4]), _nm(x[5]), _nm(str(x[4]).split("(")[0])}
    for k in keys:
        if k and k not in disc:
            disc[k] = d

df = pd.read_pickle(f"{BASE}/korlit_2008_2024.pkl")
jour = df[df["sere_id"] == SERE_ID]
CENTER = jour["journal_ko"].mode().iloc[0] if len(jour) else SERE_ID
SELF = {_nm(CENTER), _nm(CENTER.split("(")[0])}
safe = "".join(c for c in CENTER if c.isalnum() or c in "()_-")
OUT = f"{BASE}/통계/{safe}_인용통계"
os.makedirs(OUT, exist_ok=True)

inc, out = Counter(), Counter()
self_in = self_out = 0
for _, r in jour.iterrows():
    for cb in (r["cited_by"] or []):
        j = (cb.get("journal") or "").strip()
        if not j:
            continue
        if _nm(j) in SELF:
            self_in += 1
        else:
            inc[j] += 1
    for ref in (r["references"] or []):
        if "학술지" in (ref.get("type") or ""):
            j = ref_journal(ref.get("text", ""))
            if j and len(j) >= 2:
                if _nm(j) in SELF:
                    self_out += 1
                else:
                    out[j] += 1

# 이웃 학술지 표 — KCI 학술지(xls에서 분과 매칭되는 것)만. 비KCI(문예지·역사잡지 등)는 제외.
allj = set(inc) | set(out)
rows, drop_in, drop_out = [], 0, 0
for j in allj:
    d = disc.get(_nm(j))
    if d is None:                       # xls 미등재(문예지·잡지 등) → 제외
        drop_in += inc.get(j, 0); drop_out += out.get(j, 0)
        continue
    rows.append({"학술지": j, "대분류": d[0], "중분류": d[1],
                 "피인용(받은_인용)": inc.get(j, 0),
                 "참고문헌(한_인용)": out.get(j, 0),
                 "합계": inc.get(j, 0) + out.get(j, 0)})
rows.sort(key=lambda r: -r["합계"])
fields = ["학술지", "대분류", "중분류", "피인용(받은_인용)", "참고문헌(한_인용)", "합계"]
with open(f"{OUT}/이웃학술지.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

# 분과별 요약 (대분류) — KCI 매칭된 학술지만(비KCI 문예지·잡지 제외)
maj_in, maj_out = Counter(), Counter()
for j, n in inc.items():
    d = disc.get(_nm(j))
    if d:
        maj_in[d[0]] += n
for j, n in out.items():
    d = disc.get(_nm(j))
    if d:
        maj_out[d[0]] += n
majs = sorted(set(maj_in) | set(maj_out), key=lambda m: -(maj_in[m] + maj_out[m]))
y2 = [{"대분류": m, "피인용": maj_in[m], "참고문헌": maj_out[m],
       "합계": maj_in[m] + maj_out[m]} for m in majs]
with open(f"{OUT}/분과별요약.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["대분류", "피인용", "참고문헌", "합계"]); w.writeheader(); w.writerows(y2)

tot_in, tot_out = sum(inc.values()), sum(out.values())
readme = f"""# {CENTER} 인용 통계 (2008~2024) — KCI 학술지 한정

- 대상 논문: **{len(jour):,}편** ({CENTER}, sereId {SERE_ID})
- **피인용(받은 인용)**: KCI 학술지 기준 **{tot_in - drop_in:,}건**({len(rows)}종 중 피인용有) (+ 자기인용 {self_in:,})
- **참고문헌(한 인용)**: KCI 학술지 기준 **{tot_out - drop_out:,}건** (+ 자기인용 {self_out:,})
- **제외된 비KCI 인용**(문예지·역사잡지·단행본성 정기간행물 등, xls 미등재): 피인용 {drop_in:,} · 참고문헌 {drop_out:,}건
  ※ 매칭은 학술지명 기준(한글명·외국어명·구표기 괄호 보정 포함). 창작과비평·실천문학·사상계·개벽 등 *문학/역사 잡지*는 KCI 학술지가 아니라 제외됨(1차자료 인용).

## 파일
| 파일 | 내용 |
|---|---|
| `이웃학술지.csv` | 학술지별 피인용·참고문헌·합계 + 대분류/중분류(분과). 합계 내림차순. |
| `분과별요약.csv` | 대분류별 피인용 vs 참고문헌 합계 |

## 분과(대분류)별 — 피인용 / 참고문헌
| 대분류 | 피인용 | 참고문헌 | 합계 |
|---|---|---|---|
""" + "\n".join(f"| {r['대분류']} | {r['피인용']:,} | {r['참고문헌']:,} | {r['합계']:,} |" for r in y2[:10]) + f"""

## 주의
- 매칭은 학술지명 기준. 한자/영문 등재명 일부는 분과가 `(미상)`일 수 있음.
- 참고문헌은 reference 중 '학술지(연속간행물)'형만(단행본·학위논문 등 제외).
- 자기인용은 위 수치에서 제외.
"""
open(f"{OUT}/README.md", "w", encoding="utf-8").write(readme)

print(f"=== {CENTER} (논문 {len(jour)}편) ===")
print(f"피인용 합 {tot_in:,} ({len(inc)}종) · 참고문헌 합 {tot_out:,} ({len(out)}종)")
print(f"저장: {OUT}/")
print("\n[분과별 — 피인용/참고문헌]")
for r in y2[:8]:
    print(f"  {r['대분류']:8s} 피인용 {r['피인용']:>6,} · 참고문헌 {r['참고문헌']:>6,}")
print("\n[합계 Top 12 학술지]")
for r in rows[:12]:
    print(f"  합{r['합계']:>4} (피{r['피인용(받은_인용)']:>4}/참{r['참고문헌(한_인용)']:>4})  {r['학술지'][:20]:22s}[{r['대분류']}]")
