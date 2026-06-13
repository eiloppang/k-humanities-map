# -*- coding: utf-8 -*-
"""한 학술지의 인용 통계(이웃학술지.csv)를 그래프로.
사용: python build_disc_graphs.py [학술지명]   (기본 상허학보)
  ① 대분류별.png   - 대분류(분과)로만 나눈 피인용 vs 참고문헌
  ② 전체개요.png   - 상위 이웃 학술지(피인용+참고문헌), 막대=학술지, 라벨색=분과
출력: Data/한국어와문학_결과2/통계/<학술지>_인용통계/
"""
import sys, io, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

fp = "C:/Windows/Fonts/malgun.ttf"
font_manager.fontManager.addfont(fp)
matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

CENTER = sys.argv[1] if len(sys.argv) > 1 else "상허학보"
DIR = f"Data/한국어와문학_결과2/통계/{CENTER}_인용통계"
rows = list(csv.DictReader(open(f"{DIR}/이웃학술지.csv", encoding="utf-8-sig")))
IK = "피인용(받은_인용)"
OK_ = "참고문헌(한_인용)"
for r in rows:
    r[IK] = int(r[IK]); r[OK_] = int(r[OK_]); r["합계"] = int(r["합계"])

CMAP = {"인문학": "#2471a3", "사회과학": "#c0392b", "복합학": "#27ae60",
        "예술체육학": "#8e44ad", "기타": "#7f8c8d", "공학": "#e67e22",
        "자연과학": "#16a085", "의약학": "#d35400", "농수해양학": "#95a5a6"}
dcol = lambda d: CMAP.get(d, "#34495e")

# ── ① 대분류별 ──────────────────────────────────────────────
agg = defaultdict(lambda: [0, 0])      # 대분류 -> [피인용, 참고문헌]
for r in rows:
    agg[r["대분류"]][0] += r[IK]; agg[r["대분류"]][1] += r[OK_]
items = sorted(agg.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
labels = [k for k, _ in items]
inc = [v[0] for _, v in items]; out = [v[1] for _, v in items]
y = range(len(items)); h = 0.38
fig, ax = plt.subplots(figsize=(11, max(4, len(items) * 0.8)))
ax.barh([i + h/2 for i in y], inc, height=h, color="#c0392b", label="피인용 (이 분과가 인용)")
ax.barh([i - h/2 for i in y], out, height=h, color="#2471a3", label="참고문헌 (이 분과를 인용)")
mx = max(inc + out) or 1
for i, (a, b) in enumerate(zip(inc, out)):
    ax.text(a + mx*0.01, i + h/2, f"{a:,}", va="center", fontsize=9)
    ax.text(b + mx*0.01, i - h/2, f"{b:,}", va="center", fontsize=9)
ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=11)
ax.invert_yaxis(); ax.set_xlim(0, mx * 1.12)
ax.set_xlabel("인용 건수")
ax.set_title(f"{CENTER} — 대분류(분과)별 피인용 vs 참고문헌 인용 (2008~2024, KCI 학술지)", fontsize=13)
ax.legend(loc="lower right", fontsize=10)
plt.tight_layout(); plt.savefig(f"{DIR}/대분류별.png", dpi=130, bbox_inches="tight"); plt.close()
print(f"저장: {DIR}/대분류별.png")

# ── ② 전체개요: 상위 학술지 + 분과색 ─────────────────────────
TOP = 28
top = sorted(rows, key=lambda r: -r["합계"])[:TOP][::-1]
names = [r["학술지"] for r in top]
y2 = range(len(top))
fig, ax = plt.subplots(figsize=(12, 11))
ax.barh(y2, [r[IK] for r in top], color="#c0392b", label="피인용 (받은 인용)")
ax.barh(y2, [r[OK_] for r in top], left=[r[IK] for r in top], color="#2471a3",
        label="참고문헌 (한 인용)")
for i, r in enumerate(top):
    ax.text(r["합계"] + max(x["합계"] for x in top)*0.01, i,
            f"{r['합계']}", va="center", fontsize=8)
ax.set_yticks(list(y2)); ax.set_yticklabels(names, fontsize=10)
# y축 라벨 색 = 대분류
for tick, r in zip(ax.get_yticklabels(), top):
    tick.set_color(dcol(r["대분류"]))
ax.set_xlabel("인용 연결강도 (피인용 + 참고문헌)")
ax.set_title(f"{CENTER} 인용 지평 — 상위 학술지 Top{TOP} (라벨색=대분류)\n"
             "빨강=피인용 · 파랑=참고문헌", fontsize=13)
used = [d for d in CMAP if any(r["대분류"] == d for r in top)]
leg1 = ax.legend(loc="lower right", fontsize=10)
ax.add_artist(leg1)
ax.legend(handles=[Patch(color=CMAP[d], label=d) for d in used],
          loc="center right", fontsize=9, title="대분류(라벨색)")
plt.tight_layout(); plt.savefig(f"{DIR}/전체개요.png", dpi=130, bbox_inches="tight"); plt.close()
print(f"저장: {DIR}/전체개요.png")
