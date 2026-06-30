# Session Summary + Next Steps

## What we did in this session

### 1. Froze the v4 retrieval baseline
- Reviewed repo status and generated artifacts.
- Added `.gitignore` rules so older/smoke JSON files and LaTeX build products stay ignored.
- Committed the current useful v4 baseline artifacts and paper files.

Committed:
```text
c660263 Freeze v4 retrieval baseline artifacts
```

Key frozen artifacts:
- `baseline_retrieval_v4.json`
- `judged_retrieval_qwen3_v4.json`
- `baseline_with_answers_v4.json`
- `paper/pubmedqa_v4_baseline_icml2026.{tex,bib,pdf}`
- `scripts/evaluate_retrieval.py`
- `scripts/judge_retrieval.py`

### 2. Added metadata enrichment tooling
- Fixed `scripts/build_snapshot_from_precomputed.py` so it extracts `year` from NCBI precomputed `d` date fields such as `19750601`.
- Added `scripts/enrich_metadata.py`, which uses PubMed efetch to enrich local SQLite metadata:
  - `journal`
  - `year`
  - `pubtypes`
  - `mesh`
  - missing title/abstract when needed
- Ran enrichment on baseline and expanded benchmark PMIDs.

Committed:
```text
1ff3f73 Add PubMed metadata enrichment tooling
```

Example command:
```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa" \
./.venv/bin/python scripts/enrich_metadata.py --from-json baseline_retrieval_v4.json
```

### 3. Added evaluation comparison helper
- Added `scripts/compare_eval.py` to compare two retrieval/judge/answer artifacts.
- It reports:
  - latency deltas
  - context group changes
  - PMID overlap
  - added/removed papers
  - rank moves
  - judge-score deltas when present

Committed:
```text
9a9a804 Add evaluation comparison helper
```

Example command:
```bash
./.venv/bin/python scripts/compare_eval.py \
  judged_retrieval_qwen3_v4.json \
  judged_retrieval_qwen3_v4_strict.json
```

### 4. Tightened the retrieval judge rubric
- Made `scripts/judge_retrieval.py` stricter:
  - `3` requires exact-question evidence.
  - Clinical/risk/outcome questions require human outcome evidence for a `3`.
  - Mechanistic/cell/animal papers for clinical questions are capped lower.
  - Survival/treatment evidence is distinguished from incidence/risk/prevention.
  - `answers_question=true` only allowed for relevance `3`.
- Added output normalization:
  - clamps relevance to `0–3`
  - normalizes evidence types
  - coerces `answers_question=false` for relevance `<3`
- Generated `judged_retrieval_qwen3_v4_strict.json`.

Committed:
```text
b09ee33 Tighten retrieval judge rubric
```

Strict judge comparison vs prior Qwen v4:
```text
metformin / cancer risk:              2.5 -> 2.2
statins / dementia:                   3.0 -> 2.8
vitamin D / respiratory infections:   2.8 -> 2.5
aspirin / primary CVD prevention:     3.0 -> 2.8
GLP-1 / CV outcomes:                  3.0 -> 3.0
```

### 5. Added and ran an expanded benchmark
- Added `benchmarks/expanded_questions.txt` with 13 total questions:
  - original 5 starter questions
  - beta blockers and mortality in heart failure
  - SGLT2 inhibitors kidney outcomes
  - omega-3 supplementation cardiovascular prevention
  - exercise and insulin sensitivity
  - ketogenic diet epilepsy adults
  - does aspirin reduce colorectal cancer risk?
  - mechanism of metformin AMPK activation
  - p53 mutation and cancer prognosis
- Generated retrieval and strict Qwen judge artifacts.

Committed:
```text
8e17e45 Add expanded retrieval benchmark
```

Artifacts:
- `baseline_retrieval_expanded_v2.json`
- `judged_retrieval_expanded_qwen3_strict_v2.json`

Initial expanded benchmark summary:
```text
Average retrieval latency: 11.35s
Average strict Qwen mean relevance: 2.48
Direct 3/3 count: 67 / 130
```

