# -*- coding: utf-8 -*-
"""115개 저널 전체 분과 프로필 비교(HTML) + 타분과 최다인용 논문 Top100.
데이터 1회 스캔으로 (a)저널별 인용 분과 분포, (b)논문별 타분과 피인용수 동시 계산.
출력: Data/한국어와문학_결과2/통계/전체결과/
  전체비교.html, 저널별_분과프로필.csv, 타분과_최다인용_논문Top100.csv
"""
import sys, io, os, csv, re, html as H
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import defaultdict, Counter
import pandas as pd

BASE = "Data/한국어와문학_결과2"
OUT = f"{BASE}/통계/전체결과"
os.makedirs(OUT, exist_ok=True)
_cut = re.compile(r"\s*[\d０-９(（].*$")
_nm = lambda s: re.sub(r"\s+", "", str(s or "")).lower()
ref_journal = lambda t: _cut.sub("", t.split(" / ")[-1].split(" : ")[0]).strip()
SELF_FIELD = "한국어와문학"

# 분과 맵 (xls: 한글명·외국어명·괄호앞부분)
disc = {}
xls = pd.read_excel("학술지종수.xls", header=None, engine="xlrd").iloc[2:]
for _, x in xls.iterrows():
    d = (str(x[8]).strip(), str(x[9]).strip())
    for k in {_nm(x[4]), _nm(x[5]), _nm(str(x[4]).split("(")[0])}:
        if k and k not in disc:
            disc[k] = d

df = pd.read_pickle(f"{BASE}/korlit_2008_2024.pkl")
home = df.groupby("sere_id")["journal_ko"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else "")
pcount = df["sere_id"].value_counts().to_dict()

prof_maj = defaultdict(Counter)     # sid -> 대분류 Counter
prof_mid = defaultdict(Counter)     # sid -> 중분류 Counter
cross_rows = []
for r in df.itertuples(index=False):
    sid = r.sere_id
    hn = home.get(sid, "")
    selfk = {_nm(hn), _nm(hn.split("(")[0])}
    citing = Counter()
    cross = 0
    for cb in (r.cited_by or []):
        j = (cb.get("journal") or "").strip()
        nj = _nm(j)
        if not nj or nj in selfk:
            continue
        d = disc.get(nj)
        if not d:
            continue
        prof_maj[sid][d[0]] += 1
        prof_mid[sid][d[1]] += 1
        if d[1] != SELF_FIELD:
            cross += 1
            citing[d[1]] += 1
    for ref in (r.references or []):
        if "학술지" in (ref.get("type") or ""):
            j = ref_journal(ref.get("text", ""))
            nj = _nm(j)
            if not nj or nj in selfk or len(j) < 2:
                continue
            d = disc.get(nj)
            if not d:
                continue
            prof_maj[sid][d[0]] += 1
            prof_mid[sid][d[1]] += 1
    cross_rows.append((cross, int(r.cited_count or 0), r.article_id,
                       (r.title_ko or r.title_en or ""), hn, r.pub_year, r.doi,
                       "; ".join(f"{k}({v})" for k, v in citing.most_common(3))))

# ── 타분과 최다인용 Top100 ──
cross_rows.sort(key=lambda x: (-x[0], -x[1]))
with open(f"{OUT}/타분과_최다인용_논문Top100.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["순위", "타분과_피인용수", "총_피인용", "비율(%)", "제목", "학술지", "연도",
                "DOI", "article_id", "인용한_주요분과"])
    for i, (cr, cc, aid, ti, jn, yr, doi, td) in enumerate(cross_rows[:100], 1):
        w.writerow([i, cr, cc, round(100*cr/cc, 1) if cc else 0, ti, jn, yr, doi, aid, td])
print(f"타분과 최다인용 Top100 저장. 1위 교차분과 피인용수 = {cross_rows[0][0]}")

# ── 저널별 분과 프로필 ──
MID_COLS = ["한국어와문학", "언어학", "역사학", "교육학", "사회학", "철학", "문학"]
MAJ_COLS = ["인문학", "사회과학", "복합학", "예술체육학"]
prows = []
for sid in sorted(pcount, key=lambda s: -pcount[s]):
    tot = sum(prof_mid[sid].values())
    if tot == 0:
        continue
    midp = {c: round(100*prof_mid[sid].get(c, 0)/tot, 1) for c in MID_COLS}
    majp = {c: round(100*prof_maj[sid].get(c, 0)/tot, 1) for c in MAJ_COLS}
    prows.append({"학술지": home.get(sid, sid), "sere_id": sid, "논문수": pcount[sid],
                  "분과상호작용": tot, **{f"중_{c}": midp[c] for c in MID_COLS},
                  **{f"대_{c}": majp[c] for c in MAJ_COLS},
                  "분야밖%": round(100 - midp["한국어와문학"], 1),
                  "인문학밖%": round(100 - majp["인문학"], 1)})

# CSV (raw)
flds = (["학술지", "sere_id", "논문수", "분과상호작용"] + [f"중_{c}" for c in MID_COLS]
        + [f"대_{c}" for c in MAJ_COLS] + ["분야밖%", "인문학밖%"])
