#!/usr/bin/env python3
"""Generate an overall summary from cited PubMed papers.

Inputs can be explicit PMIDs, a text file containing PMIDs, or an evaluation JSON
from scripts/evaluate_retrieval.py. For eval JSON, use --question to select one
row and summarize either its cited PMIDs from the generated answer or all retrieved
papers.

Examples:
  python scripts/summarize_citations.py --pmids 25806241 32592092 --topic "metformin and cancer risk"
  python scripts/summarize_citations.py --pmids-file citations.txt --out summary.md
  python scripts/summarize_citations.py --from-json baseline_with_answers_expanded_entityfix_v1.json \
    --question "p53 mutation and cancer prognosis" --use cited
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import summarize  # noqa: E402


def _pmids_from_file(path: Path):
    text = path.read_text()
    # Supports one PMID per line, comma-separated text, or [PMID] citations.
    return [int(x) for x in re.findall(r"\b\d{5,9}\b", text)]


def _select_eval_row(path: Path, question: Optional[str]):
    payload = json.loads(path.read_text())
    rows = payload.get("results", []) if isinstance(payload, dict) else payload
    if not rows:
        raise SystemExit(f"No results found in {path}")
    if question is None:
        if len(rows) > 1:
            raise SystemExit("--question is required when eval JSON has multiple rows")
        return rows[0]
    qnorm = question.strip().lower()
    for row in rows:
        if row.get("question", "").strip().lower() == qnorm:
            return row
    # Convenience: allow substring matching if unique.
    matches = [r for r in rows if qnorm in r.get("question", "").strip().lower()]
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(f"Could not uniquely match question: {question}")


def _pmids_from_eval(path: Path, question: Optional[str], use: str):
    row = _select_eval_row(path, question)
    if use == "cited":
        pmids = ((row.get("citation_status") or {}).get("cited_pmids")
                 or summarize.cited_pmids_from_text(row.get("answer") or ""))
    else:
        pmids = [p["pmid"] for p in row.get("papers", []) if p.get("pmid")]
    topic = row.get("question")
    return pmids, topic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pmids", nargs="*", type=int, default=[])
    ap.add_argument("--pmids-file", type=Path)
    ap.add_argument("--from-json", type=Path, help="eval/answer JSON file")
    ap.add_argument("--question", help="question to select from --from-json")
    ap.add_argument("--use", choices=("cited", "retrieved"), default="cited",
                    help="with --from-json, summarize cited PMIDs or all retrieved papers")
    ap.add_argument("--topic", help="optional synthesis goal; defaults to eval question when using --from-json")
    ap.add_argument("--no-fetch", action="store_true", help="do not fetch missing papers from PubMed")
    ap.add_argument("--require-abstract", action="store_true", help="efetch rows missing abstracts")
    ap.add_argument("--plain-text", action="store_true", help="disable markdown headings")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    pmids = list(args.pmids)
    topic = args.topic
    if args.pmids_file:
        pmids.extend(_pmids_from_file(args.pmids_file))
    if args.from_json:
        eval_pmids, eval_topic = _pmids_from_eval(args.from_json, args.question, args.use)
        pmids.extend(eval_pmids)
        topic = topic or eval_topic

    pmids = summarize.unique_pmids(pmids)
    if not pmids:
        raise SystemExit("No PMIDs selected")

    print(f"Summarizing {len(pmids)} PMIDs: {', '.join(map(str, pmids))}", file=sys.stderr)
    summary, papers = summarize.summarize_pmids(
        pmids,
        topic=topic,
        fetch_missing=not args.no_fetch,
        require_abstract=args.require_abstract,
        markdown=not args.plain_text,
    )
    print(f"Loaded {len(papers)} papers", file=sys.stderr)

    if args.out:
        args.out.write_text(summary + "\n")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(summary)


if __name__ == "__main__":
    main()
