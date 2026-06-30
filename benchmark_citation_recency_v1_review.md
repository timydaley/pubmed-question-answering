# Citation + Recency Retrieval Review — v1

Artifacts compared:

- Previous retrieval baseline: `baseline_retrieval_expanded_entityfix_v1.json`
- New retrieval baseline: `baseline_retrieval_expanded_citationrecency_v1.json`
- Previous judged baseline: `judged_retrieval_expanded_entityfix_qwen3_strict_v1.json`
- New judged baseline: `judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json`

Comparison reports:

- `compare_retrieval_entityfix_to_citationrecency_v1.md`
- `compare_judged_entityfix_to_citationrecency_v1.md`

Run date: 2026-06-30

## Executive summary

Citation + recency scoring produced mostly stable retrieval sets with small rank movements and limited top-10 membership changes.

Judge metrics were essentially unchanged, with a tiny aggregate improvement:

| Metric | Previous | Citation+recency v1 | Delta |
|---|---:|---:|---:|
| Questions | 13 | 13 | 0 |
| Avg retrieval latency | 11.26s | 13.22s | +1.96s |
| Avg mean judge relevance | 2.569 | 2.577 | +0.008 |
| Total relevance >= 3 papers | 75 / 130 | 76 / 130 | +1 |
| Total relevance >= 2 papers | 129 / 130 | 129 / 130 | 0 |
| Irrelevant papers | 0 | 0 | 0 |
| Avg PMID-set Jaccard overlap | 0.909 | n/a | n/a |
| Questions with changed top-10 membership | 4 / 13 | n/a | n/a |

Interpretation: the scorer is safe enough to keep as the current retrieval baseline, but the quality gain is modest on this small benchmark. The main cost is a retrieval-latency increase of about 2 seconds per query in this run.

## Membership changes

Only four questions changed top-10 membership:

| Question | Kept | Added | Removed |
|---|---:|---|---|
| SGLT2 inhibitors kidney outcomes | 8 / 10 | `7205941`, `34991813` | `2574643`, `26046414` |
| beta blockers and mortality in heart failure | 8 / 10 | `12846268`, `34180244` | `11060685`, `12505115` |
| ketogenic diet epilepsy adults | 9 / 10 | `26000218` | `29516456` |
| vitamin D supplementation and respiratory infections | 8 / 10 | `35507293`, `36857810` | `25476069`, `34537990` |

All other questions preserved the same top-10 set, with rank-only changes.

## Notable positives

- No judged irrelevant papers were introduced.
- SGLT2 kidney outcomes improved slightly by mean judge relevance: 2.6 -> 2.7.
- Total relevance>=3 count improved by one paper across the 130 judged papers.
- Most changes were rank movements rather than set churn.
- The clinical/review vs mechanistic/other group balance remained stable for every question.

## Review concerns

- Retrieval latency increased from 11.26s to 13.22s on average. This may be run-to-run variation plus added scoring overhead, but should be watched.
- Some added papers look questionable despite nonzero judge scores, especially old/mechanistic or non-adult papers:
  - `7205941` for SGLT2 kidney outcomes is a 1980 cultured epithelial-cell sugar transport paper.
  - `26000218` for adult ketogenic diet epilepsy appears to be a childhood absence epilepsy case.
- The judge can be generous for reviews/editorials and should remain a comparative signal, not the only release gate.

## Recommendation

Keep `baseline_retrieval_expanded_citationrecency_v1.json` and `judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json` as the current citation+recency baseline.

Before v1 release, consider targeted tuning rather than broad enrichment:

1. Add/strengthen endpoint and population filters for questions with obvious age/population constraints.
2. Add a stale mechanistic penalty for clinical outcome questions when a paper is old and has weak title/abstract endpoint match.
3. Track retrieval latency in build/eval reports.
4. Use answer-level review plus citation validation as final quality gates, since judge relevance alone is not enough.