Clear failure case:
```text
p53 mutation and cancer prognosis
mean relevance: 1.6
Direct 3/3: 0/10
```

### 6. Fixed biomedical entity retrieval failures
Problem:
- Query `p53 mutation and cancer prognosis` degraded into generic `mutation/cancer/prognosis` retrieval because `_query_terms()` dropped short tokens like `p53`.

Fixes in `src/pubmedqa/retrieve.py`:
- Preserve short biomedical tokens such as `p53`, `il6`, `cd4`, etc.
- Added biomedical alias expansion/protection:
  - `p53` ⇄ `TP53`
  - initial aliases for `HER2/ERBB2`, `EGFR/ERBB1`, `PD1/PDCD1`, `PDL1/CD274`
- Added exact required entity matching.
- Added strict lexical anchoring for entity + endpoint concepts, e.g.:
  ```text
  (p53 OR tp53) AND (prognosis OR prognostic OR survival OR outcome OR mortality)
  ```
- Added `prognosis` / `prognostic` to clinical-query detection.
- Added title/entity/concept boosts.

Committed:
```text
6ca00b1 Protect biomedical entity queries in retrieval
```

Validated p53 fix:
```text
Before: mean relevance 1.6, direct 3/3 0/10
After:  mean relevance 2.8, direct 3/3 8/10
```

### 7. Reran expanded benchmark after entity fix
- Generated new preferred expanded benchmark artifacts:
  - `baseline_retrieval_expanded_entityfix_v1.json`
  - `judged_retrieval_expanded_entityfix_qwen3_strict_v1.json`

Committed:
```text
4d1ddef Add entity-fix expanded benchmark results
```

Comparison vs previous expanded benchmark:
```text
Old avg retrieval:       11.35s
New avg retrieval:       11.26s

Old avg mean relevance:  2.48
New avg mean relevance:  2.57

Old direct 3/3 count:    67 / 130
New direct 3/3 count:    75 / 130
```

No regressions on the other 12 questions. The improvement came from p53:
```text
p53 mutation and cancer prognosis:
mean relevance: 1.6 -> 2.8
direct 3/3:     0/10 -> 8/10
```

### 8. Generated expanded answer baseline
- Ran answer generation on the 13-question expanded/entity-fix benchmark.
- All generated answers passed citation validation.

Committed:
```text
b32b9fa Add expanded answer baseline
```

Artifact:
- `baseline_with_answers_expanded_entityfix_v1.json`

Summary:
```text
Questions:        13
Avg retrieval:    12.00s
Avg generation:   8.88s
Citation status:  all pass
Invalid PMIDs:    none
Warnings:         none
```

### 9. Added cited-paper summary workflow
- Added `src/pubmedqa/summarize.py`.
- Added CLI `scripts/summarize_citations.py`.
- The workflow can:
  - take explicit PMIDs
  - read PMIDs from file
  - read cited PMIDs or retrieved PMIDs from an eval/answer JSON
  - load papers from SQLite
  - optionally fetch missing PubMed records via efetch
  - generate an overall grounded summary with inline citations
  - validate cited PMIDs
- Improved citation extraction to handle grouped citations such as `[14758132, 25051299]`.

Committed:
```text
64b5296 Add cited-paper summary workflow
```

Examples:
```bash
./.venv/bin/python scripts/summarize_citations.py \
  --pmids 25806241 32592092 \
  --topic "metformin and cancer risk"

./.venv/bin/python scripts/summarize_citations.py \
  --from-json baseline_with_answers_expanded_entityfix_v1.json \
  --question "p53 mutation and cancer prognosis" \
  --use cited

./.venv/bin/python scripts/summarize_citations.py \
  --from-json baseline_with_answers_expanded_entityfix_v1.json \
  --question "p53 mutation and cancer prognosis" \
  --use retrieved
```

### 10. Made summaries more detailed
- Initial cited-paper summaries were too high-level.
- Updated summarizer prompt to require:
  - `## Paper-specific findings`
  - one bullet per PMID
  - specific paper result/finding
  - study design/population/endpoint when available
  - separate cross-paper synthesis

Committed:
```text
a8cd1aa Make cited-paper summaries more detailed
```

