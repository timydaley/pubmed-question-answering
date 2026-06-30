# Manual Review — Expanded Entity-Fix Answer Baseline

Reviewed artifact: `baseline_with_answers_expanded_entityfix_v1.json`  
Review date: 2026-06-29  
Questions reviewed: 13

## Executive summary

The expanded answer baseline is useful and generally grounded: all 13 answers have no recorded invalid PMID citations, and most answers retrieve relevant evidence. The main problems are **answer calibration**, not citation hallucination.

Key findings:

1. **Citation validity is good.** No answer had invalid cited PMIDs relative to retrieved papers.
2. **Several answers are too confident for observational evidence.** This is most visible for metformin/cancer, aspirin/CRC prevention, exercise/insulin sensitivity, ketogenic diet/adult epilepsy, and SGLT2 kidney outcomes.
3. **Some answers conflate related but distinct endpoints.** Examples: cancer risk vs cancer survival; primary prevention vs secondary prevention; kidney outcomes vs heart-failure outcomes.
4. **Mechanistic/cell/animal evidence is sometimes mixed into clinical conclusions.** This is most relevant for metformin/cancer and exercise/insulin sensitivity.
5. **The artifact predates the prompt-caution fixes.** The current prompt changes should improve several issues, especially unqualified “yes” answers and causal wording.
6. **`citation_status.cited_pmids` appears incomplete for some rows.** Manual regex extraction found additional cited PMIDs in answers that were retrieved and valid, but not listed in `citation_status.cited_pmids`. This looks like a reporting/extraction issue rather than a hallucination issue.

## Overall metrics from review

| Check | Result |
|---|---:|
| Questions reviewed | 13 |
| Answers with citation-validation warning | 0 / 13 |
| Answers with invalid cited PMIDs by manual extraction | 0 / 13 |
| Answers needing wording/calibration improvement | ~8 / 13 |
| Answers with endpoint-confusion risk | ~5 / 13 |
| Answers with mechanistic evidence over-weighting risk | ~3 / 13 |

## Cross-cutting recommendations

### Prompt / generation

Already partially addressed by the recent prompt changes:

- Avoid unqualified “yes” for observational association questions.
- Say “associated with” rather than “reduces” unless RCT evidence supports causality.
- Explicitly separate:
  - risk/incidence
  - mortality/survival after diagnosis
  - surrogate/mechanistic outcomes
  - treatment/prevention outcomes
- Do not infer clinical benefit from cell-line, animal, or mechanistic studies alone.

Additional recommended prompt improvement:

- Require the answer to include a one-line `Evidence type:` or `Evidence basis:` statement, e.g.:
  - “Mostly meta-analyses of observational studies.”
  - “Randomized cardiovascular outcome trials.”
  - “Mechanistic/cell-line evidence; not direct clinical outcome evidence.”

### Evaluation/reporting

- Fix or re-check `citation_status.cited_pmids` extraction because it under-reports citations in several answers.
- Add an endpoint-consistency check to manual review templates.
- Add a manual `claim_supported`/`overstated` score for each answer.

### Retrieval

- Most retrieval sets are relevant.
- Some questions include papers that are adjacent but not exactly targeted:
  - aspirin CRC risk includes post-diagnosis survival papers.
  - omega-3 cardiovascular prevention includes secondary-prevention papers.
  - SGLT2 kidney outcomes includes mechanistic/older sugar-transport papers.

## Per-question review

### 1. does metformin reduce cancer risk?

**Verdict:** Needs calibration.  
**Citation validity:** Pass.  
**Main issue:** Too strong / mixes cancer incidence, survival, and mechanistic evidence.

The answer starts with “Yes, metformin may reduce cancer risk.” The safer phrasing is: “The retrieved evidence suggests an association between metformin use and lower incidence or better outcomes in some cancers, but much of it is observational and cancer-type-specific.”

Issues:

- Combines cancer risk reduction with improved survival after diagnosis.
- Mentions mechanistic studies in uncertainty, but the bottom line still sounds broadly preventive.
- Should more clearly distinguish diabetic populations from general populations.

Recent prompt fix should improve this; the metformin smoke test after prompt tuning already produced better wording.

---

### 2. statins and risk of dementia

**Verdict:** Good.  
**Citation validity:** Pass.  
**Main issue:** Minor duplication in key papers.

Strengths:

