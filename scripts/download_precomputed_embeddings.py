#!/usr/bin/env python3
"""Download multiple NCBI precomputed MedCPT PubMed embedding chunks.

By default this downloads the vector file and aligned PMID file for each chunk:
  - embeds_chunk_{i}.npy
  - pmids_chunk_{i}.json

Optionally add --with-text to also download:
  - pubmed_chunk_{i}.json

Examples:
  python scripts/download_precomputed_embeddings.py --list
  python scripts/download_precomputed_embeddings.py --chunks 0 1 2
  python scripts/download_precomputed_embeddings.py --range 0 5 --with-text
  python scripts/download_precomputed_embeddings.py --all
"""
import argparse
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import config  # noqa: E402

NCBI_DIR = config.RAW_DIR / "ncbi_embeddings"
CHUNK_COUNT = 38


def list_remote():
    with urllib.request.urlopen(config.MEDCPT_EMBEDDINGS_BASE) as r:
        html = r.read().decode("utf-8", "ignore")
    names = sorted(set(re.findall(r"(?:embeds|pmids|pubmed)_chunk_\d+\.\w+", html)))
    print(f"{len(names)} files at {config.MEDCPT_EMBEDDINGS_BASE}")
    for n in names[:12]:
        print(" ", n)
    print(" ...")
    print(f"chunks: 0-{CHUNK_COUNT - 1}")


def chunk_files(chunk: int, with_text: bool):
    names = [f"embeds_chunk_{chunk}.npy", f"pmids_chunk_{chunk}.json"]
    if with_text:
        names.append(f"pubmed_chunk_{chunk}.json")
    return names


def download_file(name: str):
    NCBI_DIR.mkdir(parents=True, exist_ok=True)
    dest = NCBI_DIR / name
    if dest.exists():
        print(f"have {name} ({dest.stat().st_size / 1e6:.0f} MB)")
        return dest
    url = config.MEDCPT_EMBEDDINGS_BASE + name
    print(f"downloading {name} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"  -> {dest} ({dest.stat().st_size / 1e6:.0f} MB)")
    return dest


def parse_chunks(args):
    if args.all:
        return list(range(CHUNK_COUNT))
    if args.chunks:
        return sorted(set(args.chunks))
    if args.range_vals:
        start, end = args.range_vals
        if start > end:
            start, end = end, start
        return list(range(start, end + 1))
    raise SystemExit("Choose one of: --chunks, --range, or --all")


def validate_chunks(chunks):
    bad = [c for c in chunks if c < 0 or c >= CHUNK_COUNT]
    if bad:
        raise SystemExit(f"Invalid chunk ids: {bad}. Valid range is 0-{CHUNK_COUNT - 1}.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="list remote files and exit")
    ap.add_argument("--chunks", type=int, nargs="+", help="specific chunk ids, e.g. 0 1 2")
    ap.add_argument("--range", dest="range_vals", type=int, nargs=2,
                    metavar=("START", "END"), help="inclusive chunk range")
    ap.add_argument("--all", action="store_true", help="download all 38 chunks")
    ap.add_argument("--with-text", action="store_true",
                    help="also download pubmed_chunk_{i}.json metadata/text")
    args = ap.parse_args()

    if args.list:
        list_remote()
        return

    chosen = sum(bool(x) for x in (args.chunks, args.range_vals, args.all))
    if chosen != 1:
        ap.error("Specify exactly one of --chunks, --range, or --all")

    chunks = parse_chunks(args)
    validate_chunks(chunks)

    print(f"destination: {NCBI_DIR}")
    print(f"chunks: {chunks[:8]}{' ...' if len(chunks) > 8 else ''}")
    print(f"download text metadata: {args.with_text}")

    total = 0
    for chunk in chunks:
        print(f"\n=== chunk {chunk} ===")
        for name in chunk_files(chunk, args.with_text):
            path = download_file(name)
            total += path.stat().st_size

    print(f"\nDone. Total local size touched: {total / 1e9:.2f} GB")
    print(f"Files are in: {NCBI_DIR}")


if __name__ == "__main__":
    main()
