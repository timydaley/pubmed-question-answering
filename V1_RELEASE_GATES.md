# v1 Release Gates

This checklist defines the minimum evidence needed to tag a v1-quality local PubMed QA snapshot.

## Required artifacts

- Retrieval baseline: `baseline_retrieval_expanded_citationrecency_v1.json`
- Judged retrieval baseline: `judged_retrieval_expanded_citationrecency_qwen3_strict_v1.json`
- Answer baseline: `baseline_with_answers_expanded_evidencebasis_v1.json`
- Answer comparison: `compare_answers_promptfix_to_evidencebasis_v1.md`
- Retrieval comparison: `compare_retrieval_entityfix_to_citationrecency_v1.md`
- Judged retrieval comparison: `compare_judged_entityfix_to_citationrecency_v1.md`
- Citation/recency review: `benchmark_citation_recency_v1_review.md`
- Build report: `${PUBMEDQA_DATA}/build_report.json`

## Build integrity gates

Pass if the build report has:

- `integrity_status == "pass"`, or only documented non-blocking warnings.
- SQLite paper rows equal unique PMIDs.
- LanceDB vector rows equal inserted vector rows.
- Inserted vector rows equal SQLite paper rows.
- Abstract coverage >= 95%.
- Citation coverage >= 95% when citation fetching is enabled.
- No unexpected duplicate PMIDs across ingested chunks.

Non-blocking exceptions may be allowed for known PubMed records with missing abstracts or missing iCite rows, but must be noted in the release notes.

## Retrieval quality gates

Pass if, on `benchmarks/expanded_questions.txt`:

- 13 / 13 questions return 10 results.
- No judged irrelevant papers in top 10, or any irrelevant paper has a documented rationale and planned fix.
- Total `relevance >= 2` papers is at least 125 / 130.
- Average mean judge relevance is at least 2.50.
- No regression greater than -0.10 mean judge relevance for any benchmark question versus the previous accepted baseline, unless manually accepted.
- Clinical questions preserve a majority clinical/review evidence mix where available.

Current citation+recency v1 status:

- Total `relevance >= 2`: 129 / 130 — pass.
- Average mean judge relevance: 2.577 — pass.
- Irrelevant papers: 0 — pass.

## Answer quality gates

Pass if, on the answer benchmark:

- 13 / 13 answers include an `Evidence basis` section.
- 0 citation validation warnings.
- 0 invalid cited-PMID rows.
- 0 manual citation extraction mismatches.
- Answers use cautious language for observational, retrospective, mechanistic, animal, and cell-line evidence.
- Answers distinguish incidence/prevention, survival after diagnosis, treatment response, surrogate outcomes, and mechanistic evidence where relevant.

Current evidence-basis v1 status:

- `Evidence basis` rows: 13 / 13 — pass.
- Citation warning rows: 0 — pass.
- Invalid cited-PMID rows: 0 — pass.
- Manual citation extraction mismatches: 0 — pass.

## Latency gates

For local development hardware, pass if:

- Average retrieval latency on the expanded benchmark is <= 20s.
- Average answer generation latency is <= 15s.
- Any single query above 30s is reviewed.

Current status:

- Citation+recency retrieval average: 13.22s — pass.
- Evidence-basis answer generation average: 9.47s — pass.

## Manual review gates

Before tagging v1, manually spot-check at least these known edge cases:

- Metformin/cancer: must not claim causal cancer prevention from observational/mechanistic evidence.
- Aspirin/CRC: must distinguish primary prevention/incidence from post-diagnosis survival.
- Aspirin/CVD primary prevention: must qualify by guideline context, age/risk, and bleeding risk.
- Exercise/insulin sensitivity: must separate human evidence from animal/mechanistic evidence.
- p53/prognosis: must emphasize context dependence by cancer type, mutation type, and treatment setting.

## v1 decision rule

Tag v1 only when all blocking gates pass and any warnings are documented in a short release note. Prefer targeted fixes over broad enrichment after this point.