- Correctly emphasizes complexity and observational evidence.
- Notes mixed results and confounding.
- Avoids a definitive causal claim.

Issues:

- Repeats PMID `37291702` as two separate key bullets.
- Could cite the systematic review `20100290` more prominently because it is high-level evidence and appears in retrieved papers.

---

### 3. vitamin D supplementation and respiratory infections

**Verdict:** Good.  
**Citation validity:** Pass.  
**Main issue:** Some claims cite news/commentary-style retrieved records.

Strengths:

- Balanced answer: “may have a protective effect,” “not conclusive.”
- Separates observational associations from trial results.
- Identifies subgroup effect in COPD patients with low baseline vitamin D.

Issues:

- Some cited PMIDs appear to be short reports/commentary rather than primary trials or meta-analyses.
- Should make clearer that effects may depend on baseline vitamin D deficiency, dosing schedule, age, and population.

---

### 4. aspirin for primary prevention cardiovascular disease

**Verdict:** Mostly good, but overgeneralized.  
**Citation validity:** Pass.  
**Main issue:** “No longer recommended” is too broad without age/risk qualifiers.

Strengths:

- Correctly identifies reduced enthusiasm for aspirin in primary prevention.
- Notes bleeding-risk tradeoff and individualization.

Issues:

- “Aspirin is no longer recommended for primary prevention” should be qualified by age, ASCVD risk, bleeding risk, and guideline context.
- Some cited papers are reviews/commentaries rather than trials.
- Better bottom line: “Routine aspirin for primary prevention is generally discouraged for many adults because bleeding risk often offsets modest cardiovascular benefit; individualized use may remain appropriate for selected higher-risk, low-bleeding-risk adults.”

---

### 5. GLP-1 agonists and cardiovascular outcomes

**Verdict:** Good, with minor repetition/truncation.  
**Citation validity:** Pass.  
**Main issue:** Answer appears cut off near the end of the uncertainty section.

Strengths:

- Retrieves strong meta-analyses and cardiovascular outcome trial syntheses.
- Quantitative estimates are useful.
- Clinical endpoint is well matched.

Issues:

- Evidence summary repeats similar HR estimates across overlapping meta-analyses.
- The answer appears truncated at “patients with type...”, likely token/output issue.
- Should mention population: mainly type 2 diabetes / high cardiovascular risk, not all patients.

---

### 6. beta blockers and mortality in heart failure

**Verdict:** Good.  
**Citation validity:** Pass.  
**Main issue:** Should qualify heart-failure phenotype.

Strengths:

- Correctly identifies mortality benefit in heart failure.
- Quantifies approximate benefit.
- Mentions older adults and uncertainty around very old patients.

Issues:

- Should specify strongest evidence is for heart failure with reduced ejection fraction / systolic heart failure.
- “Routine therapy for NYHA II-IV” may be too prescriptive for a QA tool unless framed as evidence/guideline context.

---

### 7. SGLT2 inhibitors kidney outcomes

**Verdict:** Mostly good, needs endpoint precision.  
**Citation validity:** Pass.  
**Main issue:** Mixes kidney endpoints and hospitalization for heart failure.

Strengths:

- Correctly reports kidney-protective pattern from RCT/meta-analysis evidence.
- Mentions eGFR slope and kidney composite outcomes.

Issues:

- Short answer includes hospitalization for heart failure as a “kidney-related outcome”; it is cardiovascular/cardiorenal, not kidney-specific.
- Retrieved set contains some less relevant mechanistic/old sugar-transport papers.
- Should distinguish diabetic CKD, advanced CKD, and broader type 2 diabetes populations.

---

### 8. omega-3 supplementation cardiovascular prevention

**Verdict:** Good but retrieval/endpoint mix is imperfect.  
**Citation validity:** Pass.  
**Main issue:** Prevention type is mixed; some evidence is secondary prevention.

Strengths:

- Appropriately says mixed/inconclusive.
- Notes disagreement among meta-analyses.
- Does not overstate benefit.

Issues:

- Query asks cardiovascular prevention, but retrieved set includes secondary-prevention evidence and comparative statin/network meta-analyses.
- Should distinguish general omega-3 supplementation from prescription EPA formulations and dose differences.
- “Further studies are needed” is generic; better to say effects likely vary by formulation, dose, baseline risk, and endpoint.

---

### 9. exercise and insulin sensitivity

