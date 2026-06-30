#!/usr/bin/env python3
"""Report citation+recency quality signals for benchmark/eval JSON artifacts.

This is a benchmark-audit helper, not a relevance judge. Citation and recency are
secondary signals: a low-cited paper can still be good if it is recent, niche, or
directly answers the endpoint.
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import db, citations  # noqa: E402
from pubmedqa.retrieve import _impact_norm, _recency_norm, _citation_rate_norm  # noqa: E402


def _rows(payload):
    return payload.get("results", []) if isinstance(payload, dict) else payload


def _pmids(rows):
    out = []
    for row in rows:
        for p in row.get("papers", []):
            if p.get("pmid"):
                out.append(int(p["pmid"]))
    return list(dict.fromkeys(out))


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def _fmt(x, digits=2):
    if x is None:
        return "n/a"
    if isinstance(x, int):
        return str(x)
    return f"{x:.{digits}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact", type=Path)
    ap.add_argument("--fetch-citations", action="store_true", help="fetch missing iCite rows for artifact PMIDs")
    ap.add_argument("--low-citation", type=int, default=10)
    ap.add_argument("--low-score", type=float, default=0.35, help="flag papers below this citation+recency score")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    payload = json.loads(args.artifact.read_text())
    rows = _rows(payload)
    pmids = _pmids(rows)
    con = db.connect()
    db.init_db(con)

    if args.fetch_citations:
        existing = db.fetch_citations(con, pmids)
        missing = [p for p in pmids if p not in existing]
        if missing:
            loaded = citations.ingest(con, missing)
            print(f"fetched {loaded} missing citation rows", file=sys.stderr)

    cit_by = db.fetch_citations(con, pmids)

    lines = []
    lines.append(f"# Citation + Recency Benchmark Report\n\n")
    lines.append(f"Artifact: `{args.artifact}`  \n")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
    lines.append("## Scoring\n\n")
    lines.append("`impact_score` is the same bounded citation+recency signal used by retrieval: RCR/log citations + citation velocity + recency. It is a secondary quality signal, not a relevance score.\n\n")
    lines.append("## Per-question summary\n\n")
    lines.append("| Question | Median cites | Median impact_score | Low-cite PMIDs | Low-score PMIDs | Best impact PMID |\n")
    lines.append("|---|---:|---:|---:|---:|---|\n")

    detail = []
    all_scores = []
    for row in rows:
        papers = row.get("papers", [])
        scored = []
        for p in papers:
            pmid = int(p["pmid"])
            cit = cit_by.get(pmid, {})
            score = _impact_norm(cit, p)
            scored.append((pmid, p, cit, score))
            all_scores.append(score)
        cites = [x[2].get("citation_count") for x in scored if x[2].get("citation_count") is not None]
        low_cite = [x for x in scored if (x[2].get("citation_count") or 0) < args.low_citation]
        low_score = [x for x in scored if x[3] < args.low_score]
        best = max(scored, key=lambda x: x[3]) if scored else None
        lines.append(
            f"| {row.get('question')} | {_fmt(_median(cites), 1)} | {_fmt(_median([x[3] for x in scored]), 2)} | "
            f"{len(low_cite)} | {len(low_score)} | "
            f"{best[0] if best else 'n/a'} ({_fmt(best[3], 2) if best else 'n/a'}) |\n"
        )
        detail.append((row, scored, low_cite, low_score))

    lines.append("\n## Low citation/recency-score review targets\n\n")
    for row, scored, low_cite, low_score in detail:
        flagged = {x[0]: x for x in low_cite + low_score}
        if not flagged:
            continue
        lines.append(f"### {row.get('question')}\n\n")
        for pmid, p, cit, score in sorted(flagged.values(), key=lambda x: x[3]):
            lines.append(
                f"- `{pmid}` impact_score={score:.2f} cites={cit.get('citation_count')} "
                f"rcr={cit.get('rcr')} recency={_recency_norm(p):.2f} "
                f"cite_rate={_citation_rate_norm(cit, p):.2f} year={p.get('year')} — {p.get('title')}\n"
            )
        lines.append("\n")

    if all_scores:
        lines.append("## Overall\n\n")
        lines.append(f"- PMIDs scored: {len(all_scores)}\n")
        lines.append(f"- Median impact_score: {_median(all_scores):.2f}\n")
        lines.append(f"- Low impact_score (<{args.low_score}): {sum(s < args.low_score for s in all_scores)} / {len(all_scores)}\n")

    text = "".join(lines)
    if args.out:
        args.out.write_text(text)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
