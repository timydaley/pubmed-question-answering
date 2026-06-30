#!/usr/bin/env python3
"""Enrich SQLite paper metadata from PubMed E-utilities efetch.

Useful when the local snapshot was built from NCBI MedCPT precomputed chunks,
which provide PMID/title/abstract/MeSH/date but often omit journal and
publication types. This script fetches authoritative PubMed XML for selected
PMIDs and updates the `papers` table in place, then rebuilds FTS.

Examples:
  python scripts/enrich_metadata.py --from-json baseline_retrieval_v4.json
  python scripts/enrich_metadata.py --missing --limit 1000
  python scripts/enrich_metadata.py --pmids 30791074 28615298
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import config, db, parse_pubmed  # noqa: E402


def pmids_from_json(path: Path):
    data = json.load(open(path))
    out = []

    def visit(x):
        if isinstance(x, dict):
            if "pmid" in x:
                try:
                    out.append(int(x["pmid"]))
                except Exception:
                    pass
            for v in x.values():
                visit(v)
        elif isinstance(x, list):
            for v in x:
                visit(v)

    visit(data)
    return out


def unique_pmids(pmids):
    seen = set()
    out = []
    for pmid in pmids:
        try:
            pmid = int(pmid)
        except Exception:
            continue
        if pmid not in seen:
            seen.add(pmid)
            out.append(pmid)
    return out


def fetch_batch(pmids, email=None, api_key=None):
    params = {
        "db": "pubmed",
        "retmode": "xml",
        "id": ",".join(str(p) for p in pmids),
    }
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key
    url = config.EFETCH_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def update_records(con, records, overwrite_text=False):
    if overwrite_text:
        return db.insert_papers(con, records)

    rows = []
    for r in records:
        rows.append((
            r["journal"],
            r["year"],
            r["mesh"],
            r["pubtypes"],
            r["retracted"],
            r["title"],
            r["abstract"],
            r["pmid"],
        ))
    cur = con.executemany(
        """
        UPDATE papers
        SET journal = COALESCE(NULLIF(?, ''), journal),
            year = COALESCE(?, year),
            mesh = COALESCE(NULLIF(?, ''), mesh),
            pubtypes = COALESCE(NULLIF(?, ''), pubtypes),
            retracted = ?,
            title = CASE WHEN title IS NULL OR title = '' THEN ? ELSE title END,
            abstract = CASE WHEN abstract IS NULL OR abstract = '' THEN ? ELSE abstract END
        WHERE pmid = ?
        """,
        rows,
    )
    con.commit()
    return max(cur.rowcount, 0)


def missing_pmids(con, limit=None):
    sql = """
        SELECT pmid FROM papers
        WHERE journal IS NULL OR journal = ''
           OR pubtypes IS NULL OR pubtypes = ''
           OR year IS NULL
        ORDER BY pmid
    """
    if limit:
        sql += " LIMIT ?"
        return [r[0] for r in con.execute(sql, (limit,)).fetchall()]
    return [r[0] for r in con.execute(sql).fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pmids", nargs="*", type=int, default=[])
    ap.add_argument("--pmids-file", type=Path, help="one PMID per line")
    ap.add_argument("--from-json", type=Path, action="append", default=[],
                    help="baseline/eval JSON to scan recursively for pmid fields")
    ap.add_argument("--missing", action="store_true",
                    help="fetch papers missing journal, pubtypes, or year in SQLite")
    ap.add_argument("--limit", type=int, help="cap selected PMIDs")
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--sleep", type=float, default=0.34,
                    help="delay between efetch batches (NCBI-friendly default)")
    ap.add_argument("--email", default=None, help="optional email for NCBI requests")
    ap.add_argument("--api-key", default=None, help="optional NCBI API key")
    ap.add_argument("--overwrite-text", action="store_true",
                    help="replace title/abstract too; default only fills missing text")
    ap.add_argument("--rebuild-fts", action="store_true",
                    help="rebuild FTS5 after enrichment (slow on large snapshots; not needed for journal/pubtypes/year-only updates)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    con = db.connect()
    db.init_db(con)

    pmids = list(args.pmids)
    if args.pmids_file:
        pmids.extend(line.strip() for line in open(args.pmids_file) if line.strip())
    for path in args.from_json:
        pmids.extend(pmids_from_json(path))
    if args.missing:
        pmids.extend(missing_pmids(con, args.limit))

    pmids = unique_pmids(pmids)
    if args.limit:
        pmids = pmids[:args.limit]
    if not pmids:
        ap.error("No PMIDs selected. Use --pmids, --pmids-file, --from-json, or --missing.")

    print(f"selected {len(pmids)} unique PMIDs")
    if args.dry_run:
        print("first PMIDs:", ", ".join(str(p) for p in pmids[:20]))
        return

    fetched = parsed = updated = 0
    for i in range(0, len(pmids), args.batch_size):
        batch = pmids[i:i + args.batch_size]
        print(f"fetching {i + 1}-{i + len(batch)} / {len(pmids)} ...")
        xml = fetch_batch(batch, email=args.email, api_key=args.api_key)
        records = parse_pubmed.parse_efetch_xml(xml)
        fetched += len(batch)
        parsed += len(records)
        updated += update_records(con, records, overwrite_text=args.overwrite_text)
        if i + args.batch_size < len(pmids):
            time.sleep(args.sleep)

    if args.rebuild_fts:
        print("rebuilding FTS5 index ...")
        db.rebuild_fts(con)
    print(f"DONE fetched={fetched} parsed={parsed} sqlite_changes={updated}")


if __name__ == "__main__":
    main()