### 11. Increased LLM token budget
- Changed default `PUBMEDQA_LLM_MAX_TOKENS` from `600` to `2500`.
- Can still be overridden with environment variable.

Committed:
```text
d5f57ac Increase default LLM token budget
```

### 12. Constrained paper-specific bullets
- With larger token budget, the model sometimes repeated paper bullets.
- Updated the prompt to require exactly `N` paper-specific bullets, one per PMID checklist.

Committed:
```text
141be75 Constrain paper-specific summary bullets
```

### 13. Added map-reduce summary path for larger paper sets
- We tested top-20 summaries.
- Direct 20-paper summary had broader coverage but sometimes degraded into title-listing.
- Added a map-reduce path:
  1. Generate one compact evidence note per paper.
  2. Synthesize those notes into final summary.
- Added CLI flags:
  - `--map-reduce`
  - `--map-reduce-threshold` (default `12`)
- Summaries automatically use map-reduce when paper count is at least 12.

Committed:
```text
7fe9355 Add map-reduce summary path for larger paper sets
```

Example top-20 workflow:
```bash
printf 'p53 mutation and cancer prognosis\n' > /tmp/p53_question.txt

PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa" \
./.venv/bin/python scripts/evaluate_retrieval.py \
  --questions /tmp/p53_question.txt \
  --top 20 \
  --out p53_top20_entityfix.json

PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa" \
./.venv/bin/python scripts/summarize_citations.py \
  --from-json p53_top20_entityfix.json \
  --use retrieved \
  --map-reduce \
  --out p53_top20_summary.md
```

## Current best artifacts

### Retrieval / judge baselines
- `baseline_retrieval_v4.json`
- `judged_retrieval_qwen3_v4_strict.json`
- `baseline_retrieval_expanded_entityfix_v1.json`
- `judged_retrieval_expanded_entityfix_qwen3_strict_v1.json`

### Answer baseline
- `baseline_with_answers_v4.json`
- `baseline_with_answers_expanded_entityfix_v1.json`

### Paper/report
- `paper/pubmedqa_v4_baseline_icml2026.tex`
- `paper/pubmedqa_v4_baseline_icml2026.bib`
- `paper/pubmedqa_v4_baseline_icml2026.pdf`

### Key scripts
- `scripts/evaluate_retrieval.py`
- `scripts/judge_retrieval.py`
- `scripts/compare_eval.py`
- `scripts/enrich_metadata.py`
- `scripts/summarize_citations.py`
- `scripts/download_precomputed_embeddings.py`

### Key modules
- `src/pubmedqa/retrieve.py`
- `src/pubmedqa/generate.py`
- `src/pubmedqa/summarize.py`

## Latency measurements

### Expanded/entity-fix answer baseline
```text
Questions:        13
Avg retrieval:    12.00s
Avg generation:   8.88s
Citation status:  all pass
```

### p53 top-4 vs top-20 summary measurement
Measured on `p53 mutation and cancer prognosis`:

| Mode | Retrieval | End-to-end retrieval + summary | Approx summary time | Output size |
|---|---:|---:|---:|---:|
| Top 4 papers | 15.12s | 28.30s | ~13.18s | 491 words |
| Top 20 papers + map-reduce | 15.58s | 88.44s | ~72.86s | 1,735 words |

Takeaway:
```text
Retrieval top20 vs top4:  +0.46s
Summary top20 vs top4:   +59.68s
Total added latency:     +60.14s
```

The top-20 cost is almost entirely from map-reduce summarization, not retrieval.

## Important commands

Set data path:
```bash
export PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa"
```

Run expanded retrieval baseline:
```bash
./.venv/bin/python scripts/evaluate_retrieval.py \
  --questions benchmarks/expanded_questions.txt \
  --print-titles \
  --out baseline_retrieval_expanded_entityfix_v1.json
```

Run strict Qwen judge:
```bash
./.venv/bin/python scripts/judge_retrieval.py \
  --provider mlx \
  --model mlx-community/Qwen3-4B-4bit \
  --input baseline_retrieval_expanded_entityfix_v1.json \
  --out judged_retrieval_expanded_entityfix_qwen3_strict_v1.json \
  --fetch-pubmed
```

