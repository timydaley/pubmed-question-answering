#!/usr/bin/env python3
"""Run a small, repeatable retrieval/answer baseline.

Default mode is retrieval-only and writes JSON that can be compared after tuning
ranking thresholds. Add --with-llm to also generate grounded answers and check
whether the answer cites only retrieved PMIDs.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import db, evidence_select, generate, retrieve  # noqa: E402

DEFAULT_QUESTIONS = [
    "does metformin reduce cancer risk?",
    "statins and risk of dementia",
    "vitamin D supplementation and respiratory infections",
    "aspirin for primary prevention cardiovascular disease",
    "GLP-1 agonists and cardiovascular outcomes",
]


def _load_questions(path):
    if not path:
        return DEFAULT_QUESTIONS
    text = Path(path).read_text().strip()
    if not text:
        return []
    if path.endswith(".json"):
        data = json.loads(text)
        if isinstance(data, list):
            return [str(x["question"] if isinstance(x, dict) else x) for x in data]
        if isinstance(data, dict):
            return [str(x) for x in data.get("questions", [])]
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _citation_status(answer, pmids):
    cited = generate.cited_pmids(answer or "")
    return {
        "cited_pmids": sorted(cited),
        "invalid_cited_pmids": sorted(cited - set(pmids)),
        "citation_validation_warning": "[citation-validation] WARNING" in (answer or ""),
    }


def _paper_summary(p):
    row = {
        "pmid": p.get("pmid"),
        "title": p.get("title"),
        "year": p.get("year"),
        "journal": p.get("journal"),
        "score": p.get("score"),
        "relevance": p.get("relevance"),
        "overlap": p.get("overlap"),
        "focus_overlap": p.get("focus_overlap"),
        "pub_boost": p.get("pub_boost"),
        "citation_count": p.get("citation_count"),
        "rcr": p.get("rcr"),
        "pubtypes": p.get("pubtypes"),
        "context_group": p.get("context_group"),
    }
    if p.get("evidence_selection"):
        row["evidence_selection"] = p.get("evidence_selection")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", help="newline text or JSON file; defaults to starter benchmark questions")
    ap.add_argument("--top", type=int, default=10, help="number of retrieved papers to record in the benchmark")
    ap.add_argument("--retrieve-pool", type=int, help="retrieve this many candidates before evidence selection for LLM answers")
    ap.add_argument("--evidence-context", type=int, default=8, help="number of selected evidence papers to pass to the LLM")
    ap.add_argument("--no-evidence-select", action="store_true", help="pass raw top papers to the LLM instead of curated evidence")
    ap.add_argument("--with-llm", action="store_true", help="also generate answers and validate cited PMIDs")
    ap.add_argument("--out", default="retrieval_eval.json", help="JSON output path")
    ap.add_argument("--print-titles", action="store_true", help="print retrieved titles for spot checks")
    args = ap.parse_args()

    questions = _load_questions(args.questions)
    if not questions:
        raise SystemExit("No questions provided")

    con = db.connect()
    results = []
    for i, question in enumerate(questions, 1):
        retrieve_n = args.retrieve_pool or args.top
        t0 = time.perf_counter()
        papers = retrieve.search(con, question, top_n=retrieve_n)
        retrieval_s = time.perf_counter() - t0
        recorded_papers = papers[:args.top]

        answer = None
        generation_s = None
        citation_status = None
        selected_papers = None
        if args.with_llm and papers:
            if args.no_evidence_select:
                answer_papers = recorded_papers
            else:
                answer_papers = evidence_select.select_evidence(
                    question,
                    papers,
                    max_papers=args.evidence_context,
                )
                selected_papers = answer_papers
            g0 = time.perf_counter()
            answer = generate.answer(question, answer_papers)
            generation_s = time.perf_counter() - g0
            citation_status = _citation_status(answer, [p["pmid"] for p in answer_papers])

        group_counts = {}
        for p in recorded_papers:
            group = p.get("context_group", "unknown")
            group_counts[group] = group_counts.get(group, 0) + 1

        row = {
            "question": question,
            "top_n": args.top,
            "retrieve_pool": retrieve_n,
            "evidence_context": None if args.no_evidence_select or not args.with_llm else args.evidence_context,
            "retrieval_seconds": round(retrieval_s, 3),
            "generation_seconds": round(generation_s, 3) if generation_s is not None else None,
            "num_results": len(recorded_papers),
            "num_retrieved_pool": len(papers),
            "num_selected_evidence": len(selected_papers or []) if args.with_llm and not args.no_evidence_select else None,
            "unique_journals": len({p.get("journal") for p in recorded_papers if p.get("journal")}),
            "year_range": [min((p.get("year") for p in recorded_papers if p.get("year")), default=None),
                           max((p.get("year") for p in recorded_papers if p.get("year")), default=None)],
            "context_group_counts": group_counts,
            "citation_status": citation_status,
            "papers": [_paper_summary(p) for p in recorded_papers],
            "selected_evidence_papers": [_paper_summary(p) for p in (selected_papers or [])],
            "answer": answer,
            "manual_review": {
                "retrieval_relevance_1_to_5": None,
                "output_diversity_1_to_5": None,
                "notes": "",
            },
        }
        results.append(row)

        print(f"[{i}/{len(questions)}] {question} — {len(recorded_papers)} results (pool {len(papers)}), retrieval {retrieval_s:.2f}s, groups={group_counts}")
        if args.print_titles:
            for p in recorded_papers:
                print(f"  [{p['pmid']}] {p.get('context_group')} {p.get('year')} {p.get('title')}")

    payload = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results}
    Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
