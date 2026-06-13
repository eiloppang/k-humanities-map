# -*- coding: utf-8 -*-
"""한 학술지의 인용 네트워크(지평도) 구성 — 어문연구(語文硏究, sereId 000452) 예시.

COLUMNS.md 의 방법대로 references(나가는 인용) + cited_by(들어오는 인용)로
article_id 간 방향 그래프를 만든다.
  - 내부 네트워크: 어문연구 논문들 사이의 인용(저널 내부 지적 구조)
  - 전체(ego) 네트워크: 어문연구 논문이 인용하거나/인용받은 모든 엣지
출력(Data/한국어와문학_결과2/network_어문연구/):
  internal_edges.csv, nodes.csv, network.graphml  (Gephi/Cytoscape 로 시각화)
  + 콘솔에 요약 통계.
"""
import os, sys, io, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import pandas as pd
import networkx as nx

PKL = "Data/한국어와문학_결과2/korlit_2008_2024.pkl"
SERE_ID = "000452"                 # 어문연구(語文硏究) — 동명 2종 중 논문 최다
OUT = "Data/한국어와문학_결과2/network_어문연구"
os.makedirs(OUT, exist_ok=True)

df = pd.read_pickle(PKL)
jour = df[df["sere_id"] == SERE_ID].copy()
S = set(jour["article_id"])
print(f"어문연구(語文硏究) 논문 수: {len(jour)}")

# 노드 메타
meta = {r["article_id"]: {"title": (r["title_ko"] or r["title_en"] or "")[:80],
                          "year": str(r["pub_year"]), "cited_count": int(r["cited_count"] or 0)}
        for _, r in jour.iterrows()}

# 엣지 구성 (방향: 인용하는 쪽 -> 인용받는 쪽)
internal, ego = set(), set()
for _, r in jour.iterrows():
    a = r["article_id"]
    for ref in (r["references"] or []):                 # a 가 ref 를 인용 (a -> ref)
        rid = ref.get("art_id")
        if rid:
            ego.add((a, rid))
            if rid in S:
                internal.add((a, rid))
    for cb in (r["cited_by"] or []):                     # cb 가 a 를 인용 (cb -> a)
        cid = cb.get("art_id")
        if cid:
            ego.add((cid, a))
            if cid in S:
                internal.add((cid, a))

# 내부 그래프
G = nx.DiGraph()
for n in S:
    G.add_node(n, **meta[n])
G.add_edges_from(internal)

# 저장: 내부 엣지
with open(f"{OUT}/internal_edges.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["source", "target"]); w.writerows(sorted(internal))
# 노드(시각화에 쓸 메타)
with open(f"{OUT}/nodes.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "title", "year", "cited_count",
                                   "in_degree_internal", "out_degree_internal"])
    for n in S:
        w.writerow([n, meta[n]["title"], meta[n]["year"], meta[n]["cited_count"],
                    G.in_degree(n), G.out_degree(n)])
# GraphML (Gephi/Cytoscape)
nx.write_graphml(G, f"{OUT}/network.graphml")

# ---- 요약 통계 ----
nedges = G.number_of_edges()
connected = [n for n in G.nodes if G.degree(n) > 0]
print(f"\n[내부 인용 네트워크] (어문연구 논문끼리)")
print(f"  노드(논문): {G.number_of_nodes()}  | 내부 인용 엣지: {nedges}")
print(f"  내부 인용에 참여한 논문: {len(connected)} ({100*len(connected)/len(S):.1f}%)")
if nedges:
    ud = G.to_undirected()
    comps = list(nx.connected_components(ud))
    big = max(comps, key=len)
    print(f"  연결요소: {len(comps)}개, 최대 요소 크기: {len(big)}")
    print(f"\n  ▶ 저널 내부에서 가장 많이 인용된 논문 Top 10 (내부 피인용 = in-degree):")
    top = sorted(G.nodes, key=lambda n: G.in_degree(n), reverse=True)[:10]
    for n in top:
        d = G.in_degree(n)
        if d == 0: break
        print(f"     [{d:2d}회] {meta[n]['year']} {meta[n]['title'][:46]}")

print(f"\n[전체(ego) 네트워크] (외부 포함)")
print(f"  어문연구 논문이 인용한/인용받은 총 엣지: {len(ego)}")
ext_nodes = {x for e in ego for x in e} - S
print(f"  연결된 외부 논문(타 저널 등): {len(ext_nodes)}")

# 어문연구를 인용한 '저널' 분포 (cited_by 의 journal 필드)
from collections import Counter
jc = Counter()
for _, r in jour.iterrows():
    for cb in (r["cited_by"] or []):
        if cb.get("journal"):
            jc[cb["journal"]] += 1
print(f"\n  ▶ 어문연구를 가장 많이 인용한 학술지 Top 10:")
for j, c in jc.most_common(10):
    print(f"     {c:4d}회  {j[:30]}")

print(f"\n저장 위치: {OUT}/ (internal_edges.csv, nodes.csv, network.graphml)")
