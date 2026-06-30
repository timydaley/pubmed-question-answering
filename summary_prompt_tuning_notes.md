# Summary/answer prompt tuning notes

Date: 2026-06-29

## Changes made

### `src/pubmedqa/generate.py`
- Added explicit cautious-language instruction for observational, retrospective, case-control, mechanistic, animal, and cell-line evidence.
- Added instruction not to imply causality unless randomized trial evidence supports it.
- Added instruction not to answer observational-association questions with an unqualified “yes”.
- Added instruction not to infer clinical benefit from mechanistic/cell/animal papers alone.

### `src/pubmedqa/summarize.py`
- Added the same cautious-language/causality guardrail to the summary system prompt.
- Tightened `Cross-paper synthesis` so it should be 1–3 concise comparative paragraphs rather than a second paper list.
- Tightened `Agreements and conflicts` so it should summarize the main agreements/conflicts in 3–6 bullets rather than repeat every paper-specific bullet.
- Added explicit residual-confounding language for observational associations.

## Validation

Ran Python compile checks:

```bash
./.venv/bin/python -m py_compile src/pubmedqa/generate.py src/pubmedqa/summarize.py
```

Ran metformin smoke test:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa" \
./.venv/bin/python scripts/p0_ask.py \
  --top 10 \
  --second-pass-summary \
  --summary-source cited \
  "does metformin reduce cancer risk?"
```

Observed timings:
- Retrieval: 12.77s
- Answer generation: 10.46s
- Second-pass summary: 12.76s

Observed quality improvement:
- Normal answer now starts with cautious wording: “The retrieved evidence suggests an association...” rather than an unqualified “Yes”.
- Uncertainty section explicitly says evidence is mostly observational/indirect and not proven.
- Second-pass summary mentions residual confounding and observational evidence.

Remaining issue:
- The normal answer cited all 10 retrieved PMIDs, so `--summary-source cited` summarized all 10. This is valid but reduces the distinction between cited-only and retrieved-only modes for broad prompts.
