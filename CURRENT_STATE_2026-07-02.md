# Current State — PubMed Question Answering

Date: 2026-07-02

## Repository state

Current branch:

```text
main
```

Most recent implementation commit:

```text
75adaf3 Add evidence selection for answer context
```

This commit added the answer-context evidence selection layer and committed the full-snapshot / evidence-selection review notes and comparison reports.

Remaining untracked local files are benchmark/build logs only. They were intentionally not committed.

---

## Product framing

The project is now best described as:

> local, citation- and evidence-aware PubMed question answering over a fixed PubMed snapshot.

It should **not** be framed as a scientific-consensus engine yet. It retrieves and summarizes relevant PubMed abstract evidence locally, with evidence-type, endpoint, population, and citation-aware ranking/selection where metadata are available.

Hard query-time goal remains:

```text
No network calls at runtime.
```

Smoke tests passed with:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

---

## Full local snapshot

A full all-chunks NCBI precomputed MedCPT PubMed snapshot has been built at:

```text
/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full
```

Direct verified counts:

| Metric | Value |
|---|---:|
| SQLite paper rows | 35,920,666 |
| SQLite unique PMIDs | 35,920,666 |
| LanceDB vector rows | 35,920,666 |
| Rows with title or abstract text | 35,891,627 |
| Rows with abstracts | 24,760,250 |
| Rows with years | 35,891,797 |

Disk use:

| Component | Size |
|---|---:|
| Full data root | 340 GB |
| Raw NCBI embedding/text files | 153 GB |
| LanceDB | 107 GB |
| SQLite | 80 GB |

Important caveats:

1. The full build was resumed after a network reset. Direct SQLite/LanceDB counts are correct, but `build_report.json` is not resume-aware and undercounts `vectors_inserted` for the first segment.
2. Full-corpus citation/RCR metadata are **not loaded**. The API-based iCite ingestion path is not suitable for ~36M PMIDs. A bulk iCite ingestion path is needed.
3. Abstract coverage is about 68.93%, which is expected to be a warning rather than a hard failure for a full PubMed snapshot.

---

## Retrieval baseline

Current best full-corpus retrieval artifacts:

```text
baseline_retrieval_full_allchunks_v1.json
judged_retrieval_full_allchunks_qwen3_strict_v1.json
compare_judged_citationrecency_to_full_allchunks_v1.md
full_snapshot_allchunks_review.md
```

Aggregate judged result versus the previous citation+recency benchmark:

| Metric | Previous citation+recency | Full all-chunks |
|---|---:|---:|
| Questions | 13 | 13 |
| Avg retrieval latency | 13.22s | 7.13s |
| Avg mean judge relevance | 2.577 | 2.600 |
| Relevance >= 3 | 76 / 130 | 79 / 130 |
| Relevance >= 2 | 129 / 130 | 129 / 130 |
| Irrelevant papers | 0 | 0 |

Interpretation:

- The full snapshot is now the best retrieval baseline.
- It is faster and slightly better by strict Qwen judge metrics.
- This is true even without full-corpus citation metadata loaded.

---

## Answer baseline without evidence selection

Full-corpus answer artifact:

```text
baseline_with_answers_full_allchunks_v1.json
compare_answers_evidencebasis_to_full_allchunks_v1.md
```

Aggregate result versus the previous Evidence basis benchmark:

| Metric | Previous Evidence basis | Full all-chunks |
|---|---:|---:|
| Questions | 13 | 13 |
| Avg retrieval latency | 14.34s | 6.98s |
| Avg generation latency | 9.47s | 10.64s |
| Citation warning rows | 0 | 0 |
| Invalid cited-PMID rows | 0 | 0 |
| Manual citation extraction mismatches | 0 | 0 |
| Rows with Evidence basis | 13 | 13 |
| Avg cited PMIDs | 4.08 | 3.92 |

Interpretation:

- Full-corpus answers preserve citation validity and Evidence basis structure.
- Retrieval is much faster due to the full built LanceDB index.
- Generation is slightly slower but still within the v1 latency gate.

---

## Evidence-selection layer

New module:

```text
src/pubmedqa/evidence_select.py
```

Updated scripts:

```text
scripts/p0_ask.py
scripts/evaluate_retrieval.py
scripts/compare_answers.py
```

New answer-generation behavior:

