#!/usr/bin/env python3
"""Phase 0: ask a question end-to-end.

Pipeline: MedCPT query embed -> BM25 + dense -> RRF -> citation re-score -> local MLX LLM.

    python scripts/p0_ask.py "does metformin reduce cancer risk?"
    python scripts/p0_ask.py --no-llm "statins and dementia"     # retrieval only
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import db, retrieve, generate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--no-llm", action="store_true", help="show retrieved papers only")
    ap.add_argument("--summary-only", action="store_true", help="hide retrieved-paper list and print only the summary")
    ap.add_argument("--per-paper-summaries", action="store_true", help="include a short note for each retrieved paper in the final summary")
    ap.add_argument("--plain-text", action="store_true", help="disable markdown headings in the summary")
    ap.add_argument("--show-groups", action="store_true", help="show balanced-context group labels in the retrieved-paper list")
    args = ap.parse_args()
    question = " ".join(args.question)

    con = db.connect()
    t0 = time.time()
    papers = retrieve.search(con, question, top_n=args.top)
    dt = time.time() - t0
    if not papers:
        print("No results — did you build the index? (scripts/p0_build_index.py)")
        return

    if not args.summary_only:
        print(f"\n=== Top {len(papers)} papers ({dt:.2f}s retrieval) ===")
        for p in papers:
            group = f" group={p.get('context_group')}" if args.show_groups else ""
            print(f"[{p['pmid']}] score={p['score']:.3f} rcr={p.get('rcr')} "
                  f"cites={p.get('citation_count')} ({p.get('year')}){group} "
                  f"{(p.get('title') or '')[:90]}")

    if args.no_llm:
        return
    if not args.summary_only:
        print("\n=== Summary (local MLX, grounded) ===")
    print(generate.answer(
        question,
        papers,
        per_paper=args.per_paper_summaries,
        markdown=not args.plain_text,
    ))


if __name__ == "__main__":
    main()
