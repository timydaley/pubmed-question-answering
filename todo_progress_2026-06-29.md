# TODO Progress — 2026-06-29

## Completed in this pass

### 1. Pushed benchmark commit

Pushed commit:

```text
da27fdd Add prompt-fix answer benchmark
```

Branch:

```text
feat/snapshot-builder
```

### 2. Added explicit evidence-basis sections

Updated `src/pubmedqa/generate.py` so normal answers now require:

```text
## Evidence basis
```

The section asks for one concise sentence describing evidence type and population/context, such as randomized outcome trials, observational cohorts/meta-analyses, or mechanistic/cell-line evidence.

Updated `src/pubmedqa/summarize.py` so second-pass summaries now require:

```text
## Evidence basis
```

### 3. Added endpoint-specific prompt instructions

Updated answer and summary prompts to explicitly distinguish:

- risk/incidence/prevention
- survival after diagnosis
- treatment response
- surrogate outcomes
- mechanistic findings

Also reinforced that clinical questions should prefer the strongest and most directly relevant human clinical evidence.

### 4. Improved cited-only summary selectivity

Added to `scripts/p0_ask.py`:

```bash
--max-cited-summary-papers N
```

This limits `--summary-source cited` to the first N cited retrieved papers, preserving retrieval order. Example:

```bash
./.venv/bin/python scripts/p0_ask.py \
  --second-pass-summary \
  --summary-source cited \
  --max-cited-summary-papers 5 \
  "does metformin reduce cancer risk?"
```

Added to `scripts/summarize_citations.py`:

```bash
--max-papers N
```

This limits selected PMIDs after de-duplication.

### 5. Updated README examples

Added a selective cited-paper synthesis example using `--max-cited-summary-papers`.

## Validation

Compile check passed:

```bash
./.venv/bin/python -m py_compile \
  scripts/p0_ask.py \
  scripts/summarize_citations.py \
  src/pubmedqa/generate.py \
  src/pubmedqa/summarize.py
```

Smoke test:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa" \
./.venv/bin/python scripts/p0_ask.py \
  --top 5 \
  --second-pass-summary \
  --summary-source cited \
  --max-cited-summary-papers 3 \
  "does metformin reduce cancer risk?"
```

Observed:

- Retrieval: 13.71s
- Answer generation: 6.88s
- Second-pass summary: 7.41s
- Answer included the new `## Evidence basis` section.
- Second-pass summary included the new `## Evidence basis` section.
- `--max-cited-summary-papers 3` correctly limited the cited-paper synthesis to 3 papers.

## Build-integrity / metadata check

Dry-run metadata enrichment command:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa" \
./.venv/bin/python scripts/enrich_metadata.py --missing --limit 100 --dry-run
```

Output:

```text
selected 100 unique PMIDs
first PMIDs: 1, 2, 3, ...
```

Current build report summary from `$PUBMEDQA_DATA/build_report.json`:

```text
source: ncbi_precomputed_medcpt
chunks: [36]
docs_inserted: 993472
vectors_inserted: 993472
pmids_seen: 993472
pmid_vector_rows: 993472
records_with_text: 991264
records_missing_text: 2208
records_missing_abstract: 141633
citations_loaded: 0
sqlite_paper_rows: 35920666
pmid_match_rate: 0.027657
fetch_citations: false
build_index: false
```

Notes:

- The chunk-specific vector/text alignment looks internally consistent for chunk 36.
- `citations_loaded: 0` because the build report says `fetch_citations: false`.
- `pmid_match_rate` is low because the SQLite database contains many more paper rows than this one-chunk vector snapshot.
- Broader metadata enrichment remains a future longer-running task.

## Recommended next steps

1. Commit the current prompt/CLI refinements.
2. Regenerate a small smoke answer or full expanded benchmark with the new `Evidence basis` prompt if desired.
3. Decide whether to run broader metadata enrichment or rebuild a cleaner multi-chunk snapshot with citations enabled.
