#!/usr/bin/env python3
"""Build a local snapshot from NCBI's precomputed MedCPT PubMed chunks.

This is the production-aligned ingest path for v1:
- download/load NCBI chunk files
- insert title/abstract metadata into SQLite
- insert aligned vectors into LanceDB
- optionally fetch iCite citations
- emit a build integrity report JSON

Expected chunk files per chunk id:
  - embeds_chunk_{i}.npy
  - pmids_chunk_{i}.json
  - pubmed_chunk_{i}.json

Usage:
  python scripts/build_snapshot_from_precomputed.py --list
  python scripts/build_snapshot_from_precomputed.py --chunks 0
  python scripts/build_snapshot_from_precomputed.py --chunks 0 1 2 --fetch-citations
  python scripts/build_snapshot_from_precomputed.py --chunks 0 --rows 50000 --build-index
"""
import argparse
import json
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import config, db, vectorstore, citations  # noqa: E402

NCBI_DIR = config.RAW_DIR / "ncbi_embeddings"
REPORT_PATH = config.DATA_ROOT / "build_report.json"


def list_dir():
    import re
    with urllib.request.urlopen(config.MEDCPT_EMBEDDINGS_BASE) as r:
        html = r.read().decode("utf-8", "ignore")
    names = sorted(set(re.findall(r"(?:embeds|pmids|pubmed)_chunk_\d+\.\w+", html)))
    print(f"{len(names)} files at {config.MEDCPT_EMBEDDINGS_BASE}")
    for n in names[:9]:
        print("  ", n)
    print("   ...")


