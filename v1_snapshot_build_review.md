# v1 Snapshot Build Review — 50k Chunk Tests

Date: 2026-07-02

Purpose: validate the production-aligned snapshot build path from precomputed MedCPT chunks, verify build-integrity reporting, and test offline query-time retrieval/generation against fresh local snapshots.

## Builds run

### Oldest chunk smoke build

Command:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_test" \
./.venv/bin/python scripts/build_snapshot_from_precomputed.py \
  --chunks 0 \
  --rows 50000 \
  --overwrite \
  --fetch-citations \
  --build-index
```

Artifacts/logs:

```text
build_snapshot_test_chunk0_50k.log
build_snapshot_test_chunk0_50k_report_excerpt.json
baseline_retrieval_snapshot_chunk0_50k_v1.json
judged_retrieval_snapshot_chunk0_50k_qwen3_strict_v1.json
```

Build result:

| Check | Result |
|---|---:|
| SQLite rows | 50,000 |
| LanceDB rows | 50,000 |
| Unique PMIDs | 50,000 |
| Duplicate PMIDs | 0 |
| Year coverage | 100.0% |
| Citation coverage | 100.0% |
| Abstract coverage | 49.034% |
| Integrity status | `warn` |

Integrity warning cause: abstract coverage was low because chunk 0 contains old PubMed records with many missing abstracts.

### Recent chunk smoke build

Command:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_test_recent" \
./.venv/bin/python scripts/build_snapshot_from_precomputed.py \
  --chunks 37 \
  --rows 50000 \
  --overwrite \
  --fetch-citations \
  --build-index
```

Artifacts/logs:

```text
build_snapshot_test_chunk37_50k.log
build_snapshot_test_chunk37_50k_report_excerpt.json
baseline_retrieval_snapshot_chunk37_50k_v1.json
judged_retrieval_snapshot_chunk37_50k_qwen3_strict_v1.json
```

Build result:

| Check | Result |
|---|---:|
| SQLite rows | 50,000 |
| LanceDB rows | 50,000 |
| Unique PMIDs | 50,000 |
| Duplicate PMIDs | 0 |
| Year coverage | 100.0% |
| Citation coverage | 98.912% |
| Abstract coverage | 88.488% |
| Missing text rows | 129 |
| Integrity status | `warn` |

Integrity warning cause: the fresh 50k recent slice still had 129 rows with no text and abstract coverage below the current 95% threshold.

## Offline query-time smoke tests

Offline-style environment variables were used for query-time tests:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

### Retrieval-only smoke

Recent chunk command:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_test_recent" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python scripts/p0_ask.py --no-llm --show-groups \
  "SGLT2 inhibitors kidney outcomes"
```

Result: retrieval succeeded fully locally. Example latency: about 1.21s for top 10 on the 50k recent chunk.

### Retrieval + local MLX answer smoke

Recent chunk command:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_test_recent" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python scripts/p0_ask.py --top 5 \
  "SGLT2 inhibitors kidney outcomes"
```

Result: retrieval and local MLX answer generation succeeded with offline Hugging Face flags. Example timing:

```text
retrieval:          ~0.99s
generation:         ~7.95s
```

Caveat: answer quality was limited by the small single-chunk corpus. The generated answer leaned heavily on one relevant paper and the retrieved top-5 included several indirectly related papers.

## Expanded benchmark results on fresh snapshots

### Chunk 0, 50k oldest records

Retrieval benchmark:

```text
baseline_retrieval_snapshot_chunk0_50k_v1.json
```

Judged benchmark:

```text
judged_retrieval_snapshot_chunk0_50k_qwen3_strict_v1.json
```

Aggregate judged result:

| Metric | Value |
|---|---:|
| Questions | 13 |
| Judged papers | 111 |
| Avg mean judge relevance | 0.667 |
| Relevance >= 3 | 0 |
| Relevance >= 2 | 5 |
| Irrelevant papers | 45 |

Interpretation: chunk 0 is not suitable for the current expanded benchmark. It consists mostly of older records and lacks modern benchmark topics. Example: `p53 mutation and cancer prognosis` returned zero papers.

### Chunk 37, 50k recent records

Retrieval benchmark:

```text
baseline_retrieval_snapshot_chunk37_50k_v1.json
```

Judged benchmark:

```text
judged_retrieval_snapshot_chunk37_50k_qwen3_strict_v1.json
```

Aggregate judged result:

| Metric | Value |
|---|---:|
| Questions | 13 |
| Judged papers | 130 |
| Avg mean judge relevance | 1.669 |
| Relevance >= 3 | 12 |
| Relevance >= 2 | 77 |
| Irrelevant papers | 2 |

Interpretation: a recent 50k slice is much better than the oldest chunk and validates that the production-aligned build can support local retrieval. However, it is still not sufficient for v1 quality on the expanded benchmark. The benchmark expects broad historical coverage across topics, while one recent slice only covers a narrow PMID/time band.

## Key findings

1. **The production-aligned build path works.**
   - Precomputed vectors and text load correctly.
   - SQLite/LanceDB row counts match.
   - Duplicate PMID tracking works.
   - Citation ingestion works at 50k scale.
   - IVF-PQ index build completes.

2. **The new integrity report is useful.**
   - It correctly surfaced low abstract coverage in chunk 0.
   - It correctly surfaced missing text/abstract coverage issues in chunk 37.
   - It validates vector/SQLite/LanceDB row alignment.

3. **Query-time local/offline behavior works for smoke tests.**
   - Retrieval and local MLX generation succeeded with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.
   - No PubMed efetch path was used by `p0_ask.py`.

4. **Single 50k chunks are not enough for the benchmark or v1 product.**
   - Chunk 0 is too old.
   - Chunk 37 is too narrow/recent.
   - v1 needs a larger and more representative fixed snapshot.

5. **Current benchmark artifacts from the existing larger local data remain the best quality baseline.**
   - `judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json` remains the preferred quality baseline.
   - The fresh 50k builds are build-path validation tests, not replacement quality baselines.

## Recommendation

Move from single-chunk smoke builds to a representative multi-chunk fixed snapshot.

Suggested next build candidates:

1. **Recent multi-chunk slice**: chunks `33 34 35 36 37`
   - likely around recent literature;
   - manageable relative to full corpus;
   - should improve coverage for modern clinical questions.

2. **Stratified slice**: selected chunks across the full PMID/time range, e.g. `0 10 20 30 37`
   - better historical coverage;
   - useful for testing whether a non-contiguous snapshot is acceptable;
   - less realistic than a contiguous full/recent corpus.

3. **Larger contiguous corpus**: all chunks if disk/time permit.
   - best aligned with product goal;
   - requires disk/time planning because chunk files and LanceDB outputs are large.

Before scaling up, consider changing the build-integrity gates to distinguish:

- hard failures: PMID/vector/SQLite/LanceDB mismatch, duplicate PMIDs, missing LanceDB rows;
- warnings: missing abstracts/text below a documented threshold, because PubMed records can legitimately lack abstracts.

## Next steps

1. Decide v1 fixed snapshot policy:
   - recent contiguous multi-chunk;
   - stratified evaluation slice;
   - full corpus.
2. Run a multi-chunk build, probably chunks `33 34 35 36 37`, with citations and IVF-PQ index.
3. Re-run expanded retrieval benchmark on that multi-chunk snapshot.
4. Judge the multi-chunk retrieval artifact.
5. Compare against the current best larger-local-data baseline.
6. Update `V1_RELEASE_GATES.md` with refined build-integrity thresholds if missing abstracts should be warnings rather than release blockers.
