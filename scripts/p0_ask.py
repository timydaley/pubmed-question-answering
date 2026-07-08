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
from pubmedqa import db, retrieve, generate, summarize, evidence_select  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--top", type=int, default=10, help="number of papers to show/use when not using evidence selection")
    ap.add_argument("--retrieve-pool", type=int, help="retrieve this many candidates before evidence selection for LLM answers")
    ap.add_argument("--evidence-context", type=int, default=8, help="number of selected evidence papers to pass to the LLM")
    ap.add_argument("--no-evidence-select", action="store_true", help="pass raw retrieved papers to the LLM instead of curated evidence")
    ap.add_argument("--show-selected", action="store_true", help="print selected evidence papers before answer generation")
    ap.add_argument("--no-llm", action="store_true", help="show retrieved papers only")
    ap.add_argument("--summary-only", action="store_true", help="hide retrieved-paper list and print only the summary")
    ap.add_argument("--per-paper-summaries", action="store_true", help="include a short note for each retrieved paper in the final summary")
    ap.add_argument("--plain-text", action="store_true", help="disable markdown headings in the summary")
    ap.add_argument("--show-groups", action="store_true", help="show balanced-context group labels in the retrieved-paper list")
    ap.add_argument("--second-pass-summary", action="store_true", help="after the normal answer, synthesize cited or retrieved papers in more detail")
    ap.add_argument("--summary-source", choices=("cited", "retrieved"), default="cited", help="PMIDs to use for --second-pass-summary")
    ap.add_argument("--map-reduce", action="store_true", help="use map-reduce summarization for the second-pass summary")
    ap.add_argument("--map-reduce-threshold", type=int, default=12, help="automatically use map-reduce at or above this paper count")
    ap.add_argument("--summary-notes-out", type=Path, help="write second-pass map-reduce per-paper evidence notes to JSON")
    ap.add_argument("--max-cited-summary-papers", type=int, help="limit --summary-source cited to the first N cited retrieved papers")
    args = ap.parse_args()
    question = " ".join(args.question)

    con = db.connect()
    retrieve_n = args.retrieve_pool or args.top
    t0 = time.time()
    retrieval_question = evidence_select.retrieval_query(question)
    papers = retrieve.search(con, retrieval_question, top_n=retrieve_n)
    dt = time.time() - t0
    if not papers:
        print("No results — did you build the index? (scripts/p0_build_index.py)")
        return

    if not args.summary_only:
        shown = papers[:args.top]
        if retrieval_question != question:
            print(f"\nretrieval_question: {retrieval_question}")
        print(f"\n=== Top {len(shown)} papers ({dt:.2f}s retrieval; pool={len(papers)}) ===")
        for p in shown:
            group = f" group={p.get('context_group')}" if args.show_groups else ""
            print(f"[{p['pmid']}] score={p['score']:.3f} rcr={p.get('rcr')} "
                  f"cites={p.get('citation_count')} ({p.get('year')}){group} "
                  f"{(p.get('title') or '')[:90]}")

    answer_text = ""
    answer_papers = papers[:args.top]
    if not args.no_llm:
        if not args.no_evidence_select:
            answer_papers = evidence_select.select_evidence(
                question,
                papers,
                max_papers=args.evidence_context,
            )
        if args.show_selected and not args.summary_only:
            print(f"\n=== Selected evidence ({len(answer_papers)} papers) ===")
            for p in answer_papers:
                sel = p.get("evidence_selection") or {}
                print(f"[{p['pmid']}] sel={sel.get('score')} tier={sel.get('evidence_tier')} "
                      f"centrality={sel.get('management_centrality_score')} "
                      f"tags={','.join(sel.get('intervention_tags') or [])} "
                      f"exposure={sel.get('exposure_score')} endpoint={sel.get('endpoint_score')} "
                      f"pop={sel.get('population_score')} "
                      f"{(p.get('title') or '')[:90]}")
        if not args.summary_only:
            print("\n=== Summary (local MLX, grounded) ===")
        t_answer = time.time()
        answer_text = generate.answer(
            question,
            answer_papers,
            per_paper=args.per_paper_summaries,
            markdown=not args.plain_text,
        )
        print(answer_text)
        if not args.summary_only:
            print(f"\n[answer-generation: {time.time() - t_answer:.2f}s]", file=sys.stderr)

    if not args.second_pass_summary:
        return

    if args.summary_source == "cited":
        if not answer_text:
            raise SystemExit("--summary-source cited requires normal answer generation; omit --no-llm or use --summary-source retrieved")
        selected = set(summarize.cited_pmids_from_text(answer_text))
        summary_papers = [p for p in answer_papers if int(p["pmid"]) in selected]
        if args.max_cited_summary_papers is not None:
            if args.max_cited_summary_papers <= 0:
                raise SystemExit("--max-cited-summary-papers must be positive")
            summary_papers = summary_papers[:args.max_cited_summary_papers]
        if not summary_papers:
            raise SystemExit("No cited retrieved PMIDs found for second-pass summary")
    else:
        summary_papers = answer_papers

    if not args.summary_only:
        pmids = ", ".join(str(p["pmid"]) for p in summary_papers)
        print(f"\n=== Second-pass evidence synthesis ({args.summary_source}; {len(summary_papers)} papers: {pmids}) ===")

    t_summary = time.time()
    summary_text = summarize.summarize_papers(
        summary_papers,
        topic=question,
        markdown=not args.plain_text,
        map_reduce=args.map_reduce,
        map_reduce_threshold=args.map_reduce_threshold,
        notes_out=args.summary_notes_out,
    )
    print(summary_text)
    if not args.summary_only:
        print(f"\n[second-pass-summary: {time.time() - t_summary:.2f}s]", file=sys.stderr)


if __name__ == "__main__":
    main()
