# PubMed QA — local, citation-weighted question answering

Ask a medical/scientific question; the tool retrieves relevant PubMed papers —
**weighted toward higher-impact (more-cited) work** to bias answers toward scientific
consensus — and a **local LLM** answers with inline `[PMID]` citations. Everything runs
locally on an Apple-Silicon Mac. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
for the full design and rationale.

**Stack (v1 — fast & lean):** MedCPT embeddings · LanceDB (vectors) · SQLite + FTS5
(BM25, text, citations) · RRF hybrid retrieval · iCite RCR citation weighting ·
Ollama 8B. No servers; cross-encoder rerank deferred to Phase 3.

---

## Phase 0 — prove the pipeline end-to-end

Phase 0 indexes **one PubMed baseline file** (~tens of thousands of abstracts),
embedding **locally** with MedCPT — enough to validate the whole loop on the laptop.
(At scale, the embed step is replaced by *downloaded* precomputed vectors; everything
else is identical — plan §3.)

### 0. Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) running, with the model pulled:
  ```bash
  ollama pull llama3.1:8b
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
python scripts/p0_ask.py --no-llm "statins and dementia"   # retrieval only, no LLM
```

### Phase 0 success criteria (from the plan)
- [ ] Retrieved papers are on-topic (dense + BM25 + RRF working).
- [ ] Citation weighting visibly nudges higher-RCR papers up (compare `--no-llm` output
      with `ALPHA=0` vs `0.1` in `config.py`).
- [ ] LLM answer cites only retrieved `[PMID]`s (citation-validation prints no warning).
- [ ] Note query latency and peak memory — confirms the §7 budget.

### Phase 0b — verify the precomputed-download path (before full build)
Download a chunk of NCBI's precomputed MedCPT vectors
(`ftp.ncbi.nlm.nih.gov/pub/lu/MedCPT/pubmed_embeddings/`), load into LanceDB, and embed
a query with the **local** MedCPT Query-Encoder. Confirm nearest neighbours are sane —
this proves the downloaded article vectors share a space with local query vectors. Pin
`MEDCPT_REVISION`. Then choose PQ params via a recall study (`vectorstore.build_index`).

---

## Cloud embedding / backfill (RunPod) — plan §3.6
`scripts/runpod_embed_medcpt.py` runs **on a RunPod pod** to embed a custom corpus or
**backfill papers newer than NCBI's snapshot**. It writes resumable Parquet shards to the
network volume; transfer them home and load into LanceDB. This is batch *inference*, not
training.

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
  generate.py      Ollama answer + [PMID] citation validation
scripts/
  p0_download_sample.py  p0_build_index.py  p0_ask.py  runpod_embed_medcpt.py
```

## Config knobs (`src/pubmedqa/config.py`)
`PUBMEDQA_DATA` (SSD path) · `PUBMEDQA_LLM` (default `llama3.1:8b`) · `ALPHA` (citation
weight) · `IMPACT_FLOOR` (cold-start) · `USE_CROSS_ENCODER` (off in v1) · `MEDCPT_REVISION`.

## License
[MIT](LICENSE).