Run expanded answer baseline:
```bash
./.venv/bin/python scripts/evaluate_retrieval.py \
  --questions benchmarks/expanded_questions.txt \
  --with-llm \
  --out baseline_with_answers_expanded_entityfix_v1.json
```

Summarize cited papers from an answer JSON:
```bash
./.venv/bin/python scripts/summarize_citations.py \
  --from-json baseline_with_answers_expanded_entityfix_v1.json \
  --question "p53 mutation and cancer prognosis" \
  --use cited
```

Summarize retrieved top-20 papers with map-reduce:
```bash
printf 'p53 mutation and cancer prognosis\n' > /tmp/p53_question.txt

./.venv/bin/python scripts/evaluate_retrieval.py \
  --questions /tmp/p53_question.txt \
  --top 20 \
  --out p53_top20_entityfix.json

./.venv/bin/python scripts/summarize_citations.py \
  --from-json p53_top20_entityfix.json \
  --use retrieved \
  --map-reduce \
  --out p53_top20_summary.md
```

Compare eval files:
```bash
./.venv/bin/python scripts/compare_eval.py OLD.json NEW.json --titles 10
```

## Known issues / caveats

- `SESSION_SUMMARY_NEXT_STEPS.md` and `TODO_NEXT_STEPS.md` have remained untracked working/session notes.
- `python` may point to the wrong interpreter; use `./.venv/bin/python` explicitly.
- `urllib3` emits a LibreSSL warning under Python 3.9; it has not blocked current runs.
- OpenAI judge path exists but previously hit 429 quota/rate-limit errors; local MLX Qwen judge is preferred.
- Metadata is still incomplete for the full snapshot unless enriched via `scripts/enrich_metadata.py`.
- Map-reduce summaries are substantially slower for top-20 paper sets.
- The local LLM can still overgeneralize; paper-specific findings are better after prompt constraints, but manual spot checks remain important.

## Recommended next steps

### Priority 1 — integrate summary workflow into `p0_ask.py`
Expose second-pass summary directly in the user-facing CLI.

Suggested flags:
```bash
--second-pass-summary
--summary-source cited|retrieved
--map-reduce
--map-reduce-threshold 12
```

Target usage:
```bash
./.venv/bin/python scripts/p0_ask.py \
  --top 20 \
  --second-pass-summary \
  --summary-source retrieved \
  --map-reduce \
  "p53 mutation and cancer prognosis"
```

Behavior:
1. Retrieve top N papers.
2. Generate normal answer unless `--no-llm`.
3. Collect cited PMIDs or all retrieved PMIDs.
4. Run `pubmedqa.summarize` over those papers.
5. Print a deeper evidence synthesis.

### Priority 2 — benchmark summary modes
Run a small latency/quality comparison:
- top 10 normal answer
- top 10 retrieved summary
- top 20 retrieved summary with map-reduce
- cited-only summary

Track:
- retrieval time
- answer generation time
- summary generation time
- word count
- citation validation
- manual quality notes

### Priority 3 — improve summary factual precision
The map-reduce path is better, but next quality improvements could include:
- saving per-paper evidence notes to JSON for inspection/debugging
- requiring each evidence note to include `design`, `population/model`, `endpoint`, `main result`, `limitations` fields
- using JSON note extraction before final prose synthesis
- validating that every PMID appears exactly once in `Paper-specific findings`

### Priority 4 — broader metadata enrichment
Scale `scripts/enrich_metadata.py --missing` to enrich more of the local snapshot, not just benchmark PMIDs.

### Priority 5 — answer/manual review
Manually inspect `baseline_with_answers_expanded_entityfix_v1.json` for:
- overstatement of observational associations
- insufficient uncertainty language
- risk vs survival/treatment confusion
- mechanistic evidence being over-weighted for clinical questions

## Git status at time of summary

The useful code/artifacts above have been committed. Remaining untracked working notes:
```text
SESSION_SUMMARY_NEXT_STEPS.md
TODO_NEXT_STEPS.md
```
