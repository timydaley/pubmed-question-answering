# Clinical Management Retrieval/Selection Plan

Date: 2026-07-03

## Problem

The system can over-focus on papers that literally match a broad clinical question while missing the clinically central evidence needed to answer it. The `vomiting during chemotherapy` example exposed the issue: retrieved/selected evidence over-emphasized non-pharmacologic adjuncts such as massage, acupressure, expectancy, behavioral interventions, and ginger, instead of first surfacing standard antiemetic prevention/treatment evidence.

This should be treated as a general retrieval/selection problem, not a one-off CINV issue.

## Goal

For broad clinical management questions, the system should prioritize the most central evidence-supported management options, including guideline/review/RCT evidence and standard-of-care therapies, while still allowing adjunctive or non-pharmacologic evidence when relevant.

The system should be truth-seeking and evidence-weighted, not artificially balanced. If the strongest evidence supports a clear conclusion, the answer should say so plainly.

---

## 1. Add clinical-management intent detection

Add a new intent such as:

```text
clinical_management
```

Detect queries involving treatment, prevention, management, symptom control, or what-to-do questions.

Example trigger terms:

```text
treatment
treat
therapy
management
manage
prevention
prevent
control
what helps
what should be used
first line
standard of care
medication
drug
symptom
nausea
vomiting
pain
insomnia
hypertension
migraine
```

Examples that should trigger this mode:

```text
vomiting during chemotherapy
treatment for migraine
management of hypertension
back pain treatment
insomnia treatment
diabetic neuropathy pain
nausea during pregnancy
```

Do not trigger it for purely mechanistic, prognosis, risk-association, or biomarker questions unless management terms are present.

---

## 2. Add query expansion for clinical-management questions

For broad management questions, retrieve with both the original query and a conservative expanded query.

Generic expansion terms:

```text
treatment
management
guideline
clinical practice guideline
standard of care
first line
therapy
prevention
pharmacologic
drug therapy
randomized trial
systematic review
meta-analysis
```

The expansion should be conservative and transparent. Store the actual retrieval query in artifacts as:

```json
"retrieval_question": "..."
```

### Local synonym expansion

Add small curated synonym maps for common clinical concepts where literal wording is insufficient.

Example:

```text
vomiting during chemotherapy
-> chemotherapy-induced nausea and vomiting
-> CINV
-> antiemetic
```

Future options:

- MeSH-based local expansion;
- PubMed co-occurrence-based synonym extraction;
- local LLM query rewriting;
- curated maps for common family-use queries.

---

## 3. Classify evidence/intervention type

Each candidate paper should get lightweight heuristic tags such as:

```text
pharmacologic
procedure_or_surgery
behavioral_or_psychological
physical_therapy_or_rehab
diet_or_supplement
complementary_or_alternative
device
diagnostic
risk_factor
mechanistic
guideline_or_consensus
systematic_review_or_meta_analysis
randomized_trial
observational
```

This should live in the evidence-selection layer and be recorded in each selected paper's `evidence_selection` metadata.

Example metadata:

```json
"intervention_tags": ["pharmacologic", "guideline_or_consensus"],
"management_centrality_score": 2.5
```

---

## 4. Add management centrality scoring

For clinical-management questions, add a centrality score that estimates whether a paper addresses core management rather than niche adjuncts.

Boost:

- clinical practice guidelines;
- consensus recommendations;
- standard-of-care reviews;
- pharmacotherapy reviews for medication-centered conditions;
- RCTs/meta-analyses of established first-line therapies;
- papers explicitly about treatment/prevention/management of the condition.

Down-rank or cap when query is broad:

- complementary/alternative therapies;
- massage/acupressure/acupuncture/music/hypnosis/expectancy-only papers;
- supplements/diet-only papers;
- small pilot studies;
- mechanistic/animal/cell-line studies;
- narrow subgroup papers unless the query asks for that subgroup.

Important: this does **not** mean pharmacologic evidence is always preferred. It means broad management questions should start with the clinically central evidence base. For conditions where behavioral, rehab, dietary, procedural, or non-pharmacologic care is standard-of-care, those should score as central.

---

## 5. Cap adjunctive evidence for broad management questions

For broad management questions, selected context should not be dominated by adjunctive interventions unless the user explicitly asks for them.

