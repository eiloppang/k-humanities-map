# -*- coding: utf-8 -*-
"""KRI 파이프라인 오케스트레이터 (분과 일반화 진입점).

  ┌─────────────────────────────────────────────────────────────┐
  │  이 파이프라인은 '분과 완전 무관'이다.                         │
  │  입력이 어느 분과의 korlit pkl 이든(crt_id 컬럼만 있으면)      │
  │  동일 코드로 kri_num 수확 → KRI 연구자정보 수집이 돌아간다.   │
  │  다른 분과 적용 = config.py 의 ACTIVE 만 교체 (경로 자동 파생). │
  └─────────────────────────────────────────────────────────────┘

경로: 입력 korlit = config.ACTIVE.pkl / 산출 = config.ACTIVE.kri_dir

사용:
  python Scraping-Code/run_kri_pipeline.py            # 실행 계획만 출력(안전)
  python Scraping-Code/run_kri_pipeline.py --run      # 실제 실행
"""
import os, sys, argparse, subprocess
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

CODE = os.path.dirname(os.path.abspath(__file__))   # Scraping-Code
sys.path.insert(0, CODE)
import config
D = config.ACTIVE

# 전 단계 분과-무관(G). 2단계만 KRI 2FA 수동 로그인 필요(분과와 무관한 운영 제약).
STAGES = [
    ("1a 공저자 cret",  "kri/collect_crets.py",        "다저자 논문 article 페이지에서 전 저자 cretId 수집"),
    ("1b kri_num 수확", "kri/harvest_krinum.py",       "poCretDetail onclick 에서 kri_num 추출 (KCI, 2FA 없음)"),
    ("1c 매핑",         "kri/build_mapping.py",        "(논문·저자·cret·kri_num) 매핑 + 고유 연구자 목록"),
    ("2 KRI 수집",      "kri/collect_kri_overnight.py","PG-RP-102 기본정보 7필드 (KRI 2FA 수동 로그인·세션 견고화)"),
    ("3 병합",          "kri/build_final.py",          "researchers.csv · author_paper_kri.csv"),
]


def banner():
    print("=" * 66)
    print(f"  KRI 파이프라인  |  분과: {D.name} ({D.code})   [전 단계 분과-무관]")
    print(f"  입력 korlit: {D.pkl}")
    print(f"  산출 폴더  : {D.kri_dir}")
    print("=" * 66)
    for lab, scr, desc in STAGES:
        manual = "  ⚠ KRI 2FA 수동" if lab.startswith("2 ") else ""
        print(f"   ♻  {lab:14s} {scr}{manual}")
        print(f"                     └ {desc}")
    print("-" * 66)
    print("  ⇒ 분과 교체 시 코드 변경 0. config.ACTIVE 만 바꾸면 입력 pkl·산출 폴더가")
    print("     자동으로 해당 분과로 바뀐다. (crt_id 컬럼 규격만 동일하면 됨)")
    print("=" * 66)


def run():
    for lab, scr, desc in STAGES:
        print(f"\n▶ {lab}  ({scr})")
        if lab.startswith("2 "):
            print("  ※ 뜨는 브라우저에서 직접 로그인+2FA 후 자동 수집/재개됩니다.")
        rc = subprocess.call([sys.executable, scr], cwd=CODE)
        if rc != 0:
            print(f"✗ '{lab}' 실패(exit {rc}). 재실행 시 캐시로 이어집니다."); return
    print("\n✔ KRI 파이프라인 완료.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="실제 실행(미지정 시 계획만)")
    args = ap.parse_args()
    banner()
    if args.run:
        run()
    else:
        print("\n(계획만 출력했습니다. 실제 실행하려면 --run)")
