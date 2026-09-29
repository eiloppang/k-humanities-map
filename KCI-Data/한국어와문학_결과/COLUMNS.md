# 한국어와문학 데이터셋 — 컬럼 설명

연구분야 `인문학 > 한국어와문학` 학술지의 2008~2024년 논문을 KCI에서 수집한 데이터입니다.

- **파일**: `korlit_2008_2024.csv` (사람이 보기용), `korlit_2008_2024.pkl` (분석용, 중첩 데이터가 파이썬 객체 그대로 보존됨)
- **샘플**: `_sample.csv` / `_sample.pkl` (처음 N편만 뽑은 검증용)
- CSV에서는 리스트/구조 데이터(`authors_*`, `keywords_*`, `references`, `cited_by` 등)가 **JSON 문자열**로 저장됩니다. pickle에서는 파이썬 list/dict 그대로입니다.

---

## 식별자

| 열 | 설명 | 예시 |
|---|---|---|
| `article_id` | KCI 논문 고유 ID. 상세페이지·인용 네트워크의 노드 키. | `ART002536712` |
| `crt_id` | KCI **인용 보고서(Citation Report) ID**. 이 논문의 인용현황 상세를 조회하는 키. 인용 네트워크 분석 시 사용. | `CRT001511860` |
| `sere_id` | 학술지 고유 ID. (`SER000003940` 또는 `001210` 형식 둘 다 존재) | `SER000003940` |

## 서지 — 제목·학술지·발행

| 열 | 설명 |
|---|---|
| `title_ko` | 논문 제목 (국문) |
| `title_en` | 논문 제목 (영문) — KCI 메타태그 기준 |
| `journal_ko` | 학술지명 (국문) |
| `journal_en` | 학술지명 (영문) |
| `publisher_ko` | 발행기관 (국문) 예: 한국비평문학회 |
| `publisher_en` | 발행기관 (영문) |
| `pub_year` | 발행연도 |
| `volume` | 권(volume). KCI에 권 구분이 없는 학술지는 빈 값일 수 있음(호만 사용). |
| `issue` | 호(issue/number) |
| `pages` | 페이지 표기 `시작~끝` (예: `611~640`) |
| `page_start` / `page_end` | 시작/끝 페이지 (숫자 분리) |
| `doi` | DOI. **구논문·DOI 미부여 논문은 빈 값**(정상). |
| `issn` | 학술지 ISSN |
| `pub_vol_raw` | 상세페이지의 권/호 원문 표기(보정 전 원본, 검증용) |

## 분류

| 열 | 설명 |
|---|---|
| `research_field` | 이 **논문**의 KCI 세부 연구분야 (예: `인문학 > 한국어와문학`, 또는 더 세부 분류). |
| `journal_field` | 이 **학술지**의 대표 연구분야 = 수집 기준값 `인문학 > 한국어와문학` (전 행 동일). |

## 저자

| 열 | 설명 |
|---|---|
| `authors_ko` | 저자명 리스트 (국문). 예: `["최창헌"]` |
| `authors_en` | 저자명 리스트 (영문/로마자). 예: `["Choi, Chang-Heon"]` |
| `affiliations` | 저자 소속기관 리스트. 예: `["상지대학교"]` |

## 본문 요약

| 열 | 설명 |
|---|---|
| `abstract_ko` | 국문 초록 |
| `abstract_en` | 영문 초록 |
| `keywords_ko` | 키워드 리스트 (국문). 예: `["문학 교과서","동질성",...]` |
| `keywords_en` | 키워드 리스트 (영문) |

## 인용현황 (지평도 핵심)

| 열 | 설명 |
|---|---|
| `cited_count` | KCI **피인용 횟수**(이 논문이 인용된 총 횟수, KCI가 집계한 수치). |
| `fwci` | FWCI (Field-Weighted Citation Impact) — 같은 연도·분야·논문형태로 정규화한 인용지수. 없으면 빈 값. |
| `view_count` | 열람 수 |
| `ref_count` | 참고문헌 개수 (= `references` 길이) |
| `citing_count` | 이 논문을 인용한 논문 개수 (= `cited_by` 길이) |
| `references` | **참고문헌 목록**. 이 논문이 인용한 문헌들. 각 항목: `{n, type, art_id, text}`<br>· `type`: `학술논문`/`단행본` 등<br>· `art_id`: KCI 등록 논문이면 그 ID(없으면 빈 값 — 단행본 등)<br>· `text`: 서지 원문 |
| `cited_by` | **피인용 목록**. 이 논문을 인용한 논문들(=인용 네트워크의 들어오는 엣지). 각 항목: `{art_id, crt_id, title, authors, journal, pub_date, pages, cited_count}` |

---

### 인용 네트워크(지평도) 만들 때

- **나가는 엣지**(이 논문 → 참고문헌): `references` 중 `art_id`가 있는 항목 = KCI 내부 인용 링크.
- **들어오는 엣지**(이 논문 ← 피인용): `cited_by`의 `art_id` 각각이 이 논문을 인용한 노드.
- 두 방향을 합치면 `article_id` 노드 간 방향 그래프(인용 네트워크)를 구성할 수 있습니다.

### 주의 / 빈 값이 정상인 경우

- `cited_by`가 비어 있는데 `cited_count`가 0이면 정상(아직 인용 안 됨).
- **최근 논문**은 KCI 안내처럼 "인용논문 목록은 해당연도 인용지수 공개 후 확정"되므로, `cited_count`가 0보다 커도 목록(`cited_by`)이 아직 비어 있을 수 있음.
- 2025년 이후 발행 논문의 `references`는 KCI에서 구축 중일 수 있음(본 데이터는 2008~2024 대상).
