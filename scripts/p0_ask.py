#!/usr/bin/env python3
"""Phase 0: ask a question end-to-end.

Pipeline: MedCPT query embed -> BM25 + dense -> RRF -> citation re-score -> 8B LLM.

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
    args = ap.parse_args()
    question = " ".join(args.question)

    con = db.connect()
    t0 = time.time()
    papers = retrieve.search(con, question, top_n=args.top)
    dt = time.time() - t0
    if not papers:
        print("No results — did you build the index? (scripts/p0_build_index.py)")
        return

    print(f"\n=== Top {len(papers)} papers ({dt:.2f}s retrieval) ===")
    for p in papers:
        print(f"[{p['pmid']}] score={p['score']:.3f} rcr={p.get('rcr')} "
              f"cites={p.get('citation_count')} ({p.get('year')}) "
              f"{(p.get('title') or '')[:90]}")

    if args.no_llm:
        return
    print("\n=== Answer (8B, grounded) ===")
    print(generate.answer(question, papers))


if __name__ == "__main__":
    main()
