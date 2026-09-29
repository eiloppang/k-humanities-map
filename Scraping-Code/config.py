# -*- coding: utf-8 -*-
"""분과별 설정 — 다른 분과(사·철·예 등) 적용 시 '여기만' 교체한다.

파이프라인 로직은 분과에 독립적이고, 분과마다 달라지는 값·경로는 모두
이 파일의 Discipline 하나로 모았다. 새 분과는 Discipline 인스턴스를 하나
채우고 맨 아래 ACTIVE 를 바꾸기만 하면 KCI·KRI 파이프라인 전체가
그 분과 경로로 자동 전환된다.

무엇이 분과마다 다른가?
  · KCI '수집' 단계        → 분야명·연구분야문자열·학술지목록·기간·경로
  · KCI 'cited_by 정제'    → 분과 무관 (art_id 기반). 경로만 분과별로.
  · KRI 수집 전 과정        → 분과 무관 (korlit pkl 만 있으면 동작). 경로만 분과별로.
"""
import os
import sys
from dataclasses import dataclass

# 코드는 Scraping-Code/, 데이터는 저장소 루트의 KCI-Data/ · KRI-Data/ 에 둔다.
# 모든 경로를 저장소 루트 기준 절대경로로 만들어, 어느 폴더에서 실행해도 동작하게 한다.
CODE_DIR = os.path.dirname(os.path.abspath(__file__))   # .../Scraping-Code
ROOT = os.path.dirname(CODE_DIR)                         # 저장소 루트
KCI_DATA = os.path.join(ROOT, "KCI-Data")
KRI_DATA = os.path.join(ROOT, "KRI-Data")


def P(rel):
    """저장소 루트 기준 상대경로 → 절대경로."""
    return os.path.join(ROOT, rel)


# 공용(분과 무관) 리소스
JOURNAL_FIELD_XLS = P("학술지종수.xls")                          # 저널→분과 매핑표(KCI 전체)
KCI_RESEARCH_FIELDS = os.path.join(KCI_DATA, "kci_research_fields.csv")  # KCI 전체 연구분야 목록
KRI_PROFILE = os.path.join(KRI_DATA, "_chrome_profile")          # KRI 로그인 세션(공용)


def add_root_to_path():
    """스테이지 스크립트가 하위 폴더에서 실행돼도 `import config` 가 되게
    Scraping-Code 폴더를 sys.path 에 넣는다."""
    if CODE_DIR not in sys.path:
        sys.path.insert(0, CODE_DIR)


@dataclass
class Discipline:
    code: str            # KCI 분야코드 (예: A11)
    name: str            # 분과명 (예: 한국어와문학)
    target_field: str    # KCI 연구분야 문자열 (예: "인문학 > 한국어와문학")
    journals_csv: str    # 입력: 해당 분과 전체 학술지 목록 (KCI-Data 기준 상대경로)
    out_dir: str         # KCI 산출 폴더 (KCI-Data 기준 상대경로)
    start_year: int = 2008
    end_year: int = 2024

    def __post_init__(self):
        # KCI-Data 기준 상대경로 → 절대경로
        self.out_dir = os.path.join(KCI_DATA, self.out_dir)
        self.journals_csv = os.path.join(KCI_DATA, self.journals_csv)

    # --- KCI 수집 산출 ---
    @property
    def _stem(self):       return f"korlit_{self.start_year}_{self.end_year}"
    @property
    def pkl(self):         return f"{self.out_dir}/{self._stem}.pkl"
    @property
    def csv(self):         return f"{self.out_dir}/{self._stem}.csv"
    @property
    def ckpt(self):        return f"{self.out_dir}/_checkpoint.jsonl"
    @property
    def journals_out(self):return f"{self.out_dir}/_journals.csv"

    # --- cited_by 정제 중간·산출 ---
    @property
    def ext_worklist(self):     return f"{self.out_dir}/_external_artids.txt"
    @property
    def internal_resolved(self):return f"{self.out_dir}/_internal_resolved.json"
    @property
    def ext_cache(self):        return f"{self.out_dir}/_external_cache.jsonl"
    @property
    def clean_pkl(self):        return f"{self.out_dir}/{self._stem}_clean.pkl"
    @property
    def clean_csv(self):        return f"{self.out_dir}/{self._stem}_clean.csv"

    # --- KRI (분과별 폴더 KRI-Data/<code>) ---
    @property
    def kri_dir(self):          return os.path.join(KRI_DATA, self.code)
    @property
    def paper_crets(self):      return f"{self.kri_dir}/_paper_crets.jsonl"
    @property
    def krinum_cache(self):     return f"{self.kri_dir}/_krinum_cache.jsonl"
    @property
    def kri_mapping(self):      return f"{self.kri_dir}/kri_mapping.csv"
    @property
    def unique_kri(self):       return f"{self.kri_dir}/unique_kri.txt"
    @property
    def kri_cache(self):        return f"{self.kri_dir}/_kri_cache.jsonl"
    @property
    def researchers(self):      return f"{self.kri_dir}/researchers.csv"
    @property
    def author_paper_kri(self): return f"{self.kri_dir}/author_paper_kri.csv"


# ============================================================
# 분과 정의 — 새 분과는 아래에 하나 추가하고 ACTIVE 만 바꾼다
# ============================================================

A11 = Discipline(
    code="A11",
    name="한국어와문학",
    target_field="인문학 > 한국어와문학",
    journals_csv="한국어와문학_결과2/journals_a11.csv",
    out_dir="한국어와문학_결과2",
)

HISTORY = Discipline(          # 역사학 (KCI 분야코드 A02)
    code="A02", name="역사학", target_field="인문학 > 역사학",
    journals_csv="역사학_결과/journals.csv", out_dir="역사학_결과")

PHILOSOPHY = Discipline(       # 철학 (KCI 분야코드 A03)
    code="A03", name="철학", target_field="인문학 > 철학",
    journals_csv="철학_결과/journals.csv", out_dir="철학_결과")

ETC_HUM = Discipline(          # 기타인문학 (KCI 분야코드 A99)
    code="A99", name="기타인문학", target_field="인문학 > 기타인문학",
    journals_csv="기타인문학_결과/journals.csv", out_dir="기타인문학_결과")

# --- 확장 예시 (분야코드 확인 후 채우면 즉시 적용) ---
ART = Discipline(              # 예술
    code="G01", name="예술체육학", target_field="예술체육학 > 예술일반",
    journals_csv="예술_결과/journals.csv", out_dir="예술_결과")


# ↓↓↓ 실행할 분과를 여기서 고른다 (이 한 줄이 분과 스위치) ↓↓↓
ACTIVE = HISTORY
