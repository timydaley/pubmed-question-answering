# Paper Review — v1 Evidence Baseline Draft

Date: 2026-06-30

Reviewed files:

```text
paper/pubmedqa_v4_baseline_icml2026.tex
paper/pubmedqa_v4_baseline_icml2026.pdf
paper/README.md
```

Review basis:

- Fresh read of the current LaTeX source.
- Spot-check against current benchmark artifacts:
  - `judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json`
  - `baseline_with_answers_expanded_evidencebasis_v1.json`
- Current committed state after paper update commit `5b13365`.

## Executive summary

The paper is directionally good and now reflects the recent v1-oriented work much better than the older five-question v4 draft. The central reported metrics match the local benchmark artifacts I checked:

- 13 questions.
- 130 judged retrieved papers.
- 0 relevance-0 / irrelevant judged papers.
- 129 / 130 papers judged relevance >= 2.
- 76 / 130 papers judged relevance = 3.
- Average mean judged relevance = 2.577 / 3.
- Answer benchmark has 13 / 13 Evidence basis sections.
- Answer benchmark has 0 invalid cited-PMID rows.
- Average answer generation latency = 9.475s.

However, before wider sharing or treating this as a release paper, I recommend a small revision pass. The main issues are not metric correctness; they are framing, artifact availability, reproduction precision, and version/file naming clarity.

## Strengths

### 1. Metrics are mostly consistent with artifacts

Checked values from `judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json`:

```text
questions:                  13
avg judged retrieval time:  13.2246s
sum relevance >= 3:         76
sum relevance >= 2:         129
irrelevant_count total:     0
avg mean relevance:         2.5769
```

These match the paper's rounded claims:

```text
mean retrieval: 13.22s
Direct@10 total: 76/130
Rel@10 total: 129/130
zero Qwen-judged irrelevant papers
mean judged relevance: 2.577/3
```

Checked values from `baseline_with_answers_expanded_evidencebasis_v1.json`:

```text
questions:                 13
avg retrieval time:        14.3425s
avg generation time:       9.475s
invalid cited-PMID rows:   0
avg cited PMIDs:           4.0769
```

These match the answer table and summary.

### 2. The paper now covers the right current work

The updated paper correctly includes the important recent project changes:

- citation+recency retrieval scoring;
- clinical context balancing;
- Evidence basis answer prompt;
- answer comparison tooling;
- second-pass evidence summaries;
- build-integrity reporting;
- v1 release gates;
- targeted remaining limitations.

### 3. Limitations are appropriately cautious

The limitations section correctly notes:

- local judge is not expert review;
- judge can be generous;
- endpoint mismatches remain;
- population constraints remain;
- stale mechanistic papers can still surface;
- system uses abstracts/metadata, not full text.

This is important because the judge scores alone would otherwise sound stronger than the qualitative evidence supports.

## Issues to fix before broader sharing

### 1. Filename/version mismatch is still confusing

The content says:

```text
PubMedQA v1: Local Evidence-Aware Biomedical Question Answering over PubMed
```

but the files are still named:

```text
pubmedqa_v4_baseline_icml2026.tex
pubmedqa_v4_baseline_icml2026.pdf
pubmedqa_v4_baseline_icml2026.bib
```

`paper/README.md` explains that the filename is retained for continuity, but external readers will likely see the PDF filename before reading the README.

Recommendation: before publishing or sharing outside the repo, rename to something like:

```text
pubmedqa_v1_evidence_baseline_icml2026.tex
pubmedqa_v1_evidence_baseline_icml2026.pdf
pubmedqa_v1_evidence_baseline_icml2026.bib
```

or avoid version numbers in the filename:

```text
pubmedqa_local_evidence_baseline_icml2026.tex
```

### 2. Artifact availability statement may be inaccurate

The paper says:

> Full artifact filenames are recorded in the repository and release notes.

But the newest raw JSON artifacts are currently local/ignored rather than committed, including:

```text
baseline_retrieval_expanded_citationrecency_v1.json
baseline_with_answers_expanded_evidencebasis_v1.json
judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json
```

The comparison/review markdown files are committed, but the raw JSON artifacts are not tracked. This is fine if intentional, but the paper should be precise.

Recommended wording:

> Full artifact filenames and aggregate outputs are recorded in the repository; raw JSON benchmark artifacts may be regenerated with the commands below and are not necessarily committed because they are treated as generated outputs.

Alternatively, commit the raw v1 JSON artifacts if they are meant to be citable frozen baselines.

### 3. Reproduction commands are too abbreviated

The reproduction section now uses placeholders:

```text
python eval.py ...
python judge.py ...
python compare_answers.py ...
```

This avoids LaTeX line overflow but is not directly runnable. Since this is a methods/reproducibility section, it should either use exact runnable paths or explicitly label them as pseudocode.

Recommendation: use exact script paths but shorten variable names. Example:

