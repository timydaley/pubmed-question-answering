#!/usr/bin/env python3
"""Compare two retrieval/evaluation JSON artifacts.

Reports per-question latency deltas, context-group changes, PMID overlap,
added/removed papers, rank moves, and judge-score deltas when present.

Usage:
  python scripts/compare_eval.py baseline_retrieval_v3.json baseline_retrieval_v4.json
  python scripts/compare_eval.py judged_old.json judged_new.json --titles 5
"""
import argparse
import json
from pathlib import Path


def load_results(path: Path):
    data = json.load(open(path))
    if isinstance(data, dict) and "results" in data:
        rows = data["results"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError(f"Unsupported eval JSON format: {path}")
    return {r["question"]: r for r in rows}


def fmt_delta(value, unit=""):
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}{unit}"


def group_counts(row):
    if row.get("context_group_counts"):
        return dict(row["context_group_counts"])
    out = {}
    for p in row.get("papers", []):
        g = p.get("context_group") or "unknown"
        out[g] = out.get(g, 0) + 1
    return out


def mean_judge(row):
    vals = []
    for p in row.get("papers", []):
        j = p.get("judge") or {}
        if isinstance(j.get("relevance"), (int, float)):
            vals.append(float(j["relevance"]))
    return sum(vals) / len(vals) if vals else None


def paper_maps(row):
    papers = row.get("papers", [])
    by_pmid = {int(p["pmid"]): p for p in papers if p.get("pmid") is not None}
    ranks = {int(p["pmid"]): i + 1 for i, p in enumerate(papers) if p.get("pmid") is not None}
    return by_pmid, ranks


def title(p):
    y = p.get("year") or "?"
    return f"[{p.get('pmid')}] ({y}) {p.get('title') or ''}"


def compare_question(q, a, b, max_titles):
    a_papers, a_ranks = paper_maps(a)
    b_papers, b_ranks = paper_maps(b)
    a_pmids, b_pmids = set(a_papers), set(b_papers)
    common = a_pmids & b_pmids
    added = [p for p in b.get("papers", []) if int(p.get("pmid", -1)) in (b_pmids - a_pmids)]
    removed = [p for p in a.get("papers", []) if int(p.get("pmid", -1)) in (a_pmids - b_pmids)]

    print(f"\n## {q}")
    print(f"retrieval: {a.get('retrieval_seconds')}s -> {b.get('retrieval_seconds')}s "
          f"({fmt_delta((b.get('retrieval_seconds') or 0) - (a.get('retrieval_seconds') or 0), 's')})")
    if a.get("generation_seconds") is not None or b.get("generation_seconds") is not None:
        av = a.get("generation_seconds") or 0
        bv = b.get("generation_seconds") or 0
        print(f"generation: {a.get('generation_seconds')}s -> {b.get('generation_seconds')}s "
              f"({fmt_delta(bv - av, 's')})")

    print(f"groups: {group_counts(a)} -> {group_counts(b)}")
    denom = max(len(a_pmids | b_pmids), 1)
    print(f"PMID overlap: {len(common)}/{denom} union; {len(common)}/{max(len(a_pmids), 1)} original")

    aj, bj = mean_judge(a), mean_judge(b)
    if aj is not None or bj is not None:
        delta = None if aj is None or bj is None else bj - aj
        print(f"mean judge relevance: {aj if aj is not None else 'n/a'} -> {bj if bj is not None else 'n/a'} "
              f"({fmt_delta(delta)})")

    moves = []
    for pmid in common:
        delta = a_ranks[pmid] - b_ranks[pmid]  # positive means moved up in b
        if delta:
            moves.append((abs(delta), delta, pmid))
    moves.sort(reverse=True)
    if moves:
        rendered = [f"[{pmid}] {('up' if d > 0 else 'down')} {abs(d)}" for _, d, pmid in moves[:max_titles]]
        print("rank moves:", "; ".join(rendered))

    if added:
        print("added:")
        for p in added[:max_titles]:
            print("  +", title(p))
    if removed:
        print("removed:")
        for p in removed[:max_titles]:
            print("  -", title(p))

    # Per-PMID judge deltas, if both artifacts have judge scores.
    judge_deltas = []
    for pmid in common:
        ja = (a_papers[pmid].get("judge") or {}).get("relevance")
        jb = (b_papers[pmid].get("judge") or {}).get("relevance")
        if isinstance(ja, (int, float)) and isinstance(jb, (int, float)) and ja != jb:
            judge_deltas.append((abs(jb - ja), jb - ja, pmid, ja, jb))
    judge_deltas.sort(reverse=True)
    if judge_deltas:
        print("judge deltas:")
        for _, d, pmid, ja, jb in judge_deltas[:max_titles]:
            print(f"  [{pmid}] {ja} -> {jb} ({fmt_delta(d)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--titles", type=int, default=10, help="max added/removed/rank-move rows per question")
    args = ap.parse_args()

    old = load_results(args.old)
    new = load_results(args.new)
    old_q, new_q = set(old), set(new)

    print(f"Comparing {args.old} -> {args.new}")
    print(f"questions: old={len(old_q)} new={len(new_q)} common={len(old_q & new_q)}")
    if new_q - old_q:
        print("new questions:", "; ".join(sorted(new_q - old_q)))
    if old_q - new_q:
        print("removed questions:", "; ".join(sorted(old_q - new_q)))

    for q in sorted(old_q & new_q):
        compare_question(q, old[q], new[q], args.titles)


if __name__ == "__main__":
    main()