def download_chunk(n: int):
    NCBI_DIR.mkdir(parents=True, exist_ok=True)
    for name in (f"embeds_chunk_{n}.npy", f"pmids_chunk_{n}.json", f"pubmed_chunk_{n}.json"):
        dest = NCBI_DIR / name
        if dest.exists():
            print(f"  have {name} ({dest.stat().st_size/1e6:.0f} MB)")
            continue
        url = config.MEDCPT_EMBEDDINGS_BASE + name
        print(f"  downloading {name} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"    -> {dest.stat().st_size/1e6:.0f} MB")


def reset_outputs():
    for p in (config.SQLITE_PATH, config.SQLITE_PATH.with_suffix(".sqlite-wal"),
              config.SQLITE_PATH.with_suffix(".sqlite-shm"), REPORT_PATH):
        if p.exists():
            p.unlink()
    if config.LANCE_DIR.exists():
        shutil.rmtree(config.LANCE_DIR)


def _text_record(raw, pmid):
    if isinstance(raw, dict):
        title = raw.get("t") or raw.get("title") or ""
        abstract = raw.get("a") or raw.get("abstract") or ""
        journal = raw.get("j") or raw.get("journal") or ""
        year = raw.get("y") or raw.get("year")
        pubtypes = raw.get("pt") or raw.get("pubtypes") or raw.get("p") or ""
        mesh = raw.get("m") or raw.get("mesh") or ""
        retracted = raw.get("retracted") or 0
    else:
        title = abstract = journal = pubtypes = mesh = ""
        year = None
        retracted = 0
    try:
        year = int(year) if year is not None and str(year).isdigit() else None
    except Exception:
        year = None
    return {
        "pmid": int(pmid),
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "year": year,
        "mesh": mesh if isinstance(mesh, str) else "; ".join(mesh),
        "pubtypes": pubtypes if isinstance(pubtypes, str) else "; ".join(pubtypes),
        "retracted": int(bool(retracted)),
    }


def _load_text_map(path: Path):
    data = json.load(open(path))
    if isinstance(data, dict):
        return {int(k): _text_record(v, k) for k, v in data.items()}
    if isinstance(data, list):
        out = {}
        for row in data:
            if not isinstance(row, dict):
                continue
            pmid = row.get("pmid") or row.get("id") or row.get("d")
            if pmid is None:
                continue
            out[int(pmid)] = _text_record(row, pmid)
        return out
    raise ValueError(f"Unsupported JSON structure in {path}")


def load_chunk(n: int, rows: int | None = None):
    embeds = np.load(NCBI_DIR / f"embeds_chunk_{n}.npy", mmap_mode="r")
    pmids = [int(p) for p in json.load(open(NCBI_DIR / f"pmids_chunk_{n}.json"))]
    text_map = _load_text_map(NCBI_DIR / f"pubmed_chunk_{n}.json")

    total = min(len(pmids), embeds.shape[0])
    if rows is not None:
        total = min(total, rows)
    pmids = pmids[:total]
    vecs = np.array(embeds[:total], dtype=np.float32)
    records = [text_map.get(p, {"pmid": p, "title": "", "abstract": "", "journal": "",
                                "year": None, "mesh": "", "pubtypes": "", "retracted": 0})
               for p in pmids]
    return pmids, vecs, records, len(text_map), embeds.shape[0]


def build_report_template(args):
    return {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source": "ncbi_precomputed_medcpt",
        "chunks": args.chunks,
        "rows_per_chunk_limit": args.rows,
        "medcpt_revision": config.MEDCPT_REVISION,
        "sqlite_path": str(config.SQLITE_PATH),
        "lancedb_path": str(config.LANCE_DIR),
        "fetch_citations": bool(args.fetch_citations),
        "build_index": bool(args.build_index),
        "stats": {
            "docs_inserted": 0,
            "vectors_inserted": 0,
            "pmids_seen": 0,
            "pmid_vector_rows": 0,
            "records_with_text": 0,
            "records_missing_text": 0,
            "records_missing_abstract": 0,
            "citations_loaded": 0,
            "citation_rows_missing": None,
        },
        "chunk_reports": [],
    }


def write_report(report):
    config.ensure_dirs()
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"wrote build report -> {REPORT_PATH}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--chunks", type=int, nargs="+", help="chunk ids to ingest, e.g. 0 1 2")
    ap.add_argument("--rows", type=int, default=None, help="optional max rows per chunk")
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="delete existing SQLite/LanceDB first")
    ap.add_argument("--fetch-citations", action="store_true", help="fetch iCite API citations after ingest")
    ap.add_argument("--build-index", action="store_true", help="build LanceDB IVF-PQ index after ingest")
    ap.add_argument("--num-partitions", type=int, default=256)
    ap.add_argument("--num-sub-vectors", type=int, default=96)
    args = ap.parse_args()

    if args.list:
        list_dir()
        return
    if not args.chunks:
        ap.error("--chunks is required unless using --list")

    config.ensure_dirs()
    if args.overwrite:
        print("resetting prior outputs ...")
        reset_outputs()

    con = db.connect()
    db.init_db(con)

    report = build_report_template(args)
    first = not config.LANCE_DIR.exists()

    for chunk in args.chunks:
        print(f"\n=== chunk {chunk} ===")
        if not args.skip_download:
            download_chunk(chunk)

        pmids, vecs, records, text_rows, vector_rows = load_chunk(chunk, rows=args.rows)
        have_text = sum(1 for r in records if r.get("title") or r.get("abstract"))
        missing_abstract = sum(1 for r in records if not r.get("abstract"))
        missing_text = len(records) - have_text

        db.insert_papers(con, records)
        if first:
            vectorstore.create(pmids, vecs, overwrite=True)
            first = False
        else:
            vectorstore.add(pmids, vecs)

        report["stats"]["docs_inserted"] += len(records)
        report["stats"]["vectors_inserted"] += len(pmids)
        report["stats"]["pmids_seen"] += len(pmids)
        report["stats"]["pmid_vector_rows"] += vector_rows
        report["stats"]["records_with_text"] += have_text
        report["stats"]["records_missing_text"] += missing_text
        report["stats"]["records_missing_abstract"] += missing_abstract
        report["chunk_reports"].append({
            "chunk": chunk,
            "rows_ingested": len(pmids),
            "vector_rows_in_chunk": vector_rows,
            "text_rows_in_chunk": text_rows,
            "records_with_text": have_text,
            "records_missing_text": missing_text,
            "records_missing_abstract": missing_abstract,
        })
        print(f"  inserted {len(records)} papers / {len(pmids)} vectors")
        print(f"  text rows={have_text}, missing text={missing_text}, missing abstract={missing_abstract}")

    print("\nrebuilding FTS5 index ...")
    db.rebuild_fts(con)

    if args.fetch_citations:
        print("fetching iCite citations ...")
        pmids = [row[0] for row in con.execute("SELECT pmid FROM papers").fetchall()]
        loaded = citations.ingest(con, pmids)
        report["stats"]["citations_loaded"] = loaded
        report["stats"]["citation_rows_missing"] = max(0, len(pmids) - loaded)
        print(f"  loaded {loaded} citation rows")

    if args.build_index:
        print("building LanceDB IVF-PQ index ...")
        vectorstore.build_index(num_partitions=args.num_partitions,
                                num_sub_vectors=args.num_sub_vectors)
        report["index"] = {
            "type": "ivf_pq",
            "num_partitions": args.num_partitions,
            "num_sub_vectors": args.num_sub_vectors,
        }

    docs = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    vec_docs = report["stats"]["vectors_inserted"]
    report["stats"]["sqlite_paper_rows"] = docs
    report["stats"]["pmid_match_rate"] = round(vec_docs / docs, 6) if docs else 0.0

    write_report(report)
    print("\nDONE")
    print(f"  papers:   {docs}")
    print(f"  vectors:  {vec_docs}")
    print(f"  report:   {REPORT_PATH}")
    print(f"  sqlite:   {config.SQLITE_PATH}")
    print(f"  lancedb:  {config.LANCE_DIR}")


if __name__ == "__main__":
    main()
