# -*- coding: utf-8 -*-
"""Stage 1c: (article, 저자, cretId, kri_num) 매핑 테이블 구축.

입력:
  - korlit_2008_2024.pkl        (article_id, authors_ko, crt_id=제1저자 cret)
  - KRI/_paper_crets.jsonl       (다저자 article -> 저자순 cret 리스트)
  - KRI/_krinum_cache.jsonl      (cret -> kri_num)

출력:
  - KRI/kri_mapping.csv          (article_id, author_idx, author_ko, cret_id, kri_num)
  - KRI/unique_kri.txt           (Stage 2 입력: 고유 kri_num)
"""
import sys, io, os, json, csv, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
D = config.ACTIVE
os.makedirs(D.kri_dir, exist_ok=True)

PKL = D.pkl
df = pd.read_pickle(PKL)

# cret -> kri_num
kri = {}
for l in open(D.krinum_cache, encoding="utf-8"):
    r = json.loads(l)
    if r.get("ok") and r.get("kri_num"):
        kri[r["cret"]] = r["kri_num"]
print(f"cret->kri_num 맵: {len(kri):,}")

# article -> 저자순 cret (다저자)
paper_crets = {}
for l in open(D.paper_crets, encoding="utf-8"):
    r = json.loads(l)
    paper_crets[r["article_id"]] = r["crets"]

rows, mismatch = [], 0
for r in df.itertuples(index=False):
    authors = list(r.authors_ko)
    if len(authors) <= 1:
        crets = [str(r.crt_id)] if str(r.crt_id).startswith("CRT") else []
    else:
        crets = paper_crets.get(r.article_id, [])
    if authors and crets and len(authors) != len(crets):
        mismatch += 1
    for i, name in enumerate(authors):
        cret = crets[i] if i < len(crets) else ""
        rows.append({"article_id": r.article_id, "author_idx": i,
                     "author_ko": name, "cret_id": cret,
                     "kri_num": kri.get(cret, "")})

with open(D.kri_mapping, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["article_id", "author_idx", "author_ko", "cret_id", "kri_num"])
    w.writeheader(); w.writerows(rows)

uniq = sorted({x["kri_num"] for x in rows if x["kri_num"]})
with open(D.unique_kri, "w", encoding="utf-8") as f:
    f.write("\n".join(uniq) + "\n")

n_rows = len(rows)
n_kri = sum(1 for x in rows if x["kri_num"])
print(f"매핑 행(저자-논문): {n_rows:,}")
print(f"  kri_num 확보: {n_kri:,} ({n_kri/n_rows*100:.1f}%)")
print(f"  저자수≠cret수 불일치 논문: {mismatch:,}")
print(f"고유 kri_num(연구자, Stage 2 대상): {len(uniq):,}")
print(f"저장: {D.kri_mapping}, {D.unique_kri}")