**Verdict:** Needs calibration.  
**Citation validity:** Pass.  
**Main issue:** Strong causal wording despite mixed human/mechanistic evidence.

Strengths:

- Correctly identifies exercise as generally improving insulin sensitivity.
- Notes mechanisms are incompletely understood.

Issues:

- “Exercise improves insulin sensitivity” is probably true, but the evidence set includes obese men, T2DM meta-analysis, mice, rats, and vascular/mechanistic studies. The answer should separate direct human evidence from animal/mechanistic evidence.
- “Sprint interval exercise is more effective than continuous exercise” may be too broad if based on a limited study/population.
- Mechanistic factors like HISS and angiotensin-(1-7) should not be presented as established general mechanisms.

---

### 10. ketogenic diet epilepsy adults

**Verdict:** Mostly good, but too positive.  
**Citation validity:** Pass.  
**Main issue:** “Shown to be effective” and “similar to children” should be softened.

Strengths:

- Retrieves adult-relevant meta-analysis/studies.
- Notes lack of Class 1 studies.
- Notes special caution for coexisting type 1 diabetes.

Issues:

- “Response rate similar to children” may be overconfident.
- Should mention tolerability/adherence more prominently; adult ketogenic diet efficacy is tightly linked to compliance.
- Better phrasing: “may help some adults with drug-resistant epilepsy, but evidence quality and adherence limitations remain important.”

---

### 11. does aspirin reduce colorectal cancer risk?

**Verdict:** Needs endpoint precision.  
**Citation validity:** Pass.  
**Main issue:** Mixes CRC prevention/incidence with post-diagnosis survival.

Strengths:

- Correctly gives a cautious answer.
- Notes inconsistent evidence and age-related caution.

Issues:

- The question is risk reduction/prevention, but the evidence summary includes post-diagnosis mortality/survival studies.
- The 1994 review includes epidemiologic studies and an older randomized trial; this should be contextualized as old evidence.
- Should distinguish primary prevention/adenoma recurrence/CRC incidence/post-diagnosis survival.

---

### 12. mechanism of metformin AMPK activation

**Verdict:** Good for mechanistic question.  
**Citation validity:** Pass.  
**Main issue:** Could better identify cell/model context.

Strengths:

- Mechanistic evidence is appropriate for this question.
- Identifies multiple candidate pathways and uncertainty.

Issues:

- Should specify which findings are in vivo vs hepatocytes vs skeletal muscle cells vs adipocytes vs cancer cells.
- The c-Src/PI3K pathway is mentioned in the short answer but not clearly tied to a key cited paper in the answer.
- Should avoid implying one unified mechanism across all tissues.

---

### 13. p53 mutation and cancer prognosis

**Verdict:** Good.  
**Citation validity:** Pass.  
**Main issue:** Some key retrieved high-value papers not cited.

Strengths:

- Correctly says prognostic value is cancer-type- and mutation-type-dependent.
- Notes conflicting evidence.
- Avoids overgeneralizing p53/TP53 mutation as uniformly poor prognosis.

Issues:

- Retrieved top paper `22551440` is highly relevant but not cited in the generated answer.
- `31924585` is more therapeutic/mechanistic in CLL and less directly prognostic; it may not belong in key papers for this question.
- Should cite meta-analytic/systematic evidence where available, e.g. hepatocellular carcinoma or osteosarcoma meta-analysis in expanded top-20 runs.

## Priority fixes before next baseline regeneration

1. **Regenerate answer baseline with current prompt fixes.**  
   Suggested artifact name: `baseline_with_answers_expanded_promptfix_v1.json`.

2. **Fix citation-status extraction/reporting.**  
   Ensure `citation_status.cited_pmids` equals the actual set of PMIDs extracted from answer text, including grouped citations and citations in all sections.

3. **Add endpoint-specific instructions to prompt.**  
   The model should explicitly distinguish risk/incidence, survival, treatment response, mechanistic findings, and surrogate endpoints.

4. **Add answer-quality review rubric.**  
   Suggested fields per question:
   - citation validity
   - directness to question
   - evidence-type calibration
   - endpoint consistency
   - mechanistic/clinical separation
   - uncertainty language
   - overall pass/revise/fail

5. **Consider retrieval filters or rerank boosts by question intent.**  
   For clinical risk/prevention questions, prefer human clinical studies, RCTs, meta-analyses, guidelines/reviews; demote cell-line/mechanistic papers unless the query is explicitly mechanistic.
