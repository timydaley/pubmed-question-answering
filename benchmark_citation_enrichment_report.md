# Citation-Aware Benchmark PMID Enrichment Report
Artifact: `baseline_with_answers_expanded_promptfix_v1.json`  
Date: 2026-06-29
## What was enriched
- Fetched iCite citation_count/RCR for all unique benchmark PMIDs.
- Fetched PubMed metadata for all unique benchmark PMIDs.
- Unique benchmark PMIDs: 130

## Important interpretation note
Low citation count is a useful warning signal, but it is not automatically garbage. Newer papers, niche but directly relevant clinical studies, and specialized mechanistic papers can be low-cited. For benchmark quality, prefer citation/RCR as a **secondary quality signal** after direct relevance and evidence type.

## Per-question citation summary
| Question | Min cites | Median cites | Max cites | Median RCR | Low-cite PMIDs (<10) | Top PMID by cites |
|---|---:|---:|---:|---:|---:|---|
| does metformin reduce cancer risk? | 11 | 64.0 | 177 | 1.94 | 0 | 23687346 (177; Metformin decreases glucose oxidation and increases the) |
| statins and risk of dementia | 3 | 21.0 | 197 | 0.81 | 2 | 18663180 (197; Use of statins and incidence of dementia and cognitive ) |
| vitamin D supplementation and respiratory infections | 0 | 58.5 | 178 | 2.72 | 3 | 25476069 (178; Vitamin D3 supplementation in patients with chronic obs) |
| aspirin for primary prevention cardiovascular disease | 0 | 4.5 | 131 | 0.14 | 8 | 31226053 (131; The rise and fall of aspirin in the primary prevention ) |
| GLP-1 agonists and cardiovascular outcomes | 0 | 13.0 | 465 | 0.46 | 4 | 29221659 (465; Cardiovascular outcomes with glucagon-like peptide-1 re) |
| beta blockers and mortality in heart failure | 0 | 10.5 | 248 | 0.27 | 3 | 11851582 (248; beta-Blocker therapy in heart failure: scientific revie) |
| SGLT2 inhibitors kidney outcomes | 2 | 33.5 | 144 | 2.31 | 2 | 7205941 (144; Na+-dependent sugar transport in a cultured epithelial ) |
| omega-3 supplementation cardiovascular prevention | 0 | 14.5 | 278 | 0.64 | 4 | 22493407 (278; Efficacy of omega-3 fatty acid supplements (eicosapenta) |
| exercise and insulin sensitivity | 7 | 14.5 | 147 | 0.60 | 2 | 27535644 (147; The Effect of Regular Exercise on Insulin Sensitivity i) |
| ketogenic diet epilepsy adults | 3 | 28.0 | 148 | 1.37 | 3 | 25628734 (148; Efficacy of and patient compliance with a ketogenic die) |
| does aspirin reduce colorectal cancer risk? | 2 | 24.0 | 465 | 0.88 | 3 | 19671906 (465; Aspirin use and survival after diagnosis of colorectal ) |
| mechanism of metformin AMPK activation | 16 | 38.5 | 4574 | 1.86 | 0 | 11602624 (4574; Role of AMP-activated protein kinase in mechanism of me) |
| p53 mutation and cancer prognosis | 6 | 26.0 | 96 | 0.99 | 2 | 10885605 (96; p53 and Ki-ras as prognostic factors for Dukes' stage B) |

## Overall citation distribution
- PMID count with citation rows: 130
- Min citation count: 0
- Median citation count: 23.5
- Mean citation count: 86.9
- Max citation count: 4574
- PMIDs with citation_count <= 0: 7 / 130
- PMIDs with citation_count <= 1: 10 / 130
- PMIDs with citation_count <= 5: 25 / 130
- PMIDs with citation_count <= 10: 40 / 130
- PMIDs with citation_count <= 25: 69 / 130
- PMIDs with citation_count <= 50: 92 / 130
- PMIDs with citation_count <= 100: 110 / 130

## Low-citation candidates to inspect
These are not automatically bad, but they are good manual-review targets.

### statins and risk of dementia

- `34756134` cites=3 rcr=0.22904028260062392 year=2021 — An evidence-based review of neuronal cholesterol role in dementia and statins as a pharmacotherapy in reducing risk of dementia.
- `37291702` cites=6 rcr=0.8072154530262817 year=2023 — Statin therapy reduces dementia risk in atrial fibrillation patients receiving oral anticoagulants.

### vitamin D supplementation and respiratory infections

- `35761885` cites=5 rcr=0.5505303312239173 year=2022 — Immunomodulatory Effects of Vitamin D and Prevention of Respiratory Tract Infections and COVID-19.
- `28361631` cites=0 rcr=0.0 year=2017 — Vitamin D supplementation effective in preventing acute respiratory tract infections.
- `28247776` cites=0 rcr=0.0 year=2017 — Vitamin D can help stave off respiratory tract infections.

### aspirin for primary prevention cardiovascular disease

- `16110127` cites=6 rcr=0.17495763917385898 year=2005 — Aspirin for the primary prevention of cardiovascular disease: a comprehensive review.
- `16597054` cites=4 rcr=0.10823465437598262 year=2006 — [The role of aspirin in the primary prevention of cardiovascular disease].
- `31590909` cites=9 rcr=0.4178838775781824 year=2019 — Usefulness of Aspirin for Primary Prevention of Atherosclerotic Cardiovascular Disease.
- `31927808` cites=5 rcr=0.24008249159323802 year=2020 — The Aspirin Primary Prevention Conundrum.
- `32134226` cites=1 rcr=0.07291960089140877 year=2020 — [Aspirin for primary cardiovascular prevention : the end of an era ?]
- `32142233` cites=1 rcr=0.0846785913827431 year=2020 — Aspirin in Primary and Secondary Prevention of Cardiovascular Disease.
- `36354294` cites=0 rcr=0.0 year=2022 — Low-dose aspirin as primary prevention for adults without cardiovascular disease.
- `36541862` cites=0 rcr=0.0 year=2023 — Aspirin for primary prevention of cardiovascular disease in women.

### GLP-1 agonists and cardiovascular outcomes

- `34497008` cites=5 rcr=0.25930447538142914 year=2021 — Updated Meta-Analysis of Cardiovascular Outcome Trials Evaluating Cardiovascular Efficacy of Glucagon-Like Peptide-1 Receptor Agonists.
- `29935211` cites=7 rcr=0.24481930774225988 year=2018 — Cardiovascular safety of GLP-1 receptor agonists for diabetes patients with high cardiovascular risk: A meta-analysis of cardiovascular outcomes trials.
- `34383432` cites=0 rcr=0.0 year=2021 — SGLT2 Inhibitors or GLP-1 Receptor Agonists Reduce Cardiovascular Outcomes in Patients with Type 2 Diabetes.
- `27849161` cites=2 rcr=0.09861017938677052 year=2017 — Liraglutide, a GLP-1 receptor agonist, prevents cardiovascular outcomes in patients with type 2 diabetes.

### beta blockers and mortality in heart failure

- `16528934` cites=0 rcr=0.0 year=2006 — [Use of beta blockers in chronic heart failure].
- `14575625` cites=1 rcr=0.0261152410191389 year=2003 — Beta-adrenergic Receptor Blockers in Heart Failure.
- `12029183` cites=3 rcr=0.08252474705005346 year=2000 — Are all beta blockers the same for heart failure?

### SGLT2 inhibitors kidney outcomes

- `35414444` cites=9 rcr=0.8133444060252014 year=2022 — Sodium glucose cotransporter-2 inhibitors protect the cardiorenal axis: Update on recent mechanistic insights related to kidney physiology.
- `34991813` cites=2 rcr=0.21035869110234962 year=None — SGLT2 inhibition in chronic kidney disease: a preventive strategy against acute kidney injury at the same time?

### omega-3 supplementation cardiovascular prevention

- `33092130` cites=8 rcr=0.3809956508830709 year=2020 — All-Cause Mortality and Cardiovascular Death between Statins and Omega-3 Supplementation: A Meta-Analysis and Network Meta-Analysis from 55 Randomized Controlled Trials.
- `33660821` cites=3 rcr=0.2513125711190367 year=2021 — Omega-3 fatty acids supplementation on major cardiovascular outcomes: an umbrella review of meta-analyses of observational studies and randomized controlled trials.
- `32600510` cites=2 rcr=0.09870107736446017 year=2020 — Omega-3 Fatty Acid Supplements for the Prevention of Cardiovascular Disease.
- `33876607` cites=0 rcr=0.0 year=2021 — Omega-3 supplements do not prevent cardiovascular disease.

### exercise and insulin sensitivity

- `32125032` cites=7 rcr=0.46560245976133385 year=2020 — Potential role of angiotensin-(1-7) in the improvement of vascular insulin sensitivity after a bout of exercise.
- `31427876` cites=9 rcr=0.5094773628665603 year=2019 — Plasma Apelin Unchanged With Acute Exercise Insulin Sensitization.

### ketogenic diet epilepsy adults

- `16274334` cites=6 rcr=0.14699236484948275 year=2005 — Use of the ketogenic diet as a treatment for epilepsy refractory to drug treatment.
- `36637840` cites=3 rcr=0.3615948625751835 year=2022 — Intractable Seizures in Children With Type 1 Diabetes: Implications of the Ketogenic Diet.
- `10909595` cites=4 rcr=0.1511362236327453 year=None — [Ketogenic diet--an alternative therapy for epilepsy in adults].

### does aspirin reduce colorectal cancer risk?

- `34911904` cites=2 rcr=0.10062387330891602 year=2021 — [Aspirin for Chemoprevention of Colorectal Adenoma and Cancer].
- `36047054` cites=2 rcr=0.18480019209021079 year=2022 — Aspirin for Colorectal Cancer Prevention: Age Matters.
- `33849967` cites=2 rcr=0.1855350404426439 year=2021 — Can Cost-effectiveness Analysis Inform Genotype-Guided Aspirin Use for Primary Colorectal Cancer Prevention?

### p53 mutation and cancer prognosis

- `36660245` cites=6 rcr=0.7709172539681233 year=2023 — The High Expression of p53 Is Predictive of Poor Survival Rather TP53 Mutation in Esophageal Squamous Cell Carcinoma.
- `31924585` cites=7 rcr=0.3151178419748959 year=2020 — PRIMA-1MET cytotoxic effect correlates with p53 protein reduction in TP53-mutated chronic lymphocytic leukemia cells.

## Suggested benchmark policy
For clinical benchmarks, consider marking papers as stronger benchmark evidence when they satisfy most of:

- directly answers the question endpoint;
- human clinical study, systematic review, meta-analysis, or RCT when the question is clinical;
- citation_count >= 10 or RCR >= 1, unless recent/niche/directly relevant;
- publication year and journal metadata present;
- not primarily mechanistic/cell-line unless the query is mechanistic.

For mechanistic benchmarks, citation count should be weighted less heavily than pathway specificity and experimental relevance.
