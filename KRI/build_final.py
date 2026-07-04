# -*- coding: utf-8 -*-
"""Stage 3: 수집한 연구자정보 + kri_mapping 병합 → 최종 산출.

출력:
  KRI/researchers.csv        연구자 1명/행 (kri_num + 7필드 + 상태)
  KRI/author_paper_kri.csv   (논문×저자)별 연구자정보 조인 (분석용 마스터)
"""
import sys, io, json, csv, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FIELDS = ["성명", "성별", "출생년도", "소속대학기관", "직급", "재직여부",
          "전공분야", "세부전공명", "출신학교_학위수여대학", "취득학위",
          "성명_한자", "성명_영문"]

# 1) 연구자 캐시 (최신 1건/kri)
latest = {}
for l in open("KRI/_kri_cache.jsonl", encoding="utf-8"):
    try: r = json.loads(l)
    except Exception: continue
    latest[r["kri_num"]] = r

researchers = []
for kri, r in latest.items():
    row = {"kri_num": kri, "status": r.get("status", "")}
    for f in FIELDS:
        row[f] = r.get(f, "")
    researchers.append(row)

with open("KRI/researchers.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["kri_num", "status"] + FIELDS)
    w.writeheader(); w.writerows(researchers)
print(f"researchers.csv: {len(researchers):,}명 "
      f"(ok {sum(1 for x in researchers if x['status']=='ok'):,} / "
      f"비공개 {sum(1 for x in researchers if x['status']=='private'):,})")

# 2) 매핑과 조인
m = pd.read_csv("KRI/kri_mapping.csv", dtype=str).fillna("")
ri = pd.DataFrame(researchers).fillna("")
merged = m.merge(ri, on="kri_num", how="left").fillna("")
merged.to_csv("KRI/author_paper_kri.csv", index=False, encoding="utf-8-sig")

has_kri = (m["kri_num"] != "").sum()
joined = ((merged["status"] == "ok")).sum()
print(f"author_paper_kri.csv: {len(merged):,}행 (논문×저자)")
print(f"  kri_num 보유 행: {has_kri:,}")
print(f"  연구자정보(ok) 조인 행: {joined:,}")
print(f"  고유 연구자(데이터 보유): {(ri['status']=='ok').sum():,}")

# 3) 간단 분포 미리보기
ok = ri[ri["status"] == "ok"]
print("\n=== 소속기관 Top10 ===")
for name, n in ok["소속대학기관"].value_counts().head(10).items():
    print(f"  {n:>4}  {name}")
print("\n=== 직급 Top8 ===")
for name, n in ok["직급"].value_counts().head(8).items():
    print(f"  {n:>4}  {name}")
