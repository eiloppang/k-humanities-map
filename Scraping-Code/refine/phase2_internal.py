# -*- coding: utf-8 -*-
"""Phase 2: cited_by 내부(A11) 즉시 복구 + Phase 3용 외부 art_id 워크리스트 생성.

- 내부 art_id 항목: journal_ko/journal_field/research_field 를 즉시 확보
- 외부 art_id: 고유 목록을 _external_artids.txt 로 저장 (Phase 3 입력)
- 내부 해소 맵을 _internal_resolved.json 으로 저장 (Phase 4 병합용)

원본 cited_by 의 journal 은 절대 수정하지 않는다(보존). 정제 결과는 별도 산출물.
"""
import sys, io, os, json, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
D = config.ACTIVE
os.makedirs(D.out_dir, exist_ok=True)
PKL = D.pkl
df = pd.read_pickle(PKL)

# 내부 A11 art_id -> 진짜 저널/분과정보
internal = {}
for r in df.itertuples(index=False):
    internal[str(r.article_id)] = {
        "journal_ko": str(r.journal_ko),
        "journal_field": str(r.journal_field),     # = "인문학 > 한국어와문학"
        "research_field": str(getattr(r, "research_field", "")),
        "publisher_ko": str(getattr(r, "publisher_ko", "")),
    }
internal_ids = set(internal)
print(f"내부({D.code}) art_id: {len(internal_ids):,}")

ext_ids = set()
n_entries = n_internal = 0
for cb in df.cited_by:
    if not isinstance(cb, (list, tuple)):
        continue
    for c in cb:
        if not isinstance(c, dict):
            continue
        n_entries += 1
        aid = str(c.get("art_id") or "").strip()
        if not aid:
            continue
        if aid in internal_ids:
            n_internal += 1
        else:
            ext_ids.add(aid)

print(f"cited_by 항목: {n_entries:,}")
print(f"  내부 즉시 해소: {n_internal:,} ({n_internal/n_entries*100:.1f}%)")
print(f"  외부 고유 art_id (Phase 3 조회 대상): {len(ext_ids):,}")

# 외부 워크리스트 저장 (정렬해 결정적)
ext_sorted = sorted(ext_ids)
with open(D.ext_worklist, "w", encoding="utf-8") as f:
    f.write("\n".join(ext_sorted) + "\n")
print(f"\n저장: {D.ext_worklist}  ({len(ext_sorted):,}개)")

# 내부 해소 맵 저장 (Phase 4 에서 cited_by 채울 때 사용)
with open(D.internal_resolved, "w", encoding="utf-8") as f:
    json.dump(internal, f, ensure_ascii=False)
print(f"저장: {D.internal_resolved}  ({len(internal):,}개)")
