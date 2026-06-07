#!/usr/bin/env python3
"""Phase 0: build a small index from one PubMed baseline file.

Embeds locally with MedCPT (fine for tens of thousands of abstracts) to prove the
full pipeline end-to-end. At scale this step is replaced by downloaded precomputed
vectors (plan §3) — the rest of the system is identical.

    python scripts/p0_build_index.py <file.xml.gz> [--limit 30000] [--batch 256]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import config, parse_pubmed, db, embed, vectorstore, citations  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xml_gz")
    ap.add_argument("--limit", type=int, default=30000)
    ap.add_argument("--batch", type=int, default=256)
    args = ap.parse_args()

    con = db.connect()
    db.init_db(con)

    state = {"total": 0, "t0": time.time(), "first": True}

    def flush(records):
        records = [r for r in records if r["abstract"]]
        if not records:
            return
        db.insert_papers(con, records)
        vecs = embed.embed_articles(records)
        pmids = [r["pmid"] for r in records]
        if state["first"]:
            vectorstore.create(pmids, vecs, overwrite=True)
            state["first"] = False
        else:
            vectorstore.add(pmids, vecs)
        state["total"] += len(records)
        rate = state["total"] / max(1e-6, time.time() - state["t0"])
        print(f"  indexed {state['total']}  ({rate:.0f} docs/s)")

    buf = []
    for rec in parse_pubmed.iter_articles(args.xml_gz):
        buf.append(rec)
        if len(buf) >= args.batch:
            flush(buf)
            buf = []
        if state["total"] >= args.limit:
            break
    if buf and state["total"] < args.limit:
        flush(buf)

    print("rebuilding FTS5 (BM25) index ...")
    db.rebuild_fts(con)

    print("fetching iCite citation_count + RCR ...")
    pmids = [row[0] for row in con.execute("SELECT pmid FROM papers").fetchall()]
    n = citations.ingest(con, pmids)

    print(f"\nDONE: {state['total']} papers indexed, {n} citation rows.")
    print(f"Data at {config.DATA_ROOT}")
    print('Try:  python scripts/p0_ask.py "does metformin reduce cancer risk?"')


if __name__ == "__main__":
    main()
