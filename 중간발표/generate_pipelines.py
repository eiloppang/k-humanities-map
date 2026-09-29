# -*- coding: utf-8 -*-
"""KCI / KRI 수집 파이프라인 다이어그램 PNG 생성."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

# 한글 폰트
for cand in ["Malgun Gothic", "맑은 고딕", "NanumGothic", "AppleGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand; break
plt.rcParams["axes.unicode_minus"] = False

NAVY = "#2c3e50"; BLUE = "#3498db"; TEAL = "#16a085"; ORANGE = "#e67e22"; GRAY = "#7f8c8d"
BLUE_T = "#eaf2fb"; TEAL_T = "#e7f6f2"; ORANGE_T = "#fdeee0"; GRAYFILL = "#eef1f4"

def box(ax, x, y, w, h, text, fc, ec, tc="#1f2d3a", fs=11, weight="normal"):
    ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.10", fc=fc, ec=ec, lw=1.8))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc, weight=weight,
            linespacing=1.4)

def store(ax, x, y, w, h, text, fc, fs=10.5):
    box(ax, x, y, w, h, text, fc, fc, tc="white", fs=fs, weight="bold")

def arrow(ax, x1, y1, x2, y2, color=GRAY, lw=1.8):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=18, lw=lw, color=color, shrinkA=3, shrinkB=3))

def note(ax, x, y, text, color=GRAY, fs=9, ha="left"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fs, color=color, style="italic")

# ---------------------------------------------------------------- KCI
def kci():
    nodes = [
        ("proc", "KCI 로그인 (Selenium 1회)\n→ 세션 쿠키 추출", BLUE_T, BLUE, "① 수집: 로그인 후에만 인용현황 노출"),
        ("proc", "논문 열거\n학술지명 검색 · sereId 정밀 필터", BLUE_T, BLUE, "동명이저널 정확 구분"),
        ("proc", "상세 파싱 (httpx 멀티스레드)\n서지·초록·키워드·references·cited_by", BLUE_T, BLUE, "JSONL 체크포인트 · 자동 재로그인"),
        ("store", "korlit_2008_2024.pkl\n52,068편 · 115지 (2008–2024)", NAVY, None, ""),
        ("proc", "cited_by 오염 진단\nart_id 100% 보유 · 실측 오염률 13.4%", ORANGE_T, ORANGE, "② 정제: journal 칸에 공저자명 混入"),
        ("proc", "Phase 2 · 내부 즉시 복구\n144,275칸 (55.4%)", ORANGE_T, ORANGE, "코퍼스 내 art_id → 진짜 저널명"),
        ("proc", "Phase 3 · 외부 KCI 재조회\n고유 art_id 50,089 (실패 0)", ORANGE_T, ORANGE, "캐시 · 재개 · 레이트리밋"),
        ("proc", "Phase 4 · 분과 매핑\n학술지종수.xls 다중키(한글·영문·ISSN)", ORANGE_T, ORANGE, "원본 journal 보존 + 신설 필드"),
        ("store", "korlit_2008_2024_clean.pkl\ncited_by 260,537항목 · 100% 분과 복원", TEAL, None, ""),
    ]
    n = len(nodes); step = 1.55; H = 0.92; W = 6.6; x = 4.4
    fig, ax = plt.subplots(figsize=(9.6, 2.0 + n*step*0.62))
    top = n*step
    ax.text(x, top + 1.65, "KCI 논문·인용 데이터 파이프라인", ha="center",
            fontsize=16, weight="bold", color=NAVY)
    ax.text(x, top + 1.12, "수집(scrape_korlit) → cited_by 정제(art_id 재도출)", ha="center",
            fontsize=10.5, color=GRAY)
    ys = [top - i*step for i in range(n)]
    for i, (kind, text, fc, ec, side) in enumerate(nodes):
        y = ys[i]
        if kind == "store": store(ax, x, y, W, H, text, fc)
        else: box(ax, x, y, W, H, text, fc, ec)
        if side: note(ax, x + W/2 + 0.25, y, side)
        if i < n-1: arrow(ax, x, y - H/2, x, ys[i+1] + H/2)
    ax.set_xlim(0.3, 11.4); ax.set_ylim(-0.2, top + 2.1); ax.axis("off")
    fig.savefig("중간발표/pipeline_KCI.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("saved 중간발표/pipeline_KCI.png")

# ---------------------------------------------------------------- KRI
def kri():
    nodes = [
        ("store", "korlit  crt_id (보유)\n논문별 저자 인용보고서 ID", NAVY, None, ""),
        ("proc", "1a · 다저자 공저자 cret 수집\narticle 페이지 div.author (5,177건)", TEAL_T, TEAL, "제1저자 외 공저자까지 전원"),
        ("proc", "1b · kri_num 수확  (KCI, 2FA 없음)\npoCretDetail onclick fncArtiSelectCitationIdx", TEAL_T, TEAL, "고유 cret 16,195 → kri 10,092 / no_kri 6,103"),
        ("proc", "1c · 매핑 테이블\n(논문·저자·cret·kri_num) 59,552행", TEAL_T, TEAL, "고유 연구자 8,511명"),
        ("proc", "2 · KRI 수동 2FA 로그인 → 세션 인계\nPG-RP-102 기본정보 (7필드)", ORANGE_T, ORANGE, "세션 견고화: 절전방지·연속활동·재개·드라이버복구"),
        ("store", "researchers.csv · author_paper_kri.csv\n수집 7,883 / 비공개 628 · 조인 49,408행", TEAL, None, ""),
    ]
    n = len(nodes); step = 1.7; H = 1.0; W = 7.0; x = 4.6
    fig, ax = plt.subplots(figsize=(10.2, 2.0 + n*step*0.66))
    top = n*step
    ax.text(x, top + 1.85, "KRI 연구자정보 파이프라인", ha="center",
            fontsize=16, weight="bold", color=NAVY)
    ax.text(x, top + 1.25, "crt_id → kri_num(KCI) → KRI 연구자정보", ha="center",
            fontsize=10.5, color=GRAY)
    ys = [top - i*step for i in range(n)]
    for i, (kind, text, fc, ec, side) in enumerate(nodes):
        y = ys[i]
        if kind == "store": store(ax, x, y, W, H, text, fc)
        else: box(ax, x, y, W, H, text, fc, ec, fs=11)
        if side: note(ax, x + W/2 + 0.25, y, side, fs=8.8)
        if i < n-1: arrow(ax, x, y - H/2, x, ys[i+1] + H/2)
    # 7필드 안내
    note(ax, x, ys[-1] - 0.95,
         "7필드: 성명·성별·소속대학기관·직급·전공분야(세부전공)·출신학교·취득학위",
         color=NAVY, fs=9.5, ha="center")
    ax.set_xlim(0.3, 12.6); ax.set_ylim(-1.4, top + 2.4); ax.axis("off")
    fig.savefig("중간발표/pipeline_KRI.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("saved 중간발표/pipeline_KRI.png")

kci(); kri()
