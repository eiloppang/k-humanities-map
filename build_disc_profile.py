# -*- coding: utf-8 -*-
"""한 학술지의 '연관 분과 프로필' — 인용/피인용 상대 학술지의 분과를 비율로 추산.
사용: python build_disc_profile.py [학술지명]   (기본 상허학보)
출력(Data/한국어와문학_결과2/통계/<학술지>_인용통계/):
  연관분과_대분류.csv, 연관분과_중분류.csv, 연관분과_프로필.png
"""
import sys, io, csv
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

CENTER = sys.argv[1] if len(sys.argv) > 1 else "상허학보"
DIR = f"Data/한국어와문학_결과2/통계/{CENTER}_인용통계"
IK, OK_ = "피인용(받은_인용)", "참고문헌(한_인용)"
rows = list(csv.DictReader(open(f"{DIR}/이웃학술지.csv", encoding="utf-8-sig")))

maj = defaultdict(lambda: [0, 0])             # 대분류 -> [피인용, 참고문헌]
mid = defaultdict(lambda: [0, 0])             # (대분류,중분류) -> [..]
for r in rows:
    i, o = int(r[IK]), int(r[OK_])
    maj[r["대분류"]][0] += i; maj[r["대분류"]][1] += o
    mid[(r["대분류"], r["중분류"])][0] += i; mid[(r["대분류"], r["중분류"])][1] += o

TOT = sum(v[0] + v[1] for v in maj.values()) or 1


def dump(name, items, keyfields):
    items = sorted(items, key=lambda x: -(x[-2]))   # 합계 기준 정렬
    with open(f"{DIR}/{name}", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(keyfields + ["피인용", "참고문헌", "합계", "연관비율(%)"])
        for it in items:
            w.writerow(it)
    return items


maj_rows = [[k, v[0], v[1], v[0]+v[1], round(100*(v[0]+v[1])/TOT, 1)] for k, v in maj.items()]
maj_rows = dump("연관분과_대분류.csv", [[r[0], r[1], r[2], r[3], r[4]] for r in maj_rows], ["대분류"])
mid_rows = [[k[0], k[1], v[0], v[1], v[0]+v[1], round(100*(v[0]+v[1])/TOT, 1)] for k, v in mid.items()]
mid_rows = dump("연관분과_중분류.csv", mid_rows, ["대분류", "중분류"])

print(f"=== {CENTER} 연관 분과 프로필 (총 인용 상호작용 {TOT:,}건 기준) ===")
print("\n[대분류 비율]")
for r in maj_rows:
    print(f"  {r[-1]:>5.1f}%  {r[0]}  (피{r[1]}/참{r[2]})")
print("\n[중분류 비율 Top 15]")
for r in mid_rows[:15]:
    print(f"  {r[-1]:>5.1f}%  {r[1]:14s} [{r[0]}]  (피{r[2]}/참{r[3]})")

# ── 그래프: 중분류 연관비율 Top 15 ──
top = mid_rows[:15][::-1]
labels = [f"{r[1]}" for r in top]
vals = [r[-1] for r in top]
CMAP = {"인문학": "#2471a3", "사회과학": "#c0392b", "복합학": "#27ae60",
        "예술체육학": "#8e44ad", "기타": "#7f8c8d", "공학": "#e67e22"}
cols = [CMAP.get(r[0], "#34495e") for r in top]
fig, ax = plt.subplots(figsize=(11, 8))
ax.barh(range(len(top)), vals, color=cols)
for i, r in enumerate(top):
    ax.text(r[-1] + max(vals)*0.01, i, f"{r[-1]}%", va="center", fontsize=9)
ax.set_yticks(range(len(top))); ax.set_yticklabels(labels, fontsize=10)
for tick, r in zip(ax.get_yticklabels(), top):
    tick.set_color(CMAP.get(r[0], "#34495e"))
ax.set_xlabel("연관 비율 (%) = 해당 중분류와의 인용 상호작용 ÷ 전체")
ax.set_title(f"{CENTER} 연관 분과 프로필 — 중분류 Top15 (피인용+참고문헌, KCI 학술지 기준)\n"
             "막대색=대분류", fontsize=12)
plt.tight_layout(); plt.savefig(f"{DIR}/연관분과_프로필.png", dpi=130, bbox_inches="tight")
print(f"\n저장: {DIR}/ (연관분과_대분류.csv, 연관분과_중분류.csv, 연관분과_프로필.png)")
