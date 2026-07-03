# Evidence Selection v2 Manual Answer Review

Date: 2026-07-02

Artifact reviewed:

```text
baseline_with_answers_full_allchunks_evidselect_v2.json
```

Scope: targeted manual review of the six questions called out in `CURRENT_STATE_2026-07-02.md` and `evidence_selection_v1_review.md`.

Important limitation: this is a local artifact review, not an independent biomedical systematic review. Judgments below assess whether the selected evidence context and generated answer are appropriate for v1 behavior.

## Summary verdict

| Question | Verdict | Main reason |
|---|---|---|
| metformin/cancer risk | Needs tuning | Answer overgeneralizes cancer-specific evidence and over-emphasizes one prostate-cancer study in the short answer. |
| omega-3/CVD prevention | Acceptable with minor caveat | Context includes positive and negative meta-analytic evidence; answer appropriately cautious. |
| aspirin/CRC risk | Acceptable | Context captures RCT/meta-analysis/observational mix and answer preserves uncertainty. |
| ketogenic diet adults | Needs tuning | Adult focus improved, but selected context still includes young-adult/pediatric-transition/adverse vascular papers and a case report. |
| exercise/insulin sensitivity | Needs tuning | Top clinical/meta-analysis evidence is good, but generated answer still incorporates mechanistic/small acute-study claims too prominently. |
| p53 prognosis | Acceptable but broad | Answer correctly says cancer-type-specific and complex; broad pan-cancer question naturally yields heterogeneous evidence. |

Overall: evidence selection v2 is useful, but should remain experimental until the three `Needs tuning` cases are addressed or explicitly documented.

---

## 1. Does metformin reduce cancer risk?

### Selected-context behavior

Good changes:

- The selected papers now consistently anchor on metformin exposure.
- Unrelated COVID/cancer or hepatocellular papers from earlier selection are no longer present.
- The context includes multiple cancer sites rather than a single off-topic high-tier paper.

Problems:

- The question asks broad cancer risk, but the selected evidence is cancer-site heterogeneous: lung, prostate, colorectal, ovarian, breast, plus general prevention/treatment reviews.
- Several selected papers are survival/treatment papers rather than incidence/risk papers, despite the risk-prevention question.
- The short answer foregrounds “higher prostate-cancer risk” from one cohort-style selected item, which can sound like a broad metformin/cancer conclusion.

### Answer behavior

The answer is citation-valid and includes observational-confounding caveats, but the short answer is too specific and potentially misleading for a broad question.

Current short answer:

> lower risk of developing lung cancer, but higher risk of high-grade prostate cancer and overall prostate cancer.

Preferred v1 behavior:

> Retrieved observational/meta-analytic evidence is mixed and cancer-site-specific. It suggests possible lower risk for some cancers, but does not support a broad causal claim that metformin reduces overall cancer risk.

### Verdict

**Needs tuning before default.**

### Recommended fixes

- Add a broad-risk guard: for questions like “does X reduce cancer risk?”, avoid making the short answer hinge on one cancer-site-specific adverse association.
- Prefer incidence/risk papers over survival/treatment papers for risk-prevention questions.
- Consider requiring at least two independent selected papers before elevating a cancer-site-specific contrary finding into the short answer.

---

## 2. Omega-3 supplementation cardiovascular prevention

### Selected-context behavior

Good changes:

- Includes multiple meta-analyses/systematic reviews of RCTs.
- Preserves conflict/null evidence, including negative/critical papers.
- Covers MACE, myocardial infarction, cardiovascular death, and atrial fibrillation risk.

Problems:

- Some selected papers are labeled with mechanistic penalties even though they are clinical reviews/meta-analyses. This looks like heuristic over-triggering, but it did not harm the final context much here.
- The uncertainty section says evidence is “based on observational associations,” while the evidence basis correctly says RCTs/meta-analyses. That sentence should be avoided for this query.

### Answer behavior

The answer is appropriately cautious: possible benefit, not conclusive, depends on formulation/population, and includes conflict.

### Verdict

**Acceptable with minor caveat.**

### Recommended fixes

- Remove or reduce the generic “observational associations” caveat when selected evidence is mostly RCT/meta-analysis.
- Investigate why clinical omega-3 meta-analyses receive mechanistic penalties.

---

## 3. Does aspirin reduce colorectal cancer risk?

### Selected-context behavior

Good changes:

- Includes meta-analysis/systematic review evidence.
- Includes a hereditary colorectal cancer RCT follow-up.
- Includes observational cohort evidence and a null/conflicting follow-up study.
- Selected evidence is on-topic for aspirin and colorectal cancer.

Problems:

- Population heterogeneity is high: hereditary CRC carriers, diabetes cohort, male health professionals, and general prevention reviews.
- Some older observational papers receive high position in context, but this is acceptable for v1 given the small context and lack of citation metadata.

### Answer behavior

The answer is cautious, does not overclaim, and notes non-uniform evidence and uncertainty about dose/duration.

### Verdict

**Acceptable.**

### Recommended fixes

- No blocking fix. Later citation/RCR ingestion may help prioritize landmark/modern evidence.