Suggested default selection policy:

```text
- reserve most slots for central/guideline/RCT/review evidence;
- allow 0-2 adjunctive/complementary/supplement papers depending on evidence strength;
- include adjunctive evidence if it is unusually strong or if it directly answers the question;
- include more adjunctive evidence only if the query explicitly asks about it.
```

Example:

```text
vomiting during chemotherapy
```

should prioritize antiemetic prevention/treatment and guidelines, with ginger/acupressure/massage only secondary if included.

```text
acupressure for vomiting during chemotherapy
```

should prioritize acupressure evidence.

---

## 6. Improve answer prompting for management questions

For clinical-management questions, the answer prompt should instruct the LLM to structure the answer as:

1. core standard-care / most evidence-supported management;
2. when evidence applies, first-line vs adjunctive options;
3. evidence strength and population/context;
4. adjunctive/non-pharmacologic options after core therapy;
5. uncertainty/conflicts.

Suggested prompt rule:

```text
For broad clinical management questions, first summarize standard-of-care or most evidence-supported management. Mention adjunctive, complementary, behavioral, dietary, or non-pharmacologic interventions only after core therapies, and do not let them dominate unless the question asks about them.
```

Keep existing requirements:

- grounded only in retrieved abstracts;
- inline `[PMID]` citations;
- no fake neutrality;
- caveats only when warranted by evidence.

---

## 7. Benchmark new failure-mode questions

Add a benchmark file, e.g.:

```text
benchmarks/clinical_management_questions.txt
```

Initial questions:

```text
vomiting during chemotherapy
nausea during pregnancy
treatment for migraine
management of hypertension
back pain treatment
insomnia treatment
depression treatment
diabetic neuropathy pain
treatment for atrial fibrillation
management of chronic kidney disease
treatment for rheumatoid arthritis
prevention of recurrent kidney stones
```

Evaluate:

- whether selected evidence includes central management/guideline evidence;
- whether adjunctive therapies dominate incorrectly;
- whether answer structure starts with the most evidence-supported core management;
- citation validity;
- latency impact of query expansion.

---

## 8. Implementation phases

### Phase A — Generalize current CINV-specific fix

Deliverables:

- add `clinical_management` intent;
- add generic management query expansion;
- keep CINV synonym expansion as one local map entry, not hard-coded unique behavior;
- record `retrieval_question` in CLI/web/eval artifacts.

### Phase B — Evidence/intervention tagging

Deliverables:

- add `intervention_tags` to evidence-selection metadata;
- add heuristic classifiers for pharmacologic, guideline, adjunctive, supplement, behavioral, procedure, rehab, mechanistic, etc.;
- add tests/smoke outputs for representative papers.

### Phase C — Management centrality scoring

Deliverables:

- add `management_centrality_score`;
- integrate into `score_paper` only for management-intent questions;
- cap adjunctive evidence for broad management queries;
- preserve explicit user intent for adjunctive queries.

### Phase D — Prompt and web/CLI behavior

Deliverables:

- add management-specific prompt rule;
- optionally show retrieval query and intervention tags in debug/selected evidence output;
- ensure web app exposes selected evidence metadata cleanly.

### Phase E — Evaluation

Deliverables:

- add `benchmarks/clinical_management_questions.txt`;
- run retrieval + answer benchmark;
- manually review centrality failures;
- compare against current full snapshot benchmark.

---

## 9. Acceptance criteria

Before making this default behavior, require:

- broad management questions are not dominated by niche adjunctive evidence;
- explicit adjunctive questions still retrieve the requested adjunctive evidence;
- citation validity remains clean;
- no large latency regression;
- at least manual spot-check pass on the clinical-management benchmark.

Example expected behavior:

```text
vomiting during chemotherapy
```

Answer should primarily discuss antiemetic prevention/treatment evidence and guideline-like management, not foot massage/acupressure/ginger as the main answer.

```text
ginger for vomiting during chemotherapy
```

Answer should focus on ginger evidence and its limitations.

---

## 10. Design principle

Do not optimize for artificial balance. Optimize for:

1. relevance to the user question;
2. clinical centrality when the question is broad management;
3. evidence strength;
4. truthful synthesis;
5. citation-grounded answers.
