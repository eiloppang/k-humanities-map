# -*- coding: utf-8 -*-
"""KCI 파이프라인 오케스트레이터 (분과 일반화 진입점).

  ┌─────────────────────────────────────────────────────────────┐
  │  다른 분과 적용 = config.py 의 ACTIVE 만 교체.                 │
  │  아래 단계 중 [분과-특정]은 config 입력이 필요하고,           │
  │  [분과-무관]은 korlit pkl 경로만 있으면 그대로 재사용된다.    │
  └─────────────────────────────────────────────────────────────┘

사용:
  python Scraping-Code/run_kci_pipeline.py            # 실행 계획만 출력(안전)
  python Scraping-Code/run_kci_pipeline.py --run      # 실제 실행
  python Scraping-Code/run_kci_pipeline.py --only 정제 # 정제 단계만
"""
import os, sys, argparse, subprocess
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

CODE = os.path.dirname(os.path.abspath(__file__))   # Scraping-Code
sys.path.insert(0, CODE)
import config
D = config.ACTIVE

# (라벨, 스크립트, 종류, 설명)  종류: S=분과-특정, G=분과-무관
STAGES = [
    ("학술지목록",   "kci/fetch_journals.py",           "S",
     f"KCI 분류검색에서 {D.name}({D.code}) 학술지 목록 자동 추출 → {D.journals_csv}"),
    ("수집",         "kci/scrape_korlit.py",            "S",
     f"분야코드 {D.code}·{D.target_field}·학술지목록으로 논문+인용 수집 → {D.pkl}"),
    ("학술지별 논문수", "kci/journal_counts.py",          "G",
     f"수집 원본 → 학술지별 논문 수 요약 journal_article_counts.csv"),
    ("정제 Phase2",  "refine/phase2_internal.py",       "G",
     "cited_by 내부 art_id 즉시 복구 + 외부 워크리스트 (분과 무관)"),
    ("정제 Phase3",  "refine/phase3_fetch_external.py", "G",
     "외부 art_id KCI 재조회 (분과 무관)"),
    ("정제 Phase4",  "refine/phase4_merge.py",          "G",
     f"저널→분과 매핑({config.JOURNAL_FIELD_XLS}) → {D.clean_pkl} (분과 무관)"),
]


def banner():
    print("=" * 66)
    print(f"  KCI 파이프라인  |  분과: {D.name} ({D.code})")
    print(f"  기간 {D.start_year}–{D.end_year}  |  산출 폴더 {D.out_dir}")
    print("=" * 66)
    print("  단계별 분과 의존성:")
    for lab, scr, kind, desc in STAGES:
        tag = "🔧 분과-특정" if kind == "S" else "♻  분과-무관"
        print(f"   [{tag}] {lab:12s} {scr}")
        print(f"                    └ {desc}")
    print("-" * 66)
    print("  ⇒ 새 분과 적용: config.py 의 ACTIVE 교체 + 해당 분과 학술지목록 준비.")
    print("     '수집'만 분과 입력이 필요하고, '정제' 3단계는 그대로 재사용된다.")
    print("=" * 66)


def run(only=None):
    for lab, scr, kind, desc in STAGES:
        if only and only not in lab:
            continue
        print(f"\n▶ {lab}  ({scr})")
        rc = subprocess.call([sys.executable, scr], cwd=CODE)
        if rc != 0:
            print(f"✗ '{lab}' 실패(exit {rc}). 중단."); return
    print("\n✔ KCI 파이프라인 완료.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="실제 실행(미지정 시 계획만)")
    ap.add_argument("--only", help="특정 단계만 (예: 정제)")
    args = ap.parse_args()
    banner()
    if args.run:
        run(only=args.only)
    else:
        print("\n(계획만 출력했습니다. 실제 실행하려면 --run)")
