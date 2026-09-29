# -*- coding: utf-8 -*-
"""학술지별 논문 수 요약 — 수집 원본(korlit pkl)에서 journal_article_counts.csv 생성.

출력: <out_dir>/journal_article_counts.csv  (학술지, 논문수 — 논문수 내림차순)

사용: python Scraping-Code/kci/journal_counts.py   # config.ACTIVE 분과
"""
import os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Scraping-Code
import config
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

D = config.ACTIVE
OUT = os.path.join(D.out_dir, "journal_article_counts.csv")

df = pd.read_pickle(D.pkl)
counts = (df.groupby("journal_ko").size()
            .sort_values(ascending=False)
            .rename("논문수").reset_index()
            .rename(columns={"journal_ko": "학술지"}))
counts.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"저장: {OUT}  (학술지 {len(counts)}종, 논문 {int(counts['논문수'].sum()):,}편)")
