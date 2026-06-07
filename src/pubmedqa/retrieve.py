"""Hybrid retrieval: BM25 (FTS5) + dense (LanceDB) -> RRF -> bounded citation re-score.

v1 is lean: no cross-encoder. Citation impact is a *bounded booster* applied only
after a relevance gate, so a famous-but-off-topic paper can't surface (plan §5E).
"""
import math
import re
from . import config, db, embed, vectorstore


def _fts_query(text):
    """Build a safe FTS5 MATCH string: OR of quoted alphanumeric tokens."""
    toks = [t for t in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(t) > 2]
    return " OR ".join(f'"{t}"' for t in toks) if toks else None


def _rrf(rank_lists, k=config.RRF_K):
    scores = {}
    for ranks in rank_lists:
        for pos, pmid in enumerate(ranks):
            scores[pmid] = scores.get(pmid, 0.0) + 1.0 / (k + pos + 1)
    return scores


def _impact_norm(cit):
    """Map impact to 0..1. RCR (field-normalized) preferred; else log citations."""
    if not cit:
        return config.IMPACT_FLOOR
    rcr = cit.get("rcr")
    if rcr is not None:
        return 1.0 / (1.0 + math.exp(-(rcr - 1.0)))   # sigmoid centered at field median
    c = cit.get("citation_count")
    if c is not None:
        return max(config.IMPACT_FLOOR, min(1.0, math.log1p(c) / math.log1p(1000)))
    return config.IMPACT_FLOOR


def search(con, question, top_n=config.TOP_N_CONTEXT):
    qv = embed.embed_query(question)
    dense = vectorstore.search(qv, config.DENSE_TOPK)

    ftsq = _fts_query(question)
    lexical = db.bm25_search(con, ftsq, config.BM25_TOPK) if ftsq else []

    fused = _rrf([dense, lexical])
    if not fused:
        return []

    hi = max(fused.values())
    cits = db.fetch_citations(con, list(fused.keys()))

    ranked = []
    for pmid, s in fused.items():
        rel = s / hi if hi > 0 else 0.0
        final = rel if rel < config.RELEVANCE_GATE else \
            rel + config.ALPHA * _impact_norm(cits.get(pmid))
        ranked.append((pmid, final, rel))
    ranked.sort(key=lambda x: x[1], reverse=True)

    top = ranked[:top_n]
    papers = db.fetch_papers(con, [p for p, _, _ in top])
    results = []
    for pmid, final, rel in top:
        p = papers.get(pmid, {"pmid": pmid})
        c = cits.get(pmid, {})
        results.append({**p, "pmid": pmid, "score": final, "relevance": rel,
                        "citation_count": c.get("citation_count"), "rcr": c.get("rcr")})
    return results
