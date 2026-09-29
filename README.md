# k-humanities-map

한국 인문학 분과의 학술 지형을 데이터로 그리기 위한 수집·정제 파이프라인.

- **KCI**(한국학술지인용색인)에서 분과별 논문·참고문헌·피인용 데이터를 수집하고, 피인용 데이터의 오염을 자동으로 정제한다.
- **KRI**(한국연구자정보)에서 논문 저자의 소속·직급·전공·학위를 수집해 논문과 연결한다.
- 두 파이프라인 모두 **`config.py`의 한 줄(`ACTIVE`)만 바꾸면 다른 분과에 그대로 적용**된다.

---

## 수집 현황 (2008–2024)

| KCI 분야코드 | 분과 | 학술지 | 논문 (KCI) | 연구자 (KRI) |
|---|---|---|---|---|
| A11 | 한국어와문학 | 115 | 52,068 | 7,883 |
| A02 | 역사학 | 194 | 42,435 | 6,886 |
| A99 | 기타인문학 | 240 | 41,014 | 12,596 |
| A03 | 철학 | 95 | 17,333 | 3,739 |

연구자 수는 KRI에서 정보를 받은 인원이다. 정보 비공개 연구자와 KRI 미등록 저자는 제외된다.

---

## 폴더 구조

```
k-humanities-map/
├─ Scraping-Code/                 수집·정제 코드 전체
│  ├─ config.py                   분과 설정 (ACTIVE 한 줄로 분과 전환)
│  ├─ kci_config.py               KCI 로그인 정보 (git 제외, 직접 생성)
│  ├─ run_kci_pipeline.py         KCI 파이프라인 일괄 실행
│  ├─ run_kri_pipeline.py         KRI 파이프라인 일괄 실행
│  ├─ kci/     fetch_journals.py · scrape_korlit.py · journal_counts.py
│  ├─ refine/  phase2_internal.py · phase3_fetch_external.py · phase4_merge.py
│  └─ kri/     collect_crets.py · harvest_krinum.py · build_mapping.py
│              collect_kri_overnight.py · build_final.py
├─ KCI-Data/<분과>_결과/          KCI 수집·정제 결과
├─ KRI-Data/<분야코드>/           KRI 수집 결과
├─ 학술지종수.xls                 KCI 전체 학술지 → 분과 매핑표 (정제에 필요)
└─ 중간발표/                      발표 자료 · 파이프라인 다이어그램
```

대용량 데이터(수백 MB의 pkl·csv), 캐시, KRI 결과 전체, 로그인 정보는 `.gitignore`로 제외되어 있다. 저장소에는 코드와 작은 요약 파일만 올라간다.

---

## 무엇이 자동화되어 있는가

**사람이 해야 하는 일은 두 가지뿐이다.** `config.py`에서 분과를 고르는 것, 그리고 KRI 연구자정보 수집 단계에서 **2차 인증(2FA) 로그인을 한 번** 하는 것. 나머지는 전부 자동이다.

### KCI 파이프라인 — 전 과정 자동

`python Scraping-Code/run_kci_pipeline.py --run` 한 번으로 아래 단계가 순서대로 실행된다.

| 단계 | 스크립트 | 하는 일 | 사람 개입 |
|---|---|---|---|
| 학술지 목록 | `kci/fetch_journals.py` | KCI 분류검색에서 분과의 전체 학술지 목록 추출 | 없음 |
| 수집 | `kci/scrape_korlit.py` | 논문 서지·초록·키워드·참고문헌·피인용 수집 | 없음 (KCI 로그인 자동) |
| 요약 | `kci/journal_counts.py` | 학술지별 논문 수 요약(`journal_article_counts.csv`) 생성 | 없음 |
| 정제 ② | `refine/phase2_internal.py` | 피인용 항목 중 코퍼스 안의 논문은 즉시 복원, 나머지는 재조회 목록 작성 | 없음 |
| 정제 ③ | `refine/phase3_fetch_external.py` | 코퍼스 밖 논문을 KCI에서 art_id로 재조회해 진짜 저널명 확보 | 없음 |
| 정제 ④ | `refine/phase4_merge.py` | 저널을 `학술지종수.xls`로 분과에 매핑, 정제본 저장 | 없음 |