with open(f"{OUT}/저널별_분과프로필.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=flds); w.writeheader(); w.writerows(prows)

# ── HTML ──
cols = [("학술지", "s"), ("논문수", "n"), ("분과상호작용", "n"),
        ("한국어와문학", "p"), ("언어학", "p"), ("역사학", "p"), ("교육학", "p"),
        ("사회학", "p"), ("철학", "p"), ("문학", "p"),
        ("인문학", "p"), ("사회과학", "p"), ("복합학", "p"), ("예술체육학", "p"),
        ("분야밖", "p"), ("인문학밖★", "p")]
COL_INMUN = 15      # '인문학밖' 열 인덱스 (로드시 이 열로 내림차순 정렬)


def cell_pct(v):
    a = min(v / 60, 1.0)                       # 60%에서 최대 진하기
    return f'background:rgba(36,113,163,{a:.2f});color:{"#fff" if a>0.55 else "#000"}'


def cell_inter(v, mx):
    a = min(v / mx, 1.0) if mx else 0
    return f'background:rgba(192,57,43,{a*0.8:.2f});color:{"#fff" if a>0.6 else "#000"}'


mx_inter = max((r["분과상호작용"] for r in prows), default=1)
body = []
for r in prows:
    tds = [f'<td class="name">{H.escape(str(r["학술지"]))}</td>',
           f'<td data-v="{r["논문수"]}">{r["논문수"]:,}</td>',
           f'<td data-v="{r["분과상호작용"]}" style="{cell_inter(r["분과상호작용"],mx_inter)}">{r["분과상호작용"]:,}</td>']
    for c in ["한국어와문학", "언어학", "역사학", "교육학", "사회학", "철학", "문학"]:
        v = r[f"중_{c}"]; tds.append(f'<td data-v="{v}" style="{cell_pct(v)}">{v}</td>')
    for c in ["인문학", "사회과학", "복합학", "예술체육학"]:
        v = r[f"대_{c}"]; tds.append(f'<td data-v="{v}" style="{cell_pct(v)}">{v}</td>')
    v = r["분야밖%"]      # 중분류 기준(좁은 분야 밖) — 연한 회녹색
    tds.append(f'<td data-v="{v}" style="background:rgba(127,140,141,{min(v/70,1)*0.5:.2f})">{v}</td>')
    v2 = r["인문학밖%"]   # 대분류 기준(진짜 학제성) — 진한 초록 강조
    tds.append(f'<td data-v="{v2}" style="background:rgba(39,174,96,{min(v2/50,1)*0.85:.2f});font-weight:bold">{v2}</td>')
    body.append("<tr>" + "".join(tds) + "</tr>")

ths = "".join(f'<th onclick="sortT({i})">{c[0]}{" ▾" if c[1]!="s" else ""}</th>'
              for i, c in enumerate(cols))
doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>한국어와문학 115개 학술지 — 분과 프로필 비교</title>
<style>
 body{{font-family:'Malgun Gothic',sans-serif;margin:18px;color:#222}}
 h1{{font-size:20px}} p.desc{{color:#555;font-size:13px;line-height:1.6}}
 table{{border-collapse:collapse;font-size:12px}}
 th,td{{border:1px solid #ddd;padding:4px 7px;text-align:right;white-space:nowrap}}
 th{{position:sticky;top:0;background:#34495e;color:#fff;cursor:pointer;font-size:12px}}
 th:first-child,td.name{{text-align:left}} td.name{{position:sticky;left:0;background:#fafafa;font-weight:bold}}
 tr:hover td{{outline:1px solid #f39c12}}
 .wrap{{overflow:auto;max-height:82vh;border:1px solid #ccc}}
 .grp{{color:#888;font-size:11px;margin:4px 0}}
</style></head><body>
<h1>한국어와문학 115개 학술지 — 인용 분과 프로필 비교</h1>
<p class="desc">각 학술지가 인용/피인용으로 연결된 상대 학술지의 <b>분과(KCI 대·중분류)</b>를 비율(%)로 환산.
값 = 해당 분과와의 인용 상호작용 ÷ 그 학술지의 전체(자기인용·비KCI 문예지 제외).
파랑(중·대분류 %)·초록(학제성)·빨강(상호작용수)으로 색칠. <b>열 제목 클릭 = 정렬</b>.
<br>· 중분류: 한국어와문학(본령)·언어학·역사학·교육학·사회학·철학·문학  · 대분류: 인문학·사회과학·복합학·예술체육학
<br>· <b>분야밖%</b> = 100 − 한국어와문학(중분류)% (기타인문학·역사학·언어학 등 <u>옆 인문학 분야까지</u> 포함 → 높게 나옴, 참고용)
<br>· <b>인문학밖%★</b> = 100 − 인문학(대분류)% = <b>진짜 학제성</b> (인문학을 벗어나 사회과학·복합학 등 <u>다른 학문</u>과 교류한 비율). <b>기본 정렬 = 이 열 내림차순.</b></p>
<div class="grp">학술지 {len(prows)}종 · 데이터 2008~2024 · 분과 출처: 학술지종수.xls</div>
<div class="wrap"><table id="t"><thead><tr>{ths}</tr></thead><tbody>
{''.join(body)}
</tbody></table></div>
<script>
let asc={{}};
function sortT(n){{
 const tb=document.querySelector('#t tbody');
 const rows=[...tb.rows];
 asc[n]=!asc[n];const k=asc[n]?1:-1;
 rows.sort((a,b)=>{{
  let x=a.cells[n].dataset.v??a.cells[n].innerText, y=b.cells[n].dataset.v??b.cells[n].innerText;
  const nx=parseFloat(x),ny=parseFloat(y);
  if(!isNaN(nx)&&!isNaN(ny))return (nx-ny)*k;
  return (''+x).localeCompare(''+y,'ko')*k;
 }});
 rows.forEach(r=>tb.appendChild(r));
}}
asc[{COL_INMUN}]=true; sortT({COL_INMUN});   // 로드시 '인문학밖' 내림차순 정렬
</script></body></html>"""
open(f"{OUT}/전체비교.html", "w", encoding="utf-8").write(doc)
print(f"저장: {OUT}/ (전체비교.html, 저널별_분과프로필.csv, 타분과_최다인용_논문Top100.csv)")
print(f"  저널 {len(prows)}종, HTML 컬럼 {len(cols)}개")