```bash
Q=benchmarks/expanded_questions.txt
RET=baseline_retrieval_expanded_citationrecency_v1.json
JUD=judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json
ANS=baseline_with_answers_expanded_evidencebasis_v1.json

./.venv/bin/python scripts/evaluate_retrieval.py --questions $Q --out $RET
./.venv/bin/python scripts/judge_retrieval.py --input $RET --out $JUD --provider mlx --model mlx-community/Qwen3-4B-4bit
./.venv/bin/python scripts/evaluate_retrieval.py --questions $Q --with-llm --out $ANS
python3 scripts/compare_answers.py OLD_JSON $ANS
```

If LaTeX overflow recurs, move full commands to README or appendix and keep paper commands as summarized pseudocode.

### 4. The name `PubMedQA` may be ambiguous

The paper title says `PubMedQA v1`, but there is a known PubMedQA benchmark/dataset in the literature. This project appears to be a local PubMed question-answering system, not the canonical PubMedQA dataset.

Recommendation: clarify in the Purpose or title that this is the project name, not an evaluation on the standard PubMedQA dataset. Possible title:

```text
Local PubMedQA v1: Evidence-Aware Biomedical Question Answering over PubMed
```

or:

```text
A Local Evidence-Aware PubMed Question Answering Baseline
```

### 5. The phrase “passes the measured retrieval, answer, and latency gates” is correct but could be overread

The paper says:

> The current baseline passes the measured retrieval, answer, and latency gates.

This is accurate for measured gates, but build-integrity reporting was improved and not yet verified on a fresh small snapshot in this session.

Recommendation: add one sentence:

> Build-integrity gates remain to be validated on a fresh snapshot build using the updated report.

This aligns with the Next Steps section and avoids implying all v1 gates are complete.

### 6. The abstract is dense

The abstract is accurate but long and metric-heavy. It is acceptable for an internal report, but if shared externally, consider splitting or simplifying. Current abstract has many components in one sentence:

> MedCPT dense retrieval, SQLite FTS5 lexical retrieval, reciprocal-rank fusion, bounded evidence/citation/recency scoring, duplicate suppression, clinical-query-aware context balancing, local MLX generation, second-pass evidence summaries, and PMID citation validation.

Recommendation: keep if internal; simplify if external.

## Minor issues / polish

### 1. “Evidence-basis” capitalization varies

The paper uses both:

```text
Evidence basis
Evidence-basis
```

Recommendation: standardize to `Evidence basis` when referring to the generated answer section, and `evidence-basis prompt` only as an adjective if needed.

### 2. `Direct@10` and `Rel@10` labels could be clearer

The table caption explains them. Good. But `Direct@10` in the mean row shows `76/130`, which is a total rather than a mean. The row label says `Mean / total`, which is acceptable but slightly awkward.

Alternative row label:

```text
Mean / aggregate
```

### 3. The answer table uses retrieval times from a separate answer run

The paper notes elsewhere that retrieval times can differ between runs? The old paper did; the new one does not explicitly mention it. Because retrieval table average is 13.22s and answer table average retrieval is 14.34s, consider adding:

> Retrieval timings in the answer table come from a separate end-to-end answer-generation run and therefore differ slightly from the retrieval-only/judged run.

### 4. Release-gate thresholds could cite `V1_RELEASE_GATES.md`

The release gates section summarizes thresholds well. It might be useful to explicitly say the full checklist is in `V1_RELEASE_GATES.md`.

## Suggested revision checklist

Before the next commit, I would do the following:

1. Decide whether to rename the paper files from `v4` to `v1` or neutral naming.
2. Clarify raw artifact availability: committed vs generated/ignored.
3. Replace reproduction pseudocode with exact runnable script paths, or label it explicitly as pseudocode and point to README/release notes for exact commands.
4. Add a sentence that build-integrity gates still need fresh-snapshot validation.
5. Add a sentence explaining answer-table retrieval timings are from a separate run.
6. Standardize `Evidence basis` wording.
7. Optionally clarify that this is not an evaluation on the canonical PubMedQA dataset.

## Proposed patch-level text edits

### Artifact wording

Replace:

> The current key artifacts are the citation+recency retrieval baseline, the strict Qwen judged retrieval baseline, the Evidence-basis answer baseline, the citation/recency review note, and the v1 release-gate checklist. Full artifact filenames are recorded in the repository and release notes.

With:

> The current key outputs are the citation+recency retrieval baseline, the strict Qwen judged retrieval baseline, the Evidence basis answer baseline, the citation/recency review note, and the v1 release-gate checklist. Aggregate comparison reports and artifact filenames are committed in the repository; raw JSON benchmark outputs are generated artifacts and may be regenerated with the commands below.

### Answer timing note

After the answer table paragraph, add:

> Retrieval timings in Table 2 come from a separate end-to-end answer-generation run and therefore differ from the retrieval-only/judged run in Table 1.

### Build-integrity caveat

After:

> The current baseline passes the measured retrieval, answer, and latency gates.

Add:

> The updated build-integrity report still needs to be validated on a fresh snapshot build before all v1 gates can be considered complete.

### PubMedQA naming caveat

In Purpose, add:

> Here `PubMedQA` refers to this local project, not an evaluation on the canonical PubMedQA dataset.

## Overall recommendation

Do a small paper revision before pushing further. The benchmark values are sound, and the paper is suitable as an internal project report now. For external sharing, fix version/file naming, clarify generated artifact availability, and make reproduction commands exact or explicitly pseudocode.