**정제가 필요한 이유.** KCI 피인용 목록을 긁을 때, 다저자 논문에서 칸이 밀려 **저널명 자리에 공저자 이름이 들어가는 오염**이 생긴다(실측 약 13%). 하지만 모든 피인용 항목에는 정상적인 논문 번호(art_id)가 있다. 그래서 오염된 저널명은 버리고 **art_id로 진짜 저널과 분과를 다시 조회**한다. 원본 `journal` 필드는 보존하고, 정제 결과는 새 필드(`journal_clean`, `field_major`, `field_minor`, `resolve_src`)로 추가한다. 지금까지 모든 분과에서 외부 분과 매칭률 100%를 기록했다.

### KRI 파이프라인 — 2FA 로그인 한 번만 수동

`python Scraping-Code/run_kri_pipeline.py --run` 한 번으로 아래 단계가 순서대로 실행된다.

| 단계 | 스크립트 | 하는 일 | 사람 개입 |
|---|---|---|---|
| 1a | `kri/collect_crets.py` | 다저자 논문에서 공저자까지 전원의 저자 ID(crt_id) 수집 | 없음 |
| 1b | `kri/harvest_krinum.py` | KCI 연구자 페이지에서 국가연구자번호(kri_num) 추출 | 없음 (KCI 로그인 자동) |
| 1c | `kri/build_mapping.py` | 논문·저자·kri_num 연결표와 고유 연구자 목록 생성 | 없음 |
| 2 | `kri/collect_kri_overnight.py` | KRI 기본정보 페이지에서 성명·성별·소속·직급·전공·출신학교·학위 수집 | **뜨는 크롬 창에서 2FA 로그인 1회** |
| 3 | `kri/build_final.py` | 연구자정보와 연결표 병합 → 최종 결과 저장 | 없음 |

국가연구자번호는 KCI 연구자 페이지 안에 이미 들어 있다. 그래서 1단계(1a~1c)는 2FA 없이 KCI 자동 로그인만으로 끝난다. 2FA가 필요한 곳은 KRI 사이트에 접속하는 2단계 하나다.

### 중단돼도 이어서 진행된다

수집이 몇 시간씩 걸리기 때문에 모든 단계가 **끊겨도 처음부터 다시 하지 않도록** 만들어져 있다.

- **체크포인트·재개**: 한 건 받을 때마다 즉시 저장한다. 다시 실행하면 이미 받은 건 건너뛰고 남은 것만 받는다.
- **자동 재로그인**: KCI 세션이 끊기면 스스로 다시 로그인한다.
- **재시도**: 네트워크가 잠깐 끊겨도 요청마다 여러 번 재시도한다. 끝까지 실패한 건만 다음 실행 때 다시 받는다.
- **KRI 장시간 수집 보호**: PC 절전 방지, 페이지 멈춤 시 30초 제한, 브라우저가 죽으면 자동 재시작한다. 세션이 만료되면 멈추지 않고 재로그인을 기다렸다가 이어간다.
- **정상 결측 구분**: KRI에 등록되지 않은 저자(`no_kri`)와 정보 비공개 연구자(`private`)는 오류가 아니라 별도 상태로 기록한다. 그래서 불필요한 재시도가 없다.

---

## 실행 방법

### 1. 준비

```bash
pip install selenium httpx beautifulsoup4 lxml pandas tqdm xlrd
```

`Scraping-Code/kci_config.py`를 만들고 KCI 계정을 적는다. 이 파일은 git에 올라가지 않는다.

```python
KCI_ID = "아이디"
KCI_PW = "비밀번호"
```

크롬 브라우저가 설치되어 있어야 한다.

### 2. 분과 선택

`Scraping-Code/config.py` 맨 아래의 한 줄을 바꾼다.

```python
ACTIVE = HISTORY   # A11 · HISTORY(A02) · PHILOSOPHY(A03) · ETC_HUM(A99)
```

