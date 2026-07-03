# Evidence Selection v1 Review

Date: 2026-07-02

## Purpose

The goal was to change answer behavior, not patch simple string warnings. The new behavior is:

```text
retrieve broad candidate pool -> select curated evidence context -> generate answer
```

instead of:

```text
retrieve top 10 -> generate answer
```

## Implementation

Added:

```text
src/pubmedqa/evidence_select.py
```

Updated:

```text
scripts/p0_ask.py
scripts/evaluate_retrieval.py
scripts/compare_answers.py
```

New/updated CLI options:

```text
--retrieve-pool N        retrieve a broad pool before answer generation
--evidence-context N     number of selected evidence papers passed to the LLM
--no-evidence-select     disable selection and use raw top papers
--show-selected          p0_ask.py: show selected evidence papers and scores
```

Core selector behavior:

- infer question intent:
  - mechanism;
  - risk/prevention;
  - prognosis/survival;
  - clinical outcomes;
  - supplementation;
- score evidence tier:
  - meta-analysis/systematic review/RCT > cohort/case-control > review > mechanistic/editorial;
- score endpoint match;
- score required exposure/entity match;
- score population match;
- penalize mechanistic evidence for clinical outcome questions;
- preserve conflict/null evidence where possible;
- reduce near-duplicate titles;
- cap mechanistic papers for non-mechanistic clinical questions.

Important bug fixed during implementation:

- `compare_answers.py` originally treated only `row['papers']` as valid citation context.
- Evidence-selection answers may cite `selected_evidence_papers` drawn from ranks 11-30.
- The comparer now treats both `papers` and `selected_evidence_papers` as valid answer context.

## Benchmark command

Full-corpus evidence-selection answer benchmark:

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

Comparison:

```bash
python3 scripts/compare_answers.py \
  baseline_with_answers_full_allchunks_v1.json \
  baseline_with_answers_full_allchunks_evidselect_v2.json \
  --show-excerpts \
  --excerpt-chars 220 \
  > compare_answers_full_allchunks_to_evidselect_v2.md
```

## Aggregate results

| Metric | Full all-chunks baseline | Evidence selection v2 | Delta |
|---|---:|---:|---:|
| Questions | 13 | 13 | 0 |
| Avg retrieval latency | 6.98s | 7.41s | +0.42s |
| Avg generation latency | 10.64s | 10.99s | +0.35s |
| Citation warning rows | 0 | 0 | 0 |
| Invalid cited-PMID rows | 0 | 0 | 0 |
| Manual citation extraction mismatches | 0 | 0 | 0 |
| Rows with Evidence basis | 13 | 13 | 0 |
| Avg cited PMIDs | 3.92 | 5.08 | +1.15 |
| Avg selected evidence papers | n/a | 8.0 | n/a |

Interpretation: evidence selection increases retrieval/generation latency only modestly, keeps citation validation clean, and gives the LLM a broader curated evidence context.

## Behavior improvements observed

### Omega-3 / cardiovascular prevention

Before selection, the answer was cautious but based on fewer citations and the simple review flag complained about the phrase “cardiovascular causes.”

With evidence selection, the context explicitly includes both positive and negative/conflicting sources:

- positive/meta-analytic evidence:
  - `35187035`
  - `36103100`
  - `19609891`
  - `33092130`
- negative/conflicting evidence:
  - `22493407`
  - `32600510`
  - `33876607`

The generated answer now better frames mixed evidence by supplement type and population.

### Ketogenic diet / adult epilepsy

The first selector version admitted a pediatric-only systematic review. v2 adds stronger adult/population matching and rejects pediatric-title papers for adult questions.

The v2 answer removed the pediatric-only citation and cites more adult-relevant evidence, including:

- `25628734`
- `29217974`
- `32199222`
- `18358881`
- `24380692`

Remaining caveat: some mixed children/young-adult evidence still appears when adult-specific evidence is sparse.

### Metformin / cancer risk

The first selector version selected unrelated high-tier cancer/COVID and hepatocellular papers because it over-weighted evidence tier and endpoint words. v2 adds required exposure/entity matching and removes those unrelated papers.

The selected set now requires metformin exposure. However, the answer changed behavior: it emphasizes that retrieved evidence suggests lower lung-cancer risk but higher prostate-cancer risk. This may be useful conflict behavior, but it needs manual biomedical review because it can sound overly broad from a small selected context.

## Remaining issues

1. **Selector is still heuristic.** It improves context curation but can over-weight title/abstract wording and evidence tier.
2. **Metformin/cancer needs manual review.** The v2 answer may overemphasize prostate-cancer risk relative to the broader literature.
3. **Adult population handling is improved but not solved.** Mixed pediatric/young-adult ketogenic papers can still enter when adult evidence is sparse.
4. **Clinical/mechanistic separation is better but imperfect.** Exercise/insulin sensitivity still contains many mechanistic papers because the literature retrieved by the system is mixed.
5. **Full-corpus citation metadata is still missing.** Citation/RCR ranking is not active at full scale until bulk iCite ingestion is implemented.

## Recommendation

Keep evidence selection as an experimental answer-generation path and continue tuning it. It is a real behavioral improvement over raw top-10 context, especially for conflict preservation and endpoint/population filtering. Do not yet declare it the default v1 release behavior without manual review of the key edge cases.

Recommended next steps:

1. Manually review v2 answers for:
   - metformin/cancer risk;
   - omega-3/CVD prevention;
   - aspirin/CRC risk;
   - ketogenic diet adults;
   - exercise/insulin sensitivity;
   - p53 prognosis.
2. Consider making selected evidence visible by default in benchmark artifacts and optional in CLI output.
3. Add bulk iCite ingestion so selection/ranking can use full-corpus citation/RCR features.
4. Consider a lightweight learned or LLM-assisted evidence classifier after v1 if heuristic selection plateaus.