```text
retrieve broad candidate pool -> select curated evidence context -> generate answer
```

New flags:

```text
--retrieve-pool N
--evidence-context N
--no-evidence-select
--show-selected        # p0_ask.py only
```

The selector scores papers by:

- inferred question intent;
- required exposure/entity match;
- endpoint match;
- evidence tier;
- population match;
- clinical vs mechanistic fit;
- conflict/null evidence signal;
- near-duplicate title filtering.

It was implemented because prompt-only changes were not enough. The system needed to change which evidence the LLM sees, especially for questions where the raw top-10 mixes prevention, survival, mechanism, pediatric populations, or endpoint-mismatched papers.

### Evidence-selection benchmark

Current evidence-selection artifact:

```text
baseline_with_answers_full_allchunks_evidselect_v2.json
compare_answers_full_allchunks_to_evidselect_v2.md
evidence_selection_v1_review.md
```

Aggregate result versus full all-chunks no-selection answer baseline:

| Metric | No selection | Evidence selection v2 |
|---|---:|---:|
| Questions | 13 | 13 |
| Avg retrieval latency | 6.98s | 7.41s |
| Avg generation latency | 10.64s | 10.99s |
| Citation warning rows | 0 | 0 |
| Invalid cited-PMID rows | 0 | 0 |
| Manual citation extraction mismatches | 0 | 0 |
| Evidence basis rows | 13 | 13 |
| Avg cited PMIDs | 3.92 | 5.08 |
| Avg selected evidence papers | n/a | 8.0 |

Interpretation:

- Evidence selection is a real behavior change with modest latency cost.
- It keeps citation validation clean.
- It generally gives the answer model a broader, more curated, more conflict-aware evidence context.

Observed improvements:

- Omega-3/CVD now explicitly includes both positive and negative/conflicting evidence.
- Adult ketogenic epilepsy no longer selects a pediatric-only systematic review.
- Metformin/cancer no longer selects unrelated high-tier COVID/cancer or hepatocellular papers.

Remaining concerns:

- Metformin/cancer v2 emphasizes prostate-cancer risk from the selected context; this needs manual review.
- Exercise/insulin sensitivity still has many mechanistic papers.
- Adult ketogenic epilepsy still includes some mixed children/young-adult evidence when adult-only evidence is sparse.
- The selector is heuristic and may over-weight title/abstract wording.

Recommended status:

```text
Evidence selection should remain experimental until manual review of key answers is complete.
```

---

## Current CLI behavior

### Retrieval-only

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python scripts/p0_ask.py \
  --no-llm \
  "SGLT2 inhibitors kidney outcomes"
```

### Answer with evidence selection

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python scripts/p0_ask.py \
  --top 10 \
  --retrieve-pool 30 \
  --evidence-context 8 \
  --show-selected \
  "omega-3 supplementation cardiovascular prevention"
```

### Full answer benchmark with evidence selection

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python scripts/evaluate_retrieval.py \
  --questions benchmarks/expanded_questions.txt \
  --with-llm \
  --top 10 \
  --retrieve-pool 30 \
  --evidence-context 8 \
  --out baseline_with_answers_full_allchunks_evidselect_v2.json
