# Full Snapshot All-Chunks Review

Date: 2026-07-02

## What was built

Built the full NCBI precomputed MedCPT PubMed snapshot using chunks `0` through `37` under:

```text
/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full
```

The first uninterrupted run reached chunk 22 and failed because the network connection reset while downloading `embeds_chunk_22.npy`. After deleting the partial/corrupt file, the build was resumed for chunks `22` through `37` and completed.

Important caveat: because the build was resumed, the generated `build_report.json` undercounts `vectors_inserted` for the first segment. Direct SQLite and LanceDB counts were checked manually and are the authoritative counts below.

## Final direct counts

| Metric | Value |
|---|---:|
| SQLite paper rows | 35,920,666 |
| SQLite unique PMIDs | 35,920,666 |
| LanceDB vector rows | 35,920,666 |
| Rows with title or abstract text | 35,891,627 |
| Rows with abstracts | 24,760,250 |
| Rows with years | 35,891,797 |

Coverage:

| Metric | Value |
|---|---:|
| PMID uniqueness | 100.0% |
| SQLite/LanceDB row alignment | 100.0% |
| Text coverage | 99.92% |
| Abstract coverage | 68.93% |
| Year coverage | 99.92% |

Disk use:

| Component | Size |
|---|---:|
| Full data root | 340 GB |
| Raw NCBI embedding/text files | 153 GB |
| LanceDB | 107 GB |
| SQLite | 80 GB |

## Important limitation: citations were not loaded

The full build was run without `--fetch-citations`. This was intentional because the current citation ingestion path uses the iCite API in batches, which is not appropriate for ~36M PMIDs.

Result: the full snapshot currently validates the local full-corpus retrieval architecture, but not full-corpus citation-aware ranking. Citation/RCR values need a bulk iCite ingestion path before the full snapshot can fully satisfy the original citation-weighting goal.

## Full-corpus retrieval benchmark

Retrieval artifact:

```text
baseline_retrieval_full_allchunks_v1.json
```

Judge artifact:

```text
judged_retrieval_full_allchunks_qwen3_strict_v1.json
```

Comparison artifact:

```text
compare_judged_citationrecency_to_full_allchunks_v1.md
```

Aggregate comparison against the previous citation+recency benchmark:

| Metric | Previous citation+recency | Full all-chunks |
|---|---:|---:|
| Questions | 13 | 13 |
| Avg retrieval latency | 13.22s | 7.13s |
| Avg mean judge relevance | 2.577 | 2.600 |
| Total relevance >= 3 | 76 / 130 | 79 / 130 |
| Total relevance >= 2 | 129 / 130 | 129 / 130 |
| Irrelevant papers | 0 | 0 |

Interpretation: the full all-chunks local snapshot is now the best retrieval architecture baseline by judged aggregate quality and latency, even without full-corpus citations loaded. The broader corpus improves recall and candidate quality enough to offset missing citation metadata on this benchmark.

## Notable retrieval observations

Positive changes:

- Full corpus returns strong human clinical evidence for most benchmark questions.
- SGLT2 kidney outcomes improved from mean relevance 2.7 to 2.9 and removed the stale 1980 cell transport paper that appeared in the prior benchmark.
- Beta blockers / heart failure reached mean relevance 3.0.
- Omega-3 and aspirin questions improved judged direct evidence counts.
- Retrieval latency was substantially lower than the previous local benchmark run, likely due to the built IVF-PQ index over the full corpus.

Remaining issues:

- Metformin/cancer still mixes incidence/risk, survival, and mechanistic papers.
- Exercise/insulin sensitivity still returns mostly mechanistic papers despite one strong systematic review.
- Ketogenic diet adults still includes pediatric/child refractory epilepsy papers.
- p53 prognosis remains context-mixed by cancer type and includes mechanistic entries.
- Citation-aware ranking is not yet active at full scale because citations were not bulk-loaded.

## Build/reporting issue discovered

The build report is not resume-aware. After a resumed build, it reports `vectors_inserted` only for the resumed segment, causing false warnings such as:

```text
vectors_inserted=14711622, sqlite rows=35920666
```

Direct LanceDB count shows the actual vector rows equal SQLite rows:

```text
lancedb_rows=35920666
sqlite rows=35920666
```

Recommended fix: make `build_snapshot_from_precomputed.py` support an explicit resume mode or initialize report counters from existing SQLite/LanceDB state when appending to an existing snapshot.

## Recommended next steps

1. Treat `/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full` as the current best full local snapshot.
2. Add a bulk iCite ingestion path for full-corpus citation metadata instead of using the API for millions of PMIDs.
3. Make the build report resume-aware.
4. Run answer generation on the full all-chunks retrieval baseline:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python scripts/evaluate_retrieval.py \
  --questions benchmarks/expanded_questions.txt \
  --with-llm \
  --out baseline_with_answers_full_allchunks_v1.json
```

5. Compare full-corpus answers against `baseline_with_answers_expanded_evidencebasis_v1.json` with `scripts/compare_answers.py`.
6. Update `V1_RELEASE_GATES.md` to distinguish:
   - hard build failures: PMID/vector/SQLite/LanceDB mismatch;
   - warnings: missing abstracts and missing citation metadata.
