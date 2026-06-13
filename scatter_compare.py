# -*- coding: utf-8 -*-
"""어문연구(語文硏究) vs 상허학보 — 인용 이웃 산점도 비교.

journal_comparison_full.csv (전분야 포함 연결강도) 를 읽어
  x = 어문연구와의 연결강도, y = 상허학보와의 연결강도, 점 = 이웃 학술지.
대각선(공유) / 축 근처(한쪽 전속) / 색(어느 쪽으로 기우는지)으로 차이를 한눈에.
출력: Data/한국어와문학_결과2/scatter_어문연구_vs_상허학보.png
"""
import sys, io, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

fp = "C:/Windows/Fonts/malgun.ttf"
font_manager.fontManager.addfont(fp)
matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = "Data/한국어와문학_결과2"
CSV = f"{BASE}/journal_comparison_full.csv"
rows = []
for r in csv.DictReader(open(CSV, encoding="utf-8-sig")):
    a, b = int(r["어문연구"]), int(r["상허학보"])
    if a + b >= 12:                      # 잡음 제거(합계 12 미만 제외)
        rows.append((r["journal"], a, b))
print(f"표시 학술지: {len(rows)}종 (합계 12건 이상)")

fig, ax = plt.subplots(figsize=(15, 15))
# 점: x=어문+0.5, y=상허+0.5 (로그축용), 색=기울기, 크기=합계
for name, a, b in rows:
    x, y = a + 0.5, b + 0.5
    if a >= b * 1.5:
        col = "#2471a3"           # 어문연구 우세
    elif b >= a * 1.5:
        col = "#c0392b"           # 상허학보 우세
    else:
        col = "#7f8c8d"           # 공유(균형)
    ax.scatter(x, y, s=18 + 4*(a+b)**0.7, c=col, alpha=0.55,
               edgecolors="white", linewidths=0.5, zorder=3)

# 라벨: 합계 상위 24 + 양극단(한쪽 강·다른쪽 약) 일부만 → 겹침 최소화
by_total = sorted(rows, key=lambda r: -(r[1] + r[2]))[:24]
extreme = [r for r in rows if (r[1] >= 60 and r[2] <= 6) or (r[2] >= 60 and r[1] <= 6)]
labeled = {r[0]: r for r in by_total + extreme}.values()
for name, a, b in labeled:
    col = "#1b4f72" if a >= b * 1.5 else ("#922b21" if b >= a * 1.5 else "#444")
    ax.annotate(name, (a + 0.5, b + 0.5), fontsize=9.5, color=col,
                xytext=(4, 3), textcoords="offset points", zorder=6,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.7))

# 대각선(공유 기준선) y=x
import numpy as np
lim = max(max(a for _, a, _ in rows), max(b for _, _, b in rows)) + 5
ax.plot([0.5, lim], [0.5, lim], ls="--", c="#888", lw=1, zorder=1)
ax.text(lim*0.62, lim*0.78, "공유 영역\n(양쪽 비슷)", color="#555", fontsize=11,
        rotation=38, ha="center", va="center")
ax.text(lim*0.6, 1.1, "← 어문연구 전속 (언어학)", color="#2471a3", fontsize=12, ha="center")
ax.text(1.3, lim*0.6, "상허학보 전속\n(문학·역사)", color="#c0392b", fontsize=12,
        ha="left", va="center", rotation=90)

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(0.45, lim); ax.set_ylim(0.45, lim)
ax.set_xlabel("어문연구(語文硏究)와의 인용 연결강도  (로그 척도)", fontsize=12)
ax.set_ylabel("상허학보와의 인용 연결강도  (로그 척도)", fontsize=12)
ax.set_title("어문연구(語文硏究) vs 상허학보 — 인용 이웃 산점도 (2008~2024, 전분야)\n"
             "점=학술지 · 파랑=어문연구쪽 · 빨강=상허학보쪽 · 회색=공유 · 점선=균형선(y=x)",
             fontsize=13)
ax.grid(True, which="both", ls=":", alpha=0.3)
plt.tight_layout()
png = f"{BASE}/scatter_어문연구_vs_상허학보.png"
plt.savefig(png, dpi=130, bbox_inches="tight")
print("저장:", png)
