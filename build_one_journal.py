# -*- coding: utf-8 -*-
"""한 저널의 인용 지평도 — 개별 막대 차트.
사용: python build_one_journal.py <sereId> [TopN]
연결강도 = 들어오는 인용(cited_by.journal, 전분야) + 나가는 인용(reference text, 전분야).
출력: Data/한국어와문학_결과2/network_<저널>/landscape.png (+ neighbors.csv)
"""
import sys, io, csv, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import Counter
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

fp = "C:/Windows/Fonts/malgun.ttf"
font_manager.fontManager.addfont(fp)
matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

PKL = "Data/한국어와문학_결과2/korlit_2008_2024.pkl"
SERE_ID = sys.argv[1] if len(sys.argv) > 1 else "000452"
TOPN = int(sys.argv[2]) if len(sys.argv) > 2 else 20
_cut = re.compile(r"\s*[\d０-９(（].*$")


def ref_journal(text):
    seg = text.split(" / ")[-1].split(" : ")[0]
    return _cut.sub("", seg).strip()


df = pd.read_pickle(PKL)
jour = df[df["sere_id"] == SERE_ID]
CENTER = jour["journal_ko"].mode().iloc[0] if len(jour) else SERE_ID
safe = "".join(c for c in CENTER if c.isalnum() or c in "()_-")
OUT = f"Data/한국어와문학_결과2/network_{safe}"
os.makedirs(OUT, exist_ok=True)

# 자기인용 제외: 중심 저널의 국문/한자 표기 모두
_norm = lambda s: re.sub(r"\s+", "", s or "")
SELF = {_norm(CENTER), _norm(CENTER.split("(")[0])}
m = re.search(r"\(([^)]+)\)", CENTER)
if m:
    SELF.add(_norm(m.group(1)))
SELF |= {"語文研究", "語文硏究"} if "어문연구" in CENTER else set()

inc, out, self_in, self_out = Counter(), Counter(), 0, 0
for _, r in jour.iterrows():
    for cb in (r["cited_by"] or []):
        j = cb.get("journal")
        if not j:
            continue
        if _norm(j) in SELF:
            self_in += 1
        else:
            inc[j] += 1
    for ref in (r["references"] or []):
        if "학술지" in (ref.get("type") or ""):
            j = ref_journal(ref.get("text", ""))
            if j and len(j) >= 2:
                if _norm(j) in SELF:
                    self_out += 1
                else:
                    out[j] += 1
print(f"(자기인용 제외: 피인용 {self_in} / 인용 {self_out})")

allj = set(inc) | set(out)
rows = [{"journal": j, "들어오는인용(피인용)": inc.get(j, 0),
         "나가는인용": out.get(j, 0), "합계": inc.get(j, 0) + out.get(j, 0)} for j in allj]
rows.sort(key=lambda r: -r["합계"])
with open(f"{OUT}/neighbors.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["journal", "들어오는인용(피인용)", "나가는인용", "합계"])
    w.writeheader(); w.writerows(rows)

top = rows[:TOPN][::-1]          # 위가 1위가 되도록 역순
labels = [r["journal"] for r in top]
inc_v = [r["들어오는인용(피인용)"] for r in top]
out_v = [r["나가는인용"] for r in top]
y = range(len(top))

fig, ax = plt.subplots(figsize=(12, 10))
ax.barh(y, inc_v, color="#c0392b", label="들어오는 인용 (이 저널을 인용 = 피인용)")
ax.barh(y, out_v, left=inc_v, color="#2471a3", label="나가는 인용 (이 저널이 인용)")
for i, r in enumerate(top):
    tot = r["합계"]
    ax.text(tot + max(inc_v + out_v) * 0.01, i,
            f"{tot}  (피{r['들어오는인용(피인용)']}/인{r['나가는인용']})",
            va="center", ha="left", fontsize=8)
ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=10)
ax.set_xlim(0, max(r["합계"] for r in top) * 1.25)
ax.set_xlabel("인용 연결강도 (건수)")
ax.set_title(f"{CENTER} 인용 지평도 — 가장 많이 연결된 학술지 Top {TOPN} (2008~2024)\n"
             "빨강=피인용(들어옴) · 파랑=인용(나감) · 전분야 포함", fontsize=13)
ax.legend(loc="lower right", fontsize=10)
plt.tight_layout()
png = f"{OUT}/landscape.png"
plt.savefig(png, dpi=130, bbox_inches="tight")
print(f"{CENTER}: 저장 {png}")
print(f"  Top10:")
for r in rows[:10]:
    print(f"    {r['합계']:4d} (피{r['들어오는인용(피인용)']}/인{r['나가는인용']})  {r['journal'][:26]}")
