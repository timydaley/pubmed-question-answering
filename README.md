# PubMed QA — local, evidence-aware question answering

Ask a medical/scientific question; the tool retrieves relevant PubMed papers,
applies a **small evidence/citation-aware ranking boost**, and a **local LLM** answers
with inline `[PMID]` citations. The system is designed to run **fully offline at query time** on an Apple-Silicon Mac. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
for the full design and rationale.

**Stack (v1 — fast & lean):** MedCPT embeddings · LanceDB (vectors) · SQLite + FTS5
(BM25, text, citations) · RRF hybrid retrieval · bounded citation/evidence boost ·
MLX local LLM on Apple Silicon. No servers; cross-encoder rerank deferred to a later phase.

---

## Phase 0 — prove the pipeline end-to-end

Phase 0 indexes **one PubMed baseline file** (~tens of thousands of abstracts),
embedding **locally** with MedCPT — enough to validate the core loop on the laptop.
(At scale, the embed step is replaced by *downloaded* precomputed vectors; everything
else is intended to stay aligned with the production path — plan §4.)

### 0. Prerequisites
- Python 3.11+
- Apple Silicon Mac (for MLX)
- Set the local model to use with MLX if you want to override the default:
  ```bash
  export PUBMEDQA_LLM=mlx-community/Llama-3.1-8B-Instruct-4bit
  ```
- Point storage at your external SSD:
  ```bash
  export PUBMEDQA_DATA=/Volumes/<your-ssd>/pubmedqa_data
  ```

### 1. Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Download one baseline file
```bash
python scripts/p0_download_sample.py --list           # see available files
python scripts/p0_download_sample.py pubmed26n0001.xml.gz
```

### 3. Build the index (parse → SQLite/FTS5 → MedCPT embed → LanceDB → iCite)
```bash
python scripts/p0_build_index.py "$PUBMEDQA_DATA/raw/pubmed26n0001.xml.gz" --limit 30000
```
Note the printed **docs/sec** — this is your local embedding throughput (used only to
size the daily-delta path; the bulk corpus is downloaded, not embedded locally).

### 4. Ask
```bash
python scripts/p0_ask.py "does metformin reduce cancer risk?"
python scripts/p0_ask.py --no-llm "statins and dementia"                # retrieval only, no LLM
python scripts/p0_ask.py --no-llm --show-groups "statins and dementia"  # inspect balanced context groups
python scripts/p0_ask.py --top 20 --second-pass-summary --summary-source retrieved --map-reduce \
  --summary-notes-out p53_notes.json \
  "p53 mutation and cancer prognosis"                                   # deeper evidence synthesis
python scripts/p0_ask.py --second-pass-summary --summary-source cited --max-cited-summary-papers 5 \
  "does metformin reduce cancer risk?"                                  # selective cited-paper synthesis
```

### Phase 0 success criteria (from the plan)
- [ ] Retrieved papers are on-topic (dense + BM25 + RRF working).
- [ ] The bounded evidence/citation boost visibly but modestly changes ranking.
- [ ] LLM answer cites only retrieved `[PMID]`s (citation-validation prints no warning).
- [ ] Query latency and peak memory are acceptable on the target laptop.

### Phase 0b — verify the precomputed-download path (before full build)
NCBI publishes MedCPT vectors for all of PubMed as 38 chunks
(`embeds_chunk_{i}.npy` + `pmids_chunk_{i}.json` + `pubmed_chunk_{i}.json`) at
`ftp.ncbi.nlm.nih.gov/pub/lu/MedCPT/pubmed_embeddings/`. This script downloads one chunk
and runs three checks:

```bash
python scripts/p0b_verify_precomputed.py --list                 # see the chunks
python scripts/p0b_verify_precomputed.py --chunk 0 --rows 50000 # ~1-3 GB download
```
1. **Alignment** — re-embeds sample abstracts with the *local* MedCPT article encoder and
   compares to NCBI's vectors (cosine ~0.99 ⇒ same space / revision matches).
2. **Query-space** — embeds sample questions with the *local* query encoder and retrieves
   from the downloaded vectors; titles should be on-topic.
3. **PQ recall** — sweeps IVF-PQ `nprobes` vs. exact search to pick the smallest setting
   with ≥95% recall (the params for the full-corpus index).

Pin `MEDCPT_REVISION` in `config.py` so the full build matches what you verified here.
(`pubmed_chunk_{i}.json` also holds the title/abstract text — handy to populate SQLite at
full-build time instead of parsing baseline XML.)

### Download more precomputed embedding chunks
Use this helper to fetch multiple NCBI MedCPT chunks ahead of time:

```bash
python scripts/download_precomputed_embeddings.py --list
python scripts/download_precomputed_embeddings.py --chunks 0 1 2
python scripts/download_precomputed_embeddings.py --range 0 5 --with-text
```

### Snapshot build from precomputed embeddings
This is the production-aligned ingest path for v1:

```bash
python scripts/build_snapshot_from_precomputed.py --list
python scripts/build_snapshot_from_precomputed.py --chunks 0 --overwrite --build-index
python scripts/build_snapshot_from_precomputed.py --chunks 0 1 2 --fetch-citations
```

Outputs:
- SQLite papers + FTS5 index
- LanceDB vector table
- `build_report.json` with integrity stats

---

## Layout
```
src/pubmedqa/
  config.py        paths, models, retrieval + citation-weighting params
  parse_pubmed.py  streaming MEDLINE XML parser
  db.py            SQLite schema + contentless FTS5 (BM25) + citations
  embed.py         MedCPT article/query encoders (MPS), L2-normalized [CLS]
  vectorstore.py   LanceDB (cosine; IVF-PQ at scale)
  citations.py     iCite citation_count + RCR
  retrieve.py      BM25 + dense -> RRF -> bounded citation re-score
  generate.py      MLX answer + [PMID] citation validation
  summarize.py     second-pass cited/retrieved-paper synthesis
scripts/
  p0_download_sample.py  p0_build_index.py  p0_ask.py
  p0b_verify_precomputed.py  download_precomputed_embeddings.py
  build_snapshot_from_precomputed.py  evaluate_retrieval.py
  summarize_citations.py  judge_retrieval.py  compare_eval.py
```

### Small retrieval benchmark

The current frozen v4 baseline is documented in [`paper/pubmedqa_v4_baseline_icml2026.pdf`](paper/pubmedqa_v4_baseline_icml2026.pdf) with source in [`paper/pubmedqa_v4_baseline_icml2026.tex`](paper/pubmedqa_v4_baseline_icml2026.tex).

Capture a repeatable baseline before tuning retrieval thresholds:

```bash
python scripts/evaluate_retrieval.py --print-titles --out baseline_retrieval.json
python scripts/evaluate_retrieval.py --with-llm --out baseline_with_answers.json
```

Use `--questions my_questions.txt` to provide one question per line.

## Config knobs (`src/pubmedqa/config.py`)
`PUBMEDQA_DATA` (SSD path) · `PUBMEDQA_LLM` (default `mlx-community/Llama-3.1-8B-Instruct-4bit`) ·
`PUBMEDQA_LLM_MAX_TOKENS` · `ALPHA` (bounded citation/evidence weight) · `IMPACT_FLOOR`
(cold-start) · `USE_CROSS_ENCODER` (off in v1) · `MEDCPT_REVISION`.

## License
[MIT](LICENSE).