### 3. 실행

```bash
# 실행 계획만 확인 (아무것도 실행하지 않음)
python Scraping-Code/run_kci_pipeline.py

# KCI 수집 → 정제
python Scraping-Code/run_kci_pipeline.py --run

# KRI 연구자정보 (2단계에서 크롬 창이 뜨면 2FA 로그인)
python Scraping-Code/run_kri_pipeline.py --run
```

경로는 모두 저장소 루트 기준으로 고정되어 있어서, 어느 폴더에서 실행해도 된다. 단계를 하나씩 돌리고 싶으면 위 표의 스크립트를 순서대로 실행하면 된다.

### 걸리는 시간 (참고)

역사학(학술지 194종, 논문 약 4.2만 편) 기준 실측치:

| 구간 | 시간 |
|---|---|
| KCI 수집 + 정제 | 약 3시간 |
| KRI 1단계 (1a~1c) | 약 10분 |
| KRI 2단계 (연구자 7,310명, 초당 약 0.6명) | 약 3시간 반 |

KRI 2단계는 연구자 수에 비례하므로, 1단계가 끝나 연구자 수가 나오면 `연구자 수 ÷ 0.6`초로 계산하면 된다. 긴 수집 중에는 PC 절전을 꺼 둔다.

---

## 새 분과 추가하기

코드는 고치지 않는다. `config.py`에 분과 하나를 추가하고 `ACTIVE`만 바꾸면 된다.

```python
LINGUISTICS = Discipline(
    code="A0?",                        # KCI 분야코드
    name="언어학",                      # 학술지종수.xls의 중분류명과 같아야 함
    target_field="인문학 > 언어학",
    journals_csv="언어학_결과/journals.csv",
    out_dir="언어학_결과",
)
ACTIVE = LINGUISTICS
```

`name`은 정제 단계에서 "자기 분과"를 판별하는 기준이 되므로 `학술지종수.xls`의 중분류명과 똑같이 적어야 한다. 학술지 목록은 파이프라인 첫 단계가 자동으로 만든다.

---

## 결과 파일

### KCI — `KCI-Data/<분과>_결과/`

| 파일 | 내용 |
|---|---|
| `korlit_2008_2024.pkl` / `.csv` | 수집 원본 (논문 1편당 1행, 34개 컬럼) |
| `korlit_2008_2024_clean.pkl` / `.csv` | 정제본. 피인용 항목에 `journal_clean`, `field_major`, `field_minor`, `resolve_src` 추가 |
| `journals.csv` | 분과 전체 학술지 목록 |
| `journal_article_counts.csv` | 학술지별 논문 수 요약 |

pkl·csv 본체는 용량 때문에 git에 올라가지 않는다. 필요하면 별도로 공유한다. A11 정제본만 예외적으로 `KCI-Data/new-results_(선영보낼것)/`에 있다.

### KRI — `KRI-Data/<분야코드>/`

| 파일 | 내용 |
|---|---|
| `author_paper_kri.csv` | 논문×저자 1행씩, 연구자정보가 붙은 분석용 마스터 |
| `researchers.csv` | 연구자 1명당 1행 (성명·성별·출생년도·소속·직급·재직여부·전공분야·세부전공·출신학교·학위) |
| `kri_mapping.csv` | 논문·저자·crt_id·kri_num 연결표 |

KRI 결과는 개인정보가 포함되어 있어 git에 올리지 않는다.

---

## 주의

- **KCI 피인용 수치는 정제본 기준으로 쓴다.** 원본 `journal` 필드로 분과를 세면 오염 때문에 외부 피인용이 크게 과소집계된다.
- **KRI 결측은 무작위가 아니다.** 미등록 저자와 비공개 연구자가 빠지므로, 분석할 때 표본 편향으로 명시한다.
- **학술지 수와 논문이 잡힌 학술지 수는 다를 수 있다.** KCI 분류 목록에는 호수별로 따로 등록된 자료집이나 기간 내 게재가 없는 학술지도 섞여 있다.
