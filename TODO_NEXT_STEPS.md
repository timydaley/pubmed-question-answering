# TODO — Next Steps

## Priority 1 — make the MLX migration complete
- [ ] Test `scripts/p0_ask.py` end-to-end with MLX
- [ ] Confirm `src/pubmedqa/generate.py` loads the model and produces structured output
- [ ] Verify citation validation still works correctly
- [ ] Check whether any code still references Ollama
- [ ] Update `IMPLEMENTATION_PLAN.md` to replace stale Ollama mentions

### Commands
```bash
cd pubmed-question-answering
source .venv/bin/activate
pip install -r requirements.txt
export PUBMEDQA_DATA="$HOME/Documents/pubmed_qa"
export PUBMEDQA_LLM=mlx-community/Llama-3.1-8B-Instruct-4bit
python scripts/p0_ask.py "does metformin reduce cancer risk?"
python scripts/p0_ask.py --summary-only --per-paper-summaries "statins and dementia"
rg -n "Ollama|OLLAMA_URL|llama3.1:8b" .
```

## Priority 2 — verify the production-aligned ingest path
- [ ] Run `scripts/download_precomputed_embeddings.py --list`
- [ ] Download one small initial chunk set, e.g. chunk `0`
- [ ] Run `scripts/p0b_verify_precomputed.py --chunk 0 --rows 50000`
- [ ] Confirm alignment is strong enough to trust the pinned `MEDCPT_REVISION`
- [ ] Record recommended IVF-PQ / `nprobes` settings from the verification run

### Commands
```bash
cd pubmed-question-answering
source .venv/bin/activate
python scripts/download_precomputed_embeddings.py --list
python scripts/download_precomputed_embeddings.py --chunks 0 --with-text
python scripts/p0b_verify_precomputed.py --chunk 0 --rows 50000
```

## Priority 3 — build a usable local snapshot
- [ ] Run `scripts/build_snapshot_from_precomputed.py --chunks 0 --overwrite --build-index`
- [ ] Optionally rerun with `--fetch-citations`
- [ ] Inspect `build_report.json`
- [ ] Check:
  - [ ] docs inserted
  - [ ] vectors inserted
  - [ ] PMID match rate
  - [ ] missing abstract/text rate
  - [ ] citation coverage

### Commands
```bash
cd pubmed-question-answering
source .venv/bin/activate
python scripts/build_snapshot_from_precomputed.py --chunks 0 --overwrite --build-index
python scripts/build_snapshot_from_precomputed.py --chunks 0 --fetch-citations
python -m json.tool "$PUBMEDQA_DATA/build_report.json"
```

## Priority 4 — validate query-time behavior
- [ ] Run retrieval-only queries with `scripts/p0_ask.py --no-llm`
- [ ] Run full LLM summaries on a few benchmark questions
- [ ] Check whether top papers are visibly relevant
- [ ] Check whether the evidence/citation boost is modest rather than dominating relevance
- [ ] Measure rough latency for retrieval and generation

### Commands
```bash
cd pubmed-question-answering
source .venv/bin/activate
python scripts/p0_ask.py --no-llm "does metformin reduce cancer risk?"
python scripts/p0_ask.py --no-llm "statins and risk of dementia"
python scripts/p0_ask.py --summary-only "vitamin D supplementation and respiratory infections"
python scripts/p0_ask.py --summary-only --per-paper-summaries "GLP-1 agonists and cardiovascular outcomes"
```

## Priority 5 — tighten docs and usability
- [ ] Update `README.md` if the actual MLX usage differs from current instructions
- [ ] Add a short “known working setup” note (Mac model, Python version, MLX model)
- [ ] Document the new `p0_ask.py` flags with examples
- [ ] Make sure Phase 0 vs snapshot-build workflows are clearly distinguished

### Commands
```bash
cd pubmed-question-answering
rg -n "MLX|Ollama|p0_ask.py|Phase 0|snapshot" README.md IMPLEMENTATION_PLAN.md scripts/p0_ask.py src/pubmedqa/config.py src/pubmedqa/generate.py
```

## Priority 6 — prepare for tuning/eval
- [ ] Define a small set of test questions
- [ ] Record expected “good” retrieval behavior
- [ ] Decide what to track first:
  - [ ] retrieval relevance spot checks
  - [ ] citation validity
  - [ ] latency
  - [ ] memory
- [ ] Capture baseline results before changing ranking params

### Suggested starter questions
- does metformin reduce cancer risk?
- statins and risk of dementia
- vitamin D supplementation and respiratory infections
- aspirin for primary prevention cardiovascular disease
- GLP-1 agonists and cardiovascular outcomes

## Suggested execution order
1. MLX end-to-end test
2. Clean up stale Ollama references
3. Verify precomputed chunk alignment
4. Build one snapshot chunk locally
5. Run query spot checks
6. Record baseline metrics