```

---

## Important implementation notes

### Citation validation with selected evidence

`evaluate_retrieval.py` validates citations against the selected evidence papers when evidence selection is enabled.

`compare_answers.py` was updated so that valid answer context includes both:

```text
row['papers']
row['selected_evidence_papers']
```

This matters because selected evidence can come from ranks 11-30 and therefore may not appear in the recorded top-10 `papers` list.

### Build report is not resume-aware

The all-chunks build completed correctly, but because it was resumed, `build_report.json` underreports `vectors_inserted`. Direct LanceDB/SQLite counts are correct.

This should be fixed before treating the build report as authoritative for resumed builds.

---

## Next major work

### 1. Manual answer review

Targeted manual review has been completed and recorded in:

```text
evidence_selection_v2_manual_answer_review.md
```

Verdict by target question:

| Question | Verdict |
|---|---|
| metformin/cancer risk | Needs tuning |
| omega-3/CVD prevention | Acceptable with minor caveat |
| aspirin/CRC risk | Acceptable |
| ketogenic diet adults | Needs tuning |
| exercise/insulin sensitivity | Needs tuning |
| p53 prognosis | Acceptable but broad |

Follow-up tuning started in `src/pubmedqa/evidence_select.py`:

- stronger penalty for survival/prognosis papers in risk/prevention questions;
- additional penalty for treatment/therapy endpoints in risk/prevention questions when no prevention/risk framing is present;
- stronger down-rank for animal/cell-line-only evidence in clinical outcome questions;
- safety/adverse endpoint penalty for non-safety clinical questions;
- missing required exposure/entity candidates are rejected instead of backfilled;
- backfill now preserves the mechanistic evidence cap instead of reintroducing too many mechanistic papers.

The tuning passed syntax/local selector smoke checks and a full 13-question answer benchmark was re-run.

New artifacts:

```text
baseline_with_answers_full_allchunks_evidselect_tuned_v1.json
compare_answers_evidselect_v2_to_tuned_v1.md
```

Aggregate tuned-v1 result versus evidence-selection v2:

| Metric | Evidence selection v2 | Tuned v1 | Delta |
|---|---:|---:|---:|
| Questions | 13 | 13 | 0 |
| Avg retrieval latency | 7.41s | 7.58s | +0.17s |
| Avg generation latency | 10.99s | 9.76s | -1.23s |
| Citation warning rows | 0 | 0 | 0 |
| Invalid cited-PMID rows | 0 | 0 | 0 |
| Manual citation extraction mismatches | 0 | 0 | 0 |
| Rows with Evidence basis | 13 | 13 | 0 |
| Rows with review flags | 1 | 1 | 0 |

The GLP-1 benchmark caveat was fixed after the tuned-v1 run. Citation processing now:

- normalizes retrieved bare/parenthesized PMIDs to bracket format, e.g. `(35546664)` -> `[35546664]`;
- extracts `pmids_anywhere` in addition to bracketed `cited_pmids`;
- records `unbracketed_pmids`, `invalid_pmids_anywhere`, `citation_format_warning`, and `citation_normalization_note` in benchmark artifacts;
- reports invalid-PMID-anywhere, unbracketed-PMID, and normalization-note rows in answer comparisons.

Citation-fix benchmark artifacts:

```text
baseline_with_answers_full_allchunks_evidselect_tuned_citationfix_v1.json
compare_answers_tuned_v1_to_citationfix_v1.md
compare_answers_evidselect_v2_to_tuned_citationfix_v1.md
```

Aggregate tuned+citationfix result versus evidence-selection v2:

| Metric | Evidence selection v2 | Tuned + citation fix | Delta |
|---|---:|---:|---:|
| Questions | 13 | 13 | 0 |
| Avg retrieval latency | 7.41s | 7.40s | -0.01s |
| Avg generation latency | 10.99s | 9.60s | -1.39s |
| Citation warning rows | 0 | 0 | 0 |
| Invalid cited-PMID rows | 0 | 0 | 0 |
| Invalid PMID-anywhere rows | 1 | 0 | -1 |
| Unbracketed PMID rows | 1 | 0 | -1 |
| Citation normalization note rows | 0 | 1 | +1 |
| Manual citation extraction mismatches | 0 | 0 | 0 |
| Rows with Evidence basis | 13 | 13 | 0 |
| Rows with review flags | 1 | 1 | 0 |

The one normalization note row is GLP-1: the model produced parenthesized PMIDs, and post-processing converted them to `[PMID]` citations with no invalid PMIDs.

### 2. Bulk iCite ingestion

Implement full-corpus citation/RCR ingestion from the iCite bulk dataset. The current API path is only suitable for small benchmark sets.

Needed so the full snapshot actually satisfies the original citation-weighting goal at scale.

### 3. Resume-aware build reporting

Update `scripts/build_snapshot_from_precomputed.py` to support either:

- explicit `--resume`; or
- report counters initialized from existing SQLite/LanceDB state.

Hard checks should use direct final counts, not only per-run inserted counts.

### 4. Decide whether evidence selection becomes default

Evidence selection is currently enabled by default in `evaluate_retrieval.py --with-llm` and `p0_ask.py` unless `--no-evidence-select` is passed.

Before declaring it release-default, complete manual review and tune known edge cases.

### 5. Update paper / release gates

After manual review and bulk citation ingest decisions:

- update `V1_RELEASE_GATES.md`;
- update the paper to mention the full all-chunks snapshot and evidence-selection layer;
- decide whether to rename the paper files away from `v4`.
