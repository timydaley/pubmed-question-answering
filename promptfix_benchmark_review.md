# Benchmark Review — Updated Prompt Behavior

Artifacts compared:

- Previous baseline: `baseline_with_answers_expanded_entityfix_v1.json`
- Updated prompt baseline: `baseline_with_answers_expanded_promptfix_v1.json`

Benchmark command:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa" \
./.venv/bin/python scripts/evaluate_retrieval.py \
  --questions benchmarks/expanded_questions.txt \
  --with-llm \
  --out baseline_with_answers_expanded_promptfix_v1.json
```

Run date: 2026-06-29

## Executive summary

The updated prompt behavior is an improvement. The new baseline preserves citation validity while producing more cautious language for observational/associational questions.

Most important improvement:

- Metformin/cancer changed from an unqualified-ish “Yes, metformin may reduce cancer risk” to “The retrieved evidence suggests an association between metformin use and reduced cancer risk.”

Citation status also looks cleaner in the regenerated artifact: manual regex extraction of all answer citations matched `citation_status.cited_pmids` for every question, and no cited PMID was outside the retrieved set.

Remaining issues are mostly refinement-level:

- Some answers still use broad wording where guideline-/population-specific wording would be safer.
- Some answers cite many/all retrieved papers, making cited-only summaries less selective.
- Endpoint distinction is improved but still imperfect for aspirin/CRC, SGLT2 kidney outcomes, and p53 prognosis.

## Aggregate metrics

| Metric | Previous baseline | Updated prompt baseline |
|---|---:|---:|
| Questions | 13 | 13 |
| Avg retrieval latency | 12.00s | 10.97s |
| Avg generation latency | 8.88s | 9.68s |
| Citation warning rows | 0 | 0 |
| Invalid cited-PMID rows | 0 | 0 |
| Manual citation extraction mismatch | several rows | 0 rows |

Retrieval latency differences are likely normal run-to-run variation; retrieval code was not changed for this benchmark. Generation is slightly slower, plausibly because the updated prompt asks for more cautious evidence qualification.

## Per-question timing table

| Question | Old retrieval | New retrieval | Old gen | New gen | New cited PMIDs |
|---|---:|---:|---:|---:|---:|
| does metformin reduce cancer risk? | 13.25s | 12.73s | 7.36s | 10.60s | 10 |
| statins and risk of dementia | 5.65s | 6.92s | 9.97s | 12.20s | 8 |
| vitamin D supplementation and respiratory infections | 10.91s | 11.93s | 7.21s | 8.58s | 4 |
| aspirin for primary prevention cardiovascular disease | 19.05s | 17.99s | 6.27s | 7.02s | 8 |
| GLP-1 agonists and cardiovascular outcomes | 12.86s | 15.88s | 9.51s | 8.85s | 4 |
| beta blockers and mortality in heart failure | 12.31s | 13.82s | 7.20s | 7.61s | 4 |
| SGLT2 inhibitors kidney outcomes | 12.52s | 8.85s | 9.60s | 8.39s | 4 |
| omega-3 supplementation cardiovascular prevention | 12.01s | 8.79s | 9.87s | 10.15s | 8 |
| exercise and insulin sensitivity | 11.59s | 9.09s | 9.73s | 11.34s | 8 |
| ketogenic diet epilepsy adults | 8.96s | 6.56s | 8.24s | 7.68s | 3 |
| does aspirin reduce colorectal cancer risk? | 10.13s | 9.00s | 10.45s | 11.24s | 7 |
| mechanism of metformin AMPK activation | 15.37s | 10.93s | 9.23s | 11.58s | 5 |
| p53 mutation and cancer prognosis | 11.44s | 10.05s | 10.84s | 10.58s | 6 |

## Qualitative spot check

### Metformin and cancer risk

Improved. The new answer uses cautious association language and explicitly says the evidence is mostly observational and indirect. This directly addresses the largest issue in the previous review.

Remaining caveat: the answer now cites all 10 retrieved papers, including mechanistic/cell-line papers. This is valid, but it makes `--summary-source cited` less selective.

### Aspirin for primary prevention cardiovascular disease

Mostly good but still slightly overgeneralized. It says aspirin is “no longer recommended” for primary prevention. This should ideally be qualified by age, cardiovascular risk, bleeding risk, and guideline context.

Suggested future wording: routine aspirin for primary prevention is generally discouraged for many adults because bleeding risk often offsets modest benefit, but individualized use may remain appropriate in selected higher-risk, low-bleeding-risk adults.

### Exercise and insulin sensitivity

Improved caution. The short answer says exercise is “associated with improved insulin sensitivity,” and the uncertainty section notes small sample sizes and mechanistic uncertainty.

Remaining issue: the evidence summary still blends human, mouse/rat, and mechanistic vascular evidence in one paragraph. Future prompt should require explicit human vs animal/mechanistic separation.

### Aspirin and colorectal cancer risk

Improved causal caution. The short answer now says association rather than definitive reduction.

Remaining issue: endpoint mixing persists. The answer includes post-diagnosis mortality/survival studies in a risk/prevention answer. Future retrieval or prompt logic should distinguish prevention/incidence from post-diagnosis survival.

### p53 mutation and cancer prognosis

Generally good. The answer correctly says prognosis is complex and context-dependent.

Remaining issue: it includes a therapy/mechanistic CLL paper as a key paper and omits some stronger prognostic/meta-analytic evidence from broader top-20 retrieval runs. This is more of a retrieval/context-selection issue than a prompt issue.

## Citation validation check

Manual extraction of all bracketed numeric citations from the updated answer text found:

- every cited PMID is in the retrieved set
- `citation_status.cited_pmids` matches manual extraction for every row
- no citation-validation warnings

This resolves the earlier concern that `citation_status.cited_pmids` was under-reporting citations in the old artifact. The old mismatch was likely from an older citation extraction path or older generated artifact.

## Recommendation

Treat `baseline_with_answers_expanded_promptfix_v1.json` as the preferred answer baseline, replacing `baseline_with_answers_expanded_entityfix_v1.json` for future answer-quality comparisons.

Before committing/publishing, consider one more small prompt tweak:

- Require an explicit `Evidence basis:` line in each answer, e.g. “mostly observational cohorts/meta-analyses,” “randomized outcome trials,” or “mechanistic/cell-line evidence.”

But this is not blocking. The updated baseline is good enough to freeze as the current answer baseline.
