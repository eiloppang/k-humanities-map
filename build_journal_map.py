# -*- coding: utf-8 -*-
"""어문연구(語文硏究, 000452) 저널 단위 인용 지평도.

어문연구를 중심으로, 인용 관계가 있는 다른 학술지들을 인용수 가중치로 시각화한다.
  - 들어오는 인용: 타 학술지 → 어문연구  (cited_by 의 journal 필드, 구조화되어 정확)
  - 나가는 인용:   어문연구 → 타 학술지  (references 의 art_id 를 전체 데이터에서 학술지로
                   해석; 한국어와문학 115개 저널에 한해 해석 가능)
출력: Data/한국어와문학_결과2/network_어문연구/journal_map.png (+ journal_edges.csv)
"""
import os, sys, io, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import Counter
import math
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 한글/한자 폰트 (맑은 고딕)
fp = "C:/Windows/Fonts/malgun.ttf"
font_manager.fontManager.addfont(fp)
matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

PKL = "Data/한국어와문학_결과2/korlit_2008_2024.pkl"
SERE_ID = sys.argv[1] if len(sys.argv) > 1 else "000452"   # 기본: 어문연구(語文硏究)
TOPN = int(sys.argv[2]) if len(sys.argv) > 2 else 18       # 표시할 상위 이웃 학술지 수

df = pd.read_pickle(PKL)
aid2j = dict(zip(df["article_id"], df["journal_ko"]))   # art_id -> 학술지명(전체 데이터)
jour = df[df["sere_id"] == SERE_ID]
CENTER = jour["journal_ko"].mode().iloc[0] if len(jour) else SERE_ID   # 대표 저널명
safe = "".join(c for c in CENTER if c.isalnum() or c in "()_-")
OUT = f"Data/한국어와문학_결과2/network_{safe}"
os.makedirs(OUT, exist_ok=True)
print(f"{CENTER} (sereId {SERE_ID}) 논문 수: {len(jour)}")

incoming = Counter()           # 타저널 -> 어문연구 (피인용)
outgoing = Counter()           # 어문연구 -> 타저널 (인용)
for _, r in jour.iterrows():
    for cb in (r["cited_by"] or []):
        j = cb.get("journal")
        if j and j != CENTER:
            incoming[j] += 1
    for ref in (r["references"] or []):
        rid = ref.get("art_id")
        if rid and rid in aid2j:
            j = aid2j[rid]
            if j and j != CENTER:
                outgoing[j] += 1

# 이웃 학술지 = 들어오는+나가는 가중치 합 상위 TOPN
total = Counter()
for j, c in incoming.items():
    total[j] += c
for j, c in outgoing.items():
    total[j] += c
neighbors = [j for j, _ in total.most_common(TOPN)]

# 엣지 CSV 저장(전체)
with open(f"{OUT}/journal_edges.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["source", "target", "weight", "direction"])
    for j, c in incoming.most_common():
        w.writerow([j, CENTER, c, "in(타저널→어문연구)"])
    for j, c in outgoing.most_common():
        w.writerow([CENTER, j, c, "out(어문연구→타저널)"])

# ---- 시각화: 중심(어문연구) + 이웃 원형 배치 ----
fig, ax = plt.subplots(figsize=(15, 15))
n = len(neighbors)
pos = {CENTER: (0, 0)}
for i, j in enumerate(neighbors):
    ang = 2 * math.pi * i / n
    pos[j] = (math.cos(ang), math.sin(ang))

maxw = max([total[j] for j in neighbors] + [1])
# 엣지
for j in neighbors:
    x0, y0 = pos[CENTER]; x1, y1 = pos[j]
    inw, outw = incoming.get(j, 0), outgoing.get(j, 0)
    if inw:
        ax.annotate("", xy=(x0*0.12, y0*0.12) if False else (0, 0), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#c0392b",
                                    lw=0.5 + 4*inw/maxw, alpha=0.55,
                                    shrinkA=18, shrinkB=26))
    if outw:
        ax.annotate("", xy=(x1, y1), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#2471a3",
                                    lw=0.5 + 4*outw/maxw, alpha=0.55,
                                    shrinkA=26, shrinkB=18))
# 노드
for j in neighbors:
    x, y = pos[j]
    s = total[j]
    ax.scatter([x], [y], s=300 + 1400*s/maxw, c="#aed6f1", edgecolors="#2471a3",
               zorder=3, linewidths=1.2)
    lab = f"{j}\n(피인용 {incoming.get(j,0)} · 인용 {outgoing.get(j,0)})"
    ax.text(x*1.13, y*1.13, lab, ha="center", va="center", fontsize=9, zorder=5)
# 중심
ax.scatter([0], [0], s=3000, c="#f9e79f", edgecolors="#b7950b", zorder=4, linewidths=2)
ax.text(0, 0, CENTER.replace("(", "\n("), ha="center", va="center", fontsize=12,
        fontweight="bold", zorder=6)

ax.set_xlim(-1.45, 1.45); ax.set_ylim(-1.45, 1.45); ax.axis("off")
ax.set_title(f"{CENTER} 인용 지평도 — 학술지 단위 (2008~2024)\n"
             f"빨강 화살표: 타 저널→{CENTER}(피인용)  ·  파랑 화살표: {CENTER}→타 저널(인용)  ·  "
             "원 크기·선 굵기 = 인용 건수",
             fontsize=13)
plt.tight_layout()
png = f"{OUT}/journal_map.png"
plt.savefig(png, dpi=130, bbox_inches="tight")
print("저장:", png)

print(f"\n[들어오는 인용] {CENTER}를 인용한 학술지 Top 10")
for j, c in incoming.most_common(10):
    print(f"  {c:4d}  {j[:30]}")
print(f"\n[나가는 인용] {CENTER}가 인용한 학술지 Top 10 (한국어와문학 내 해석분)")
for j, c in outgoing.most_common(10):
    print(f"  {c:4d}  {j[:30]}")
