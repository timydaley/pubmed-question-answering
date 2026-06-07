#!/usr/bin/env python3
"""Phase 0b: verify NCBI's precomputed MedCPT vectors before the full build.

Answers three questions (plan §3, §10 Phase 0):
  1. ALIGNMENT  — does our LOCAL MedCPT article encoder reproduce NCBI's vectors?
                  (cosine ~0.99 if the pinned revision matches; lower => text drift
                  or a revision mismatch.)
  2. QUERY-SPACE — does our LOCAL query encoder retrieve on-topic articles from the
                  downloaded vectors? (the real functional requirement)
  3. PQ RECALL  — what IVF-PQ nprobes gives >=95% recall vs. exact search? (sets the
                  scale-up index params)

Usage:
  python scripts/p0b_verify_precomputed.py --list
  python scripts/p0b_verify_precomputed.py --chunk 0 --rows 50000
  python scripts/p0b_verify_precomputed.py --chunk 0 --skip-download   # reuse files

NOTE: one embeds_chunk_*.npy is ~1.1-2.9 GB. pmids_chunk_*.json is small (~5-11 MB).
We do NOT download pubmed_chunk_*.json (text); abstracts for the alignment sample come
from the lightweight efetch API instead.
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import config, embed, parse_pubmed, vectorstore  # noqa: E402
import requests  # noqa: E402

NCBI_DIR = config.RAW_DIR / "ncbi_embeddings"


def _cos(a, b):
    a = np.asarray(a, dtype=np.float64); b = np.asarray(b, dtype=np.float64)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def _norm_rows(m):
    m = np.asarray(m, dtype=np.float32)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-12)


def list_dir():
    import re
    with urllib.request.urlopen(config.MEDCPT_EMBEDDINGS_BASE) as r:
        html = r.read().decode("utf-8", "ignore")
    names = sorted(set(re.findall(r"(?:embeds|pmids|pubmed)_chunk_\d+\.\w+", html)))
    print(f"{len(names)} files at {config.MEDCPT_EMBEDDINGS_BASE}")
    for n in names[:6]:
        print("  ", n)
    print("   ... (chunks 0-37)")


def download_chunk(n):
    NCBI_DIR.mkdir(parents=True, exist_ok=True)
    for name in (f"embeds_chunk_{n}.npy", f"pmids_chunk_{n}.json"):
        dest = NCBI_DIR / name
        if dest.exists():
            print(f"  have {name} ({dest.stat().st_size/1e6:.0f} MB)")
            continue
        url = config.MEDCPT_EMBEDDINGS_BASE + name
        print(f"  downloading {name} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"    -> {dest.stat().st_size/1e6:.0f} MB")


def load_chunk(n, rows):
    embeds = np.load(NCBI_DIR / f"embeds_chunk_{n}.npy", mmap_mode="r")
    pmids = json.load(open(NCBI_DIR / f"pmids_chunk_{n}.json"))
    rows = min(rows, embeds.shape[0])
    vecs = np.array(embeds[:rows], dtype=np.float32)         # materialize subsample
    pmids = [int(p) for p in pmids[:rows]]
    print(f"  loaded chunk {n}: {rows} x {vecs.shape[1]} (of {embeds.shape[0]})")
    return pmids, vecs


def efetch(pmids):
    r = requests.get(config.EFETCH_URL,
                     params={"db": "pubmed", "id": ",".join(map(str, pmids)),
                             "retmode": "xml"}, timeout=180)
    r.raise_for_status()
    return {rec["pmid"]: rec for rec in parse_pubmed.parse_efetch_xml(r.content)}


def alignment_check(pmids, vecs, k):
    print("\n[1] ALIGNMENT — local article encoder vs NCBI vectors")
    sample = pmids[:k]
    text = efetch(sample)
    have = [p for p in sample if p in text and text[p]["abstract"]]
    if not have:
        print("    (could not fetch abstracts for the sample; skipping)")
        return
    recs = [text[p] for p in have]
    local = embed.embed_articles(recs)                       # normalized [CLS]
    idx = {p: i for i, p in enumerate(pmids)}
    csims = np.array([_cos(local[i], vecs[idx[p]]) for i, p in enumerate(have)])
    print(f"    n={len(have)}  mean cos={csims.mean():.4f}  min={csims.min():.4f}")
    if csims.mean() > 0.99:
        print("    PASS: same embedding space (revision matches).")
    elif csims.mean() > 0.95:
        print("    OK-ish: likely same space; small gaps = abstract text drift.")
    else:
        print("    WARNING: low similarity — check MEDCPT_REVISION / input formatting.")


def query_space_check(table_pmids, queries, k=5):
    print("\n[2] QUERY-SPACE — local query encoder retrieves from NCBI vectors")
    titles = {}
    for q in queries:
        qv = embed.embed_query(q)
        hits = vectorstore.search(qv, k, table=config.LANCE_VERIFY_TABLE)
        missing = [h for h in hits if h not in titles]
        if missing:
            titles.update({p: r.get("title", "") for p, r in efetch(missing).items()})
        print(f"  Q: {q}")
        for h in hits:
            print(f"     [{h}] {titles.get(h, '(title?)')[:88]}")


def pq_recall_study(pmids, vecs, queries, nprobe_grid=(5, 10, 20, 40, 80),
                    num_partitions=256, num_sub_vectors=96, topk=100):
    print("\n[3] PQ RECALL — IVF-PQ vs exact, to pick nprobes")
    qv = _norm_rows([embed.embed_query(q) for q in queries])
    nvecs = _norm_rows(vecs)
    gt = []                                                  # exact top-k via numpy
    for i in range(qv.shape[0]):
        sims = nvecs @ qv[i]
        gt.append(set(pmids[j] for j in np.argpartition(-sims, topk)[:topk]))

    vectorstore.build_index(table=config.LANCE_VERIFY_TABLE,
                            num_partitions=num_partitions,
                            num_sub_vectors=num_sub_vectors)
    print(f"    index: IVF{num_partitions}/PQ{num_sub_vectors}  (~{num_sub_vectors} B/vec)")
    for nprobes in nprobe_grid:
        recs = []
        for i in range(qv.shape[0]):
            pred = set(vectorstore.search(qv[i], topk,
                                          table=config.LANCE_VERIFY_TABLE,
                                          nprobes=nprobes))
            recs.append(len(pred & gt[i]) / max(1, len(gt[i])))
        r = float(np.mean(recs))
        flag = "  <- recommended" if r >= 0.95 else ""
        print(f"    nprobes={nprobes:>3}  recall@{topk}={r:.3f}{flag}")


SAMPLE_QUERIES = [
    "does metformin reduce cancer risk",
    "statins and risk of dementia",
    "vitamin D supplementation and respiratory infections",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--rows", type=int, default=50000)
    ap.add_argument("--samples", type=int, default=25)
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    if args.list:
        list_dir(); return

    if not args.skip_download:
        print(f"downloading chunk {args.chunk} (embeds .npy is GB-scale) ...")
        download_chunk(args.chunk)

    pmids, vecs = load_chunk(args.chunk, args.rows)

    print("building LanceDB verify table ...")
    vectorstore.create(pmids, _norm_rows(vecs), overwrite=True,
                       table=config.LANCE_VERIFY_TABLE)

    alignment_check(pmids, vecs, args.samples)
    query_space_check(pmids, SAMPLE_QUERIES)
    pq_recall_study(pmids, vecs, SAMPLE_QUERIES)

    print("\nPhase 0b done. If alignment passes and a small nprobes hits >=0.95 recall, "
          "the download path is good — set those PQ params for the full build.")


if __name__ == "__main__":
    main()
