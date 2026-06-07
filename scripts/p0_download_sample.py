#!/usr/bin/env python3
"""Download one PubMed baseline file for the Phase 0 spike.

The yearly directory listing changes (e.g. pubmed26n0001.xml.gz for the 2026
production year). Pass an explicit filename, or list what's available:

    python scripts/p0_download_sample.py --list
    python scripts/p0_download_sample.py pubmed26n0001.xml.gz
"""
import argparse
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("filename", nargs="?", help="e.g. pubmed26n0001.xml.gz")
    ap.add_argument("--list", action="store_true", help="print the baseline index page")
    args = ap.parse_args()

    if args.list or not args.filename:
        with urllib.request.urlopen(config.PUBMED_BASELINE_BASE) as r:
            html = r.read().decode("utf-8", "ignore")
        names = sorted(set(__import__("re").findall(r"pubmed\d+n\d+\.xml\.gz", html)))
        print(f"{len(names)} baseline files at {config.PUBMED_BASELINE_BASE}")
        for n in names[:10]:
            print("  ", n)
        if names:
            print(f"\nRun: python scripts/p0_download_sample.py {names[0]}")
        return

    config.ensure_dirs()
    url = config.PUBMED_BASELINE_BASE + args.filename
    dest = config.RAW_DIR / args.filename
    print(f"downloading {url}\n      -> {dest}")
    urllib.request.urlretrieve(url, dest)
    print(f"done ({dest.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
