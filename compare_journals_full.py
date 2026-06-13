# -*- coding: utf-8 -*-
"""어문연구 vs 상허학보 — 완전판 비교 (나가는 인용도 밖 분야 포함).

나가는 인용(references)을 art_id 해석(한국어와문학 한정) 대신 **서지 원문(text)에서
출처 학술지명을 파싱**해 모든 분야를 포함한다.
  reference type '학술지(연속간행물)' 의 text 형식:
    [학술지(연속간행물)] - 저자 / 연도 / 제목 / 학술지명 권 : 페이지
  → 마지막 '/' 칸에서 ' 권 : 페이지' 를 떼면 학술지명.
연결강도 = 들어오는 인용(cited_by.journal, 전분야) + 나가는 인용(reference text, 전분야).
출력(Data/한국어와문학_결과2/):
  journal_comparison_full.csv, comparison_full_어문연구_vs_상허학보.png
"""
import sys, io, csv, re
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
BASE = "Data/한국어와문학_결과2"
TARGETS = [("어문연구(語文硏究)", "000452"), ("상허학보", "000769")]
_cut = re.compile(r"\s*[\d０-９(（].*$")        # 첫 숫자 또는 여는 괄호 이후 전부 제거


def ref_journal(text):
    """학술지 reference text 에서 출처 학술지명 추출.
    형식: '... / 학술지명 (영문명) 권 : 페이지' → '학술지명'.
    숫자(권/호)나 여는 괄호(영문병기) 이후를 잘라 변형을 합친다."""
    seg = text.split(" / ")[-1]               # 마지막 칸
    seg = seg.split(" : ")[0]                  # 페이지 제거
    seg = _cut.sub("", seg).strip()            # 권호/영문병기 제거
    return seg


def neighbors(df, sere_id, center):
    jour = df[df["sere_id"] == sere_id]
    inc, out = Counter(), Counter()
    for _, r in jour.iterrows():
        for cb in (r["cited_by"] or []):                  # 들어오는(전분야)
            j = cb.get("journal")
            if j and j != center:
                inc[j] += 1
        for ref in (r["references"] or []):               # 나가는(전분야, text 파싱)
            if "학술지" not in (ref.get("type") or ""):
                continue
            j = ref_journal(ref.get("text", ""))
            if j and j != center and len(j) >= 2:
                out[j] += 1
    return inc, out, len(jour)


df = pd.read_pickle(PKL)
data = {}
for center, sid in TARGETS:
    inc, out, n = neighbors(df, sid, center)
    data[center] = {"inc": inc, "out": out, "n": n}
    print(f"{center}: 논문 {n} | 들어오는 이웃 {len(inc)} / 나가는 이웃 {len(out)}")
    print(f"  [나가는 인용 Top10 — 전분야]")
    for j, c in out.most_common(10):
        print(f"     {c:4d}  {j[:30]}")
    print()

A, B = TARGETS[0][0], TARGETS[1][0]
wa = data[A]["inc"] + data[A]["out"]      # Counter 합 = 연결강도
wb = data[B]["inc"] + data[B]["out"]
allj = set(wa) | set(wb)
rows = [{"journal": j, "어문연구": wa.get(j, 0), "상허학보": wb.get(j, 0),
         "어문_나가는": data[A]["out"].get(j, 0), "어문_들어오는": data[A]["inc"].get(j, 0),
         "상허_나가는": data[B]["out"].get(j, 0), "상허_들어오는": data[B]["inc"].get(j, 0),
         "합계": wa.get(j, 0) + wb.get(j, 0)} for j in allj]
rows.sort(key=lambda r: -r["합계"])
with open(f"{BASE}/journal_comparison_full.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["journal", "어문연구", "상허학보", "어문_나가는",
                                      "어문_들어오는", "상허_나가는", "상허_들어오는", "합계"])
    w.writeheader(); w.writerows(rows)
print(f"비교표 저장: {BASE}/journal_comparison_full.csv (이웃 {len(rows)}종)")

# ---- 좌우 대칭 막대 (상위 26) ----
TOP = 26
top = sorted(rows, key=lambda r: -r["합계"])[:TOP]
top.sort(key=lambda r: (r["어문연구"] - r["상허학보"]))
labels = [r["journal"] for r in top]
y = range(len(top))
fig, ax = plt.subplots(figsize=(13, 12))
ax.barh(y, [-r["어문연구"] for r in top], color="#2471a3", height=0.72,
        label="어문연구(語文硏究) 연결강도")
ax.barh(y, [r["상허학보"] for r in top], color="#c0392b", height=0.72,
        label="상허학보 연결강도")
ax.axvline(0, color="#555", lw=0.8)
for i, r in enumerate(top):
    if r["어문연구"]:
        ax.text(-r["어문연구"] - 6, i, str(r["어문연구"]), va="center", ha="right", fontsize=8)
    if r["상허학보"]:
        ax.text(r["상허학보"] + 6, i, str(r["상허학보"]), va="center", ha="left", fontsize=8)
ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=10)
mx = max(max(r["어문연구"] for r in top), max(r["상허학보"] for r in top)) * 1.18
ax.set_xlim(-mx, mx)
ax.set_xticks(ax.get_xticks())
ax.set_xticklabels([str(abs(int(t))) for t in ax.get_xticks()])
ax.set_xlabel("인용 연결강도 (들어오는+나가는, 전분야 포함)")
ax.set_title("어문연구(語文硏究) vs 상허학보 — 인용 이웃 비교 [완전판: 나가는 인용 전분야 포함]\n"
             "← 파랑: 어문연구와의 연결   |   빨강: 상허학보와의 연결 →", fontsize=13)
ax.legend(loc="lower right", fontsize=11)
plt.tight_layout()
png = f"{BASE}/comparison_full_어문연구_vs_상허학보.png"
plt.savefig(png, dpi=130, bbox_inches="tight")
print("그래프 저장:", png)
