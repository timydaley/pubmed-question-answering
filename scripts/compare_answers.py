#!/usr/bin/env python3
"""Compare two answer benchmark JSON artifacts.

Reports aggregate latency/citation changes plus per-question answer/citation deltas.
This complements scripts/compare_eval.py, which focuses on retrieval/ranking changes.

Usage:
  python scripts/compare_answers.py old_answers.json new_answers.json
  python scripts/compare_answers.py old_answers.json new_answers.json --show-excerpts --excerpt-chars 500
"""
import argparse
import json
import re
from pathlib import Path


CITATION_RE = re.compile(r"\[([^\]]+)\]")
PMID_RE = re.compile(r"\b\d{5,9}\b")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$|^([A-Za-z][A-Za-z /-]+):\s*$", re.MULTILINE)


CAUSAL_TERMS = (
    " proves ",
    " proven ",
    " causes ",
    " caused ",
    " prevents ",
    " prevented ",
    " cures ",
    " cured ",
)


QUALIFYING_TERMS = (
    "associated",
    "association",
    "observational",
    "confounding",
    "confounded",
    "randomized",
    "trial",
    "mechanistic",
    "cell-line",
    "animal",
)


def load_results(path: Path):
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "results" in data:
        rows = data["results"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError(f"Unsupported answer JSON format: {path}")
    return {r["question"]: r for r in rows}


def cited_pmids(text: str):
    out = set()
    for bracket in CITATION_RE.findall(text or ""):
        for match in PMID_RE.findall(bracket):
            out.add(int(match))
    return out


def pmids_anywhere(text: str):
    return {int(match) for match in PMID_RE.findall(text or "")}


def unbracketed_pmids(text: str):
    text = text or ""
    outside = []
    pos = 0
    for match in re.finditer(r"\[[^\]]*\]", text):
        outside.append(text[pos:match.start()])
        pos = match.end()
    outside.append(text[pos:])
    return pmids_anywhere("\n".join(outside))


def artifact_cited_pmids(row):
    status = row.get("citation_status") or {}
    return {int(p) for p in status.get("cited_pmids") or []}


def retrieved_pmids(row):
    """PMIDs valid for answer citations.

    Older artifacts cite from row['papers']. Evidence-selection artifacts generate
    from row['selected_evidence_papers'], which can include candidates outside the
    recorded top-10 retrieval list. Treat both as valid context.
    """
    out = {int(p["pmid"]) for p in row.get("papers", []) if p.get("pmid") is not None}
    out.update(int(p["pmid"]) for p in row.get("selected_evidence_papers", []) if p.get("pmid") is not None)
    return out


def invalid_pmids(row):
    return cited_pmids(row.get("answer") or "") - retrieved_pmids(row)


def invalid_pmids_anywhere(row):
    return pmids_anywhere(row.get("answer") or "") - retrieved_pmids(row)


def heading_names(answer: str):
    names = []
    for match in HEADING_RE.finditer(answer or ""):
        name = (match.group(1) or match.group(2) or "").strip().lower()
        name = re.sub(r"\s+", " ", name)
        names.append(name)
    return names


def has_evidence_basis(row):
    return "evidence basis" in heading_names(row.get("answer") or "")


def section(answer: str, heading: str):
    """Return markdown-ish section text for a heading, if present."""
    answer = answer or ""
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(answer)
    if not match:
        return ""
    next_heading = re.search(r"^##\s+", answer[match.end():], flags=re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(answer)
    return answer[match.end():end].strip()


def answer_flags(row):
    answer = " " + (row.get("answer") or "").lower().replace("\n", " ") + " "
    short = section(row.get("answer") or "", "Short answer").lower()
    flags = []
    if short.startswith("yes") and "observ" in answer:
        flags.append("short-answer starts with yes despite observational language")
    for term in CAUSAL_TERMS:
        if term in answer:
            flags.append(f"causal term:{term.strip()}")
    if not any(term in answer for term in QUALIFYING_TERMS):
        flags.append("no obvious evidence qualifier")
    if not has_evidence_basis(row):
        flags.append("missing Evidence basis section")
    return flags


def avg(rows, key):
    vals = [float(r[key]) for r in rows if isinstance(r.get(key), (int, float))]
    return sum(vals) / len(vals) if vals else None


def fmt(value, digits=2):
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_delta(value, unit=""):
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}{unit}"


def citation_mismatch_count(rows):
    n = 0
    for row in rows:
        if cited_pmids(row.get("answer") or "") != artifact_cited_pmids(row):
            n += 1
    return n


def warning_count(rows):
    count = 0
    for row in rows:
        status = row.get("citation_status") or {}
        if status.get("citation_validation_warning") or status.get("citation_format_warning"):
            count += 1
    return count


def invalid_count(rows):
    return sum(1 for row in rows if invalid_pmids(row))


def print_aggregate(old_path, new_path, old_rows, new_rows):
    old_list = list(old_rows.values())
    new_list = list(new_rows.values())
    print(f"Comparing {old_path} -> {new_path}")
    print(f"questions: old={len(old_rows)} new={len(new_rows)} common={len(set(old_rows) & set(new_rows))}")
    print()
    print("## Aggregate")
    print("| Metric | Old | New | Delta |")
    print("|---|---:|---:|---:|")
    metrics = [
        ("Avg retrieval latency (s)", avg(old_list, "retrieval_seconds"), avg(new_list, "retrieval_seconds")),
        ("Avg generation latency (s)", avg(old_list, "generation_seconds"), avg(new_list, "generation_seconds")),
        ("Citation warning rows", warning_count(old_list), warning_count(new_list)),
        ("Invalid cited-PMID rows", invalid_count(old_list), invalid_count(new_list)),
        ("Invalid PMID-anywhere rows", sum(1 for r in old_list if invalid_pmids_anywhere(r)), sum(1 for r in new_list if invalid_pmids_anywhere(r))),
        ("Unbracketed PMID rows", sum(1 for r in old_list if unbracketed_pmids(r.get("answer") or "")), sum(1 for r in new_list if unbracketed_pmids(r.get("answer") or ""))),
        ("Citation normalization note rows", sum(bool((r.get("citation_status") or {}).get("citation_normalization_note")) for r in old_list), sum(bool((r.get("citation_status") or {}).get("citation_normalization_note")) for r in new_list)),
        ("Manual citation extraction mismatches", citation_mismatch_count(old_list), citation_mismatch_count(new_list)),
        ("Rows with Evidence basis", sum(has_evidence_basis(r) for r in old_list), sum(has_evidence_basis(r) for r in new_list)),
        ("Rows with review flags", sum(bool(answer_flags(r)) for r in old_list), sum(bool(answer_flags(r)) for r in new_list)),
    ]
    for name, old, new in metrics:
        delta = None if old is None or new is None else new - old
        print(f"| {name} | {fmt(old) if isinstance(old, float) else old} | {fmt(new) if isinstance(new, float) else new} | {fmt_delta(delta)} |")


def excerpt(text, chars):
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= chars:
        return text
    return text[:chars].rstrip() + "…"


def compare_question(question, old, new, show_excerpts=False, excerpt_chars=400):
    old_cited = cited_pmids(old.get("answer") or "")
    new_cited = cited_pmids(new.get("answer") or "")
    common = old_cited & new_cited
    added = sorted(new_cited - old_cited)
    removed = sorted(old_cited - new_cited)
    union = old_cited | new_cited

    old_invalid = sorted(invalid_pmids(old))
    new_invalid = sorted(invalid_pmids(new))
    old_flags = answer_flags(old)
    new_flags = answer_flags(new)

    print(f"\n## {question}")
    old_gen = old.get("generation_seconds")
    new_gen = new.get("generation_seconds")
    delta_gen = None if old_gen is None or new_gen is None else new_gen - old_gen
    print(f"generation: {old_gen}s -> {new_gen}s ({fmt_delta(delta_gen, 's')})")
    print(f"answer chars: {len(old.get('answer') or '')} -> {len(new.get('answer') or '')} ({fmt_delta(len(new.get('answer') or '') - len(old.get('answer') or ''))})")
    print(f"Evidence basis: {has_evidence_basis(old)} -> {has_evidence_basis(new)}")
    print(f"cited PMIDs: {len(old_cited)} -> {len(new_cited)}; overlap {len(common)}/{max(len(union), 1)} union")
    if added:
        print("added citations:", ", ".join(str(p) for p in added))
    if removed:
        print("removed citations:", ", ".join(str(p) for p in removed))
    if old_invalid or new_invalid:
        print(f"invalid cited PMIDs: {old_invalid} -> {new_invalid}")

    old_mismatch = old_cited != artifact_cited_pmids(old)
    new_mismatch = new_cited != artifact_cited_pmids(new)
    if old_mismatch or new_mismatch:
        print(f"citation-status mismatch: {old_mismatch} -> {new_mismatch}")

    if old_flags or new_flags:
        print(f"review flags: {old_flags or 'none'} -> {new_flags or 'none'}")

    if show_excerpts:
        print("old short answer:", excerpt(section(old.get("answer") or "", "Short answer") or old.get("answer") or "", excerpt_chars))
        print("new short answer:", excerpt(section(new.get("answer") or "", "Short answer") or new.get("answer") or "", excerpt_chars))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--show-excerpts", action="store_true", help="include old/new short-answer excerpts")
    ap.add_argument("--excerpt-chars", type=int, default=400)
    args = ap.parse_args()

    old = load_results(args.old)
    new = load_results(args.new)
    old_q, new_q = set(old), set(new)

    print_aggregate(args.old, args.new, old, new)
    if new_q - old_q:
        print("\nnew questions:", "; ".join(sorted(new_q - old_q)))
    if old_q - new_q:
        print("\nremoved questions:", "; ".join(sorted(old_q - new_q)))

    for question in sorted(old_q & new_q):
        compare_question(question, old[question], new[question], args.show_excerpts, args.excerpt_chars)


if __name__ == "__main__":
    main()
