# -*- coding: utf-8 -*-
"""두 저널(어문연구 vs 상허학보)의 인용 이웃을 비교 — 차이를 한눈에.

각 저널의 network_*/journal_edges.csv 를 읽어, 이웃 학술지별 연결강도(들어오는+나가는 인용
건수 합)를 두 저널에 대해 나란히 놓는다.
출력(Data/한국어와문학_결과2/):
  journal_comparison.csv      - 이웃 학술지별 두 저널 연결강도 비교표
  comparison_어문연구_vs_상허학보.png - 좌우 대칭 막대그래프
"""
import sys, io, csv, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

fp = "C:/Windows/Fonts/malgun.ttf"
font_manager.fontManager.addfont(fp)
matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = "Data/한국어와문학_결과2"
A = ("어문연구(語文硏究)", f"{BASE}/network_어문연구/journal_edges.csv")
B = ("상허학보", f"{BASE}/network_상허학보/journal_edges.csv")


def load(center, path):
    """이웃 학술지 -> 연결강도(in+out 합) dict."""
    w = defaultdict(int)
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            other = r["source"] if r["source"] != center else r["target"]
            if other == center:
                continue
            w[other] += int(r["weight"])
    return w


wa, wb = load(*A), load(*B)
allj = set(wa) | set(wb)
rows = [{"journal": j, "어문연구": wa.get(j, 0), "상허학보": wb.get(j, 0),
         "합계": wa.get(j, 0) + wb.get(j, 0),
         "치우침": ("어문연구" if wa.get(j, 0) > wb.get(j, 0) else
                    ("상허학보" if wb.get(j, 0) > wa.get(j, 0) else "양쪽"))}
        for j in allj]
rows.sort(key=lambda r: -r["합계"])

# 비교 CSV
with open(f"{BASE}/journal_comparison.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["journal", "어문연구", "상허학보", "합계", "치우침"])
    w.writeheader(); w.writerows(rows)
print(f"비교표 저장: {BASE}/journal_comparison.csv  (이웃 학술지 {len(rows)}종)")

# ---- 좌우 대칭(back-to-back) 막대그래프 ----
# 상위 N 을 '치우침 점수'(어문연구-상허학보)로 정렬 → 위=어문연구쪽, 아래=상허학보쪽
TOP = 24
top = sorted(rows, key=lambda r: -r["합계"])[:TOP]
top.sort(key=lambda r: (r["어문연구"] - r["상허학보"]))   # 아래로 갈수록 어문연구 우세
labels = [r["journal"] for r in top]
va = [r["어문연구"] for r in top]
vb = [r["상허학보"] for r in top]
y = range(len(top))

fig, ax = plt.subplots(figsize=(13, 11))
ax.barh(y, [-v for v in va], color="#2471a3", label="어문연구(語文硏究) 연결강도", height=0.7)
ax.barh(y, vb, color="#c0392b", label="상허학보 연결강도", height=0.7)
ax.axvline(0, color="#555", lw=0.8)
for i, r in enumerate(top):
    if r["어문연구"]:
        ax.text(-r["어문연구"] - 4, i, str(r["어문연구"]), va="center", ha="right", fontsize=8)
    if r["상허학보"]:
        ax.text(r["상허학보"] + 4, i, str(r["상허학보"]), va="center", ha="left", fontsize=8)
ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=10)
mx = max(max(va), max(vb)) * 1.18
ax.set_xlim(-mx, mx)
xt = ax.get_xticks()
ax.set_xticks(xt); ax.set_xticklabels([str(abs(int(t))) for t in xt])
ax.set_xlabel("인용 연결강도 (들어오는+나가는 인용 건수)")
ax.set_title("어문연구(語文硏究) vs 상허학보 — 인용 이웃 비교 (2008~2024)\n"
             "← 파랑: 어문연구와의 연결   |   빨강: 상허학보와의 연결 →",
             fontsize=14)
ax.legend(loc="lower right", fontsize=11)
plt.tight_layout()
png = f"{BASE}/comparison_어문연구_vs_상허학보.png"
plt.savefig(png, dpi=130, bbox_inches="tight")
print("그래프 저장:", png)

# ---- 요약: 각 저널 고유 이웃 ----
only_a = sorted([r for r in rows if r["상허학보"] == 0 and r["어문연구"] > 0],
                key=lambda r: -r["어문연구"])[:8]
only_b = sorted([r for r in rows if r["어문연구"] == 0 and r["상허학보"] > 0],
                key=lambda r: -r["상허학보"])[:8]
shared = sorted([r for r in rows if r["어문연구"] > 0 and r["상허학보"] > 0],
                key=lambda r: -r["합계"])[:8]
print("\n[어문연구만 연결] (상허학보와 무관)")
for r in only_a: print(f"  {r['어문연구']:4d}  {r['journal'][:26]}")
print("\n[상허학보만 연결] (어문연구와 무관)")
for r in only_b: print(f"  {r['상허학보']:4d}  {r['journal'][:26]}")
print("\n[양쪽 공통 이웃] (합계 상위)")
for r in shared: print(f"  어문 {r['어문연구']:4d} / 상허 {r['상허학보']:4d}  {r['journal'][:24]}")
