# -*- coding: utf-8 -*-
"""cited_by 구조 확인 + 오염 사례 재현 (읽기 전용 진단)."""
import sys, pandas as pd

PKL = "Data/한국어와문학_결과2/korlit_2008_2024.pkl"
df = pd.read_pickle(PKL)

print("=== shape ===", df.shape)
print("=== columns ===")
print(list(df.columns))
print("=== dtypes (cited_by/references/article_id) ===")
for c in ("article_id", "cited_by", "references"):
    if c in df.columns:
        print(f"  {c}: {df[c].dtype}")

# cited_by 한 항목의 키 구조
row = df[df.article_id == "ART002602737"]
print("\n=== ART002602737 존재? ===", len(row))
if len(row):
    cb = row.iloc[0].cited_by
    print("cited_by type:", type(cb), "len:", (len(cb) if hasattr(cb, "__len__") else "n/a"))
    if hasattr(cb, "__len__") and len(cb):
        print("첫 항목 키:", list(cb[0].keys()) if isinstance(cb[0], dict) else type(cb[0]))
        print("\n--- 오염 재현 (authors | journal) 처음 8건 ---")
        for c in cb[:8]:
            print("  ", c.get("authors"), "|", repr(c.get("journal")))
