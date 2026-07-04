# -*- coding: utf-8 -*-
"""cited_by 재수집 규모 산정 (읽기 전용).

산출:
  1) cited_by 전체 항목 수 / art_id 보유율
  2) 고유 art_id 수, 그중 korlit(A11) 내부 보유분 vs 외부(API 필요)분
     - 고유 art_id 기준 + 발생(occurrence) 기준 둘 다
  3) 내부 art_id로 해소되는 항목에서 journal 오염률 직접 측정
     (저장된 journal vs 진짜 journal_ko 비교)
"""
import sys, io, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PKL = "Data/한국어와문학_결과2/korlit_2008_2024.pkl"
df = pd.read_pickle(PKL)

# 내부 A11 art_id -> 진짜 저널명
internal = dict(zip(df.article_id.astype(str), df.journal_ko.astype(str)))
internal_ids = set(internal)
print(f"내부(A11) 논문 수: {len(internal_ids):,}")

total_entries = 0          # cited_by 전체 항목 수
entries_with_artid = 0     # art_id 채워진 항목
uniq_artids = {}           # art_id -> 발생횟수
empty_cb = 0

for cb in df.cited_by:
    if not isinstance(cb, (list, tuple)) or len(cb) == 0:
        empty_cb += 1
        continue
    for c in cb:
        if not isinstance(c, dict):
            continue
        total_entries += 1
        aid = c.get("art_id")
        aid = str(aid).strip() if aid not in (None, "") else ""
        if aid:
            entries_with_artid += 1
            uniq_artids[aid] = uniq_artids.get(aid, 0) + 1

print(f"\n=== 1) cited_by 항목 규모 ===")
print(f"cited_by 없는 논문: {empty_cb:,} / {len(df):,}")
print(f"cited_by 전체 항목 수: {total_entries:,}")
print(f"  art_id 보유 항목: {entries_with_artid:,} ({entries_with_artid/total_entries*100:.1f}%)")
print(f"  art_id 없는 항목: {total_entries-entries_with_artid:,}")

# 고유 art_id 기준
uids = set(uniq_artids)
uid_internal = uids & internal_ids
uid_external = uids - internal_ids
print(f"\n=== 2) 고유 art_id 기준 ===")
print(f"고유 art_id 수: {len(uids):,}")
print(f"  내부(A11, 즉시 조회): {len(uid_internal):,} ({len(uid_internal)/len(uids)*100:.1f}%)")
print(f"  외부(API 추가수집):  {len(uid_external):,} ({len(uid_external)/len(uids)*100:.1f}%)")

# 발생(occurrence) 기준 — 실제로 고쳐야 할 '칸' 수
occ_internal = sum(n for a, n in uniq_artids.items() if a in internal_ids)
occ_external = entries_with_artid - occ_internal
print(f"\n=== 2') 발생(occurrence) 기준 — 실제 수정 대상 항목 수 ===")
print(f"art_id 보유 항목: {entries_with_artid:,}")
print(f"  내부로 즉시 해소: {occ_internal:,} ({occ_internal/entries_with_artid*100:.1f}%)")
print(f"  API 조회 필요:    {occ_external:,} ({occ_external/entries_with_artid*100:.1f}%)")

# 3) 오염률 직접 측정: 내부 art_id 항목에서 저장 journal vs 진짜 journal_ko
def norm(s):
    return "".join(str(s).split()).replace(" ", "")

match = mismatch = checked = 0
mism_samples = []
for cb in df.cited_by:
    if not isinstance(cb, (list, tuple)):
        continue
    for c in cb:
        if not isinstance(c, dict):
            continue
        aid = c.get("art_id")
        aid = str(aid).strip() if aid not in (None, "") else ""
        if aid and aid in internal:
            checked += 1
            stored = norm(c.get("journal"))
            truth = norm(internal[aid])
            if stored == truth or (truth and truth in stored) or (stored and stored in truth):
                match += 1
            else:
                mismatch += 1
                if len(mism_samples) < 8:
                    mism_samples.append((c.get("authors"), c.get("journal"), internal[aid]))

print(f"\n=== 3) 내부 art_id 항목 오염률 (저장 journal vs 진짜 journal_ko) ===")
print(f"대조 항목: {checked:,}")
if checked:
    print(f"  일치(정상): {match:,} ({match/checked*100:.1f}%)")
    print(f"  불일치(오염 의심): {mismatch:,} ({mismatch/checked*100:.1f}%)")
print("  --- 불일치 예시 (authors | 저장journal | 진짜journal) ---")
for a, j, t in mism_samples:
    print(f"    {a} | {j!r} | {t!r}")