---

## 4. Ketogenic diet epilepsy adults

### Selected-context behavior

Good changes:

- The pediatric-only systematic review noted in earlier review is no longer selected.
- Adult-specific meta-analysis and adult-focused review are selected.

Problems:

- Several selected papers still have mixed children/young-adult or transition populations.
- A vascular morphology/adverse-effect paper in children and young adults appears in the key evidence and distracts from adult seizure-efficacy question.
- A case report appears in key papers despite weak evidentiary value.

### Answer behavior

The answer is mostly cautious and adult-focused, but it includes arterial stiffness in children/young adults in the evidence summary, which is off-target for the adult epilepsy efficacy question.

### Verdict

**Needs tuning.**

### Recommended fixes

- For adult clinical efficacy questions, down-rank mixed pediatric/young-adult papers more strongly unless adult-specific context count is below the minimum.
- Suppress case reports from “Key papers” when higher-tier adult evidence is present.
- Consider endpoint-specific filtering: efficacy/seizure-frequency questions should not select adverse vascular morphology papers unless the question asks safety.

---

## 5. Exercise and insulin sensitivity

### Selected-context behavior

Good changes:

- Top selected papers include two directly relevant systematic review/meta-analysis papers.
- The answer correctly identifies exercise as associated with improved insulin sensitivity.

Problems:

- The remaining selected context is heavily mechanistic or small acute-intervention evidence.
- Mechanistic claims appear too prominently in the short answer, including undercarboxylated osteocalcin after acute exercise.
- A mouse study is selected for a human clinical question.

### Answer behavior

The answer is broadly directionally correct, but the short answer is too long and mixes clinical conclusion with mechanistic/acute-study details.

### Verdict

**Needs tuning.**

### Recommended fixes

- For clinical outcome questions with at least two clinical/meta-analysis papers, cap mechanistic evidence at zero or one and prevent animal-only studies from selection.
- Keep mechanistic details out of the short answer unless the question asks for mechanism.
- Prefer human intervention/meta-analysis papers for exercise questions.

---

## 6. p53 mutation and cancer prognosis

### Selected-context behavior

Good changes:

- Selected evidence is broadly on-topic for TP53/p53 and prognosis.
- Includes meta-analyses/systematic reviews plus cohort-style studies.
- Captures cancer-type specificity and complexity.

Problems:

- The question is broad, so selected evidence spans many tumor types and related p53 biology; this makes a precise answer difficult.
- Some selected papers are p53 expression/isoform/pathway papers rather than strictly TP53 mutation prognostic papers.

### Answer behavior

The answer appropriately avoids a single universal conclusion and says the relationship is cancer-type-specific and complex.

### Verdict

**Acceptable but broad.**

### Recommended fixes

- No blocking fix for v1. For future work, add query clarification or cancer-type-specific follow-up prompts for broad biomarker prognosis questions.

---

## Cross-cutting recommendations

1. Keep evidence selection enabled for experimentation, but do not declare it release-default yet.
2. Add stronger endpoint filtering for risk/prevention vs survival/treatment vs safety/adverse-effect questions.
3. Add a stricter human-clinical preference for non-mechanistic clinical questions:
   - if at least `min_papers` clinical papers exist, exclude animal-only/cell-line papers;
   - cap mechanistic papers at zero or one depending on query intent.
4. Add short-answer safeguards:
   - broad questions should not foreground one narrow cancer-site or subgroup finding;
   - mechanistic details should not appear in short answers for clinical questions;
   - generic observational caveats should not be inserted when the selected evidence is mainly RCT/meta-analysis.
5. Re-run the evidence-selection benchmark after tuning and compare against `baseline_with_answers_full_allchunks_evidselect_v2.json`.

## Follow-up tuning smoke checks

After this review, initial selector tuning was applied in `src/pubmedqa/evidence_select.py` and smoke-tested with `p0_ask.py` on the full snapshot.

### Exercise / insulin sensitivity

Command used:

```bash
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python scripts/p0_ask.py \
  --top 10 --retrieve-pool 30 --evidence-context 8 --show-selected \
  "exercise and insulin sensitivity"
```

Observed change:

- Selected context shrank to the two direct meta-analyses plus one non-animal mechanistic/nutrition paper.
- The mouse Rac1 paper was no longer selected after adding title-level animal/cell filtering.
- The generated short answer became more clinically focused and no longer foregrounded osteocalcin/acute-mechanism details.

### Ketogenic diet / adult epilepsy

Observed change:

- Selected context dropped the children/young-adult arterial-stiffness safety paper after safety/adverse endpoint filtering.
- The answer no longer foregrounded pediatric/young-adult vascular findings.
- Remaining limitation: adult evidence is sparse, and one case-report/review-style adult paper can still appear.

### Metformin / cancer risk

Observed change:

- Missing-exposure candidates are now rejected, preventing unrelated high-tier COVID/cancer papers from backfilling the selected context.
- Survival/treatment endpoint penalties were strengthened.
- The answer remains cancer-site-specific and observational; broad metformin/cancer questions still need cautious answer prompting or additional site-diversity logic.
