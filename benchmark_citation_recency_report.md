# Citation + Recency Benchmark Report

Artifact: `baseline_with_answers_expanded_promptfix_v1.json`  
Generated: 2026-06-29T19:49:51

## Scoring

`impact_score` is the same bounded citation+recency signal used by retrieval: RCR/log citations + citation velocity + recency. It is a secondary quality signal, not a relevance score.

## Per-question summary

| Question | Median cites | Median impact_score | Low-cite PMIDs | Low-score PMIDs | Best impact PMID |
|---|---:|---:|---:|---:|---|
| does metformin reduce cancer risk? | 64.0 | 0.58 | 0 | 1 | 32592092 (0.84) |
| statins and risk of dementia | 21.0 | 0.40 | 2 | 3 | 18663180 (0.78) |
| vitamin D supplementation and respiratory infections | 58.5 | 0.65 | 3 | 2 | 35507293 (0.86) |
| aspirin for primary prevention cardiovascular disease | 4.5 | 0.26 | 8 | 8 | 31226053 (0.86) |
| GLP-1 agonists and cardiovascular outcomes | 13.0 | 0.34 | 4 | 5 | 29221659 (0.90) |
| beta blockers and mortality in heart failure | 10.5 | 0.23 | 3 | 6 | 11851582 (0.78) |
| SGLT2 inhibitors kidney outcomes | 33.5 | 0.66 | 2 | 1 | 36706745 (0.86) |
| omega-3 supplementation cardiovascular prevention | 14.5 | 0.35 | 4 | 5 | 22493407 (0.85) |
| exercise and insulin sensitivity | 14.5 | 0.34 | 2 | 6 | 27535644 (0.83) |
| ketogenic diet epilepsy adults | 28.0 | 0.47 | 3 | 4 | 25628734 (0.82) |
| does aspirin reduce colorectal cancer risk? | 24.0 | 0.37 | 3 | 5 | 19671906 (0.87) |
| mechanism of metformin AMPK activation | 38.5 | 0.58 | 0 | 0 | 11602624 (0.87) |
| p53 mutation and cancer prognosis | 26.0 | 0.42 | 2 | 2 | 10885605 (0.56) |

## Low citation/recency-score review targets

### does metformin reduce cancer risk?

- `25806241` impact_score=0.27 cites=11 rcr=0.3408150930252199 recency=0.17 cite_rate=0.18 year=2013 — Association of the metformin with the risk of lung cancer: a meta-analysis.

### statins and risk of dementia

- `34756134` impact_score=0.28 cites=3 rcr=0.22904028260062392 recency=0.47 cite_rate=0.12 year=2021 — An evidence-based review of neuronal cholesterol role in dementia and statins as a pharmacotherapy in reducing risk of dementia.
- `18695588` impact_score=0.29 cites=18 rcr=0.5568503304239146 recency=0.11 cite_rate=0.21 year=2009 — Use of statins and risk of hospitalization with dementia: a Danish population-based case-control study.
- `20100290` impact_score=0.34 cites=24 rcr=0.7696811411767122 recency=0.12 cite_rate=0.27 year=2010 — Systematic review of statins for the prevention of vascular dementia or dementia.
- `37291702` impact_score=0.42 cites=6 rcr=0.8072154530262817 recency=0.61 cite_rate=0.28 year=2023 — Statin therapy reduces dementia risk in atrial fibrillation patients receiving oral anticoagulants.

### vitamin D supplementation and respiratory infections

- `28361631` impact_score=0.22 cites=0 rcr=0.0 recency=0.29 cite_rate=0.10 year=2017 — Vitamin D supplementation effective in preventing acute respiratory tract infections.
- `28247776` impact_score=0.22 cites=0 rcr=0.0 recency=0.29 cite_rate=0.10 year=2017 — Vitamin D can help stave off respiratory tract infections.
- `35761885` impact_score=0.36 cites=5 rcr=0.5505303312239173 recency=0.54 cite_rate=0.21 year=2022 — Immunomodulatory Effects of Vitamin D and Prevention of Respiratory Tract Infections and COVID-19.

### aspirin for primary prevention cardiovascular disease

- `16597054` impact_score=0.20 cites=4 rcr=0.10823465437598262 recency=0.10 cite_rate=0.10 year=2006 — [The role of aspirin in the primary prevention of cardiovascular disease].
- `16110127` impact_score=0.21 cites=6 rcr=0.17495763917385898 recency=0.10 cite_rate=0.10 year=2005 — Aspirin for the primary prevention of cardiovascular disease: a comprehensive review.
- `32134226` impact_score=0.25 cites=1 rcr=0.07291960089140877 recency=0.42 cite_rate=0.10 year=2020 — [Aspirin for primary cardiovascular prevention : the end of an era ?]
- `32142233` impact_score=0.25 cites=1 rcr=0.0846785913827431 recency=0.42 cite_rate=0.10 year=2020 — Aspirin in Primary and Secondary Prevention of Cardiovascular Disease.
- `36354294` impact_score=0.26 cites=0 rcr=0.0 recency=0.54 cite_rate=0.10 year=2022 — Low-dose aspirin as primary prevention for adults without cardiovascular disease.
- `36541862` impact_score=0.27 cites=0 rcr=0.0 recency=0.61 cite_rate=0.10 year=2023 — Aspirin for primary prevention of cardiovascular disease in women.
- `31927808` impact_score=0.29 cites=5 rcr=0.24008249159323802 recency=0.42 cite_rate=0.17 year=2020 — The Aspirin Primary Prevention Conundrum.
- `31590909` impact_score=0.32 cites=9 rcr=0.4178838775781824 recency=0.37 cite_rate=0.23 year=2019 — Usefulness of Aspirin for Primary Prevention of Atherosclerotic Cardiovascular Disease.

### GLP-1 agonists and cardiovascular outcomes

- `27849161` impact_score=0.23 cites=2 rcr=0.09861017938677052 recency=0.29 cite_rate=0.10 year=2017 — Liraglutide, a GLP-1 receptor agonist, prevents cardiovascular outcomes in patients with type 2 diabetes.
- `34383432` impact_score=0.25 cites=0 rcr=0.0 recency=0.47 cite_rate=0.10 year=2021 — SGLT2 Inhibitors or GLP-1 Receptor Agonists Reduce Cardiovascular Outcomes in Patients with Type 2 Diabetes.
- `29935211` impact_score=0.28 cites=7 rcr=0.24481930774225988 recency=0.32 cite_rate=0.18 year=2018 — Cardiovascular safety of GLP-1 receptor agonists for diabetes patients with high cardiovascular risk: A meta-analysis of cardiovascular outcomes trials.
- `34497008` impact_score=0.30 cites=5 rcr=0.25930447538142914 recency=0.47 cite_rate=0.19 year=2021 — Updated Meta-Analysis of Cardiovascular Outcome Trials Evaluating Cardiovascular Efficacy of Glucagon-Like Peptide-1 Receptor Agonists.
- `31422061` impact_score=0.32 cites=10 rcr=0.3508302154353724 recency=0.37 cite_rate=0.25 year=2019 — GLP-1 receptor agonists and cardiovascular outcomes: an updated synthesis.

### beta blockers and mortality in heart failure

- `16528934` impact_score=0.19 cites=0 rcr=0.0 recency=0.10 cite_rate=0.10 year=2006 — [Use of beta blockers in chronic heart failure].
- `14575625` impact_score=0.20 cites=1 rcr=0.0261152410191389 recency=0.10 cite_rate=0.10 year=2003 — Beta-adrenergic Receptor Blockers in Heart Failure.
- `12029183` impact_score=0.20 cites=3 rcr=0.08252474705005346 recency=0.10 cite_rate=0.10 year=2000 — Are all beta blockers the same for heart failure?
- `12173717` impact_score=0.22 cites=10 rcr=0.2087446617938144 recency=0.10 cite_rate=0.10 year=2002 — Beta-blockers: new standard therapy for heart failure.
- `15516859` impact_score=0.22 cites=10 rcr=0.24839260875408947 recency=0.10 cite_rate=0.11 year=2004 — The effects of beta blockers on morbidity and mortality in heart failure.
- `15311169` impact_score=0.23 cites=11 rcr=0.29147008166722976 recency=0.10 cite_rate=0.12 year=2004 — Use of beta-blockers in older adults with chronic heart failure.

### SGLT2 inhibitors kidney outcomes

- `34991813` impact_score=0.29 cites=2 rcr=0.21035869110234962 recency=0.10 cite_rate=0.34 year=None — SGLT2 inhibition in chronic kidney disease: a preventive strategy against acute kidney injury at the same time?
- `35414444` impact_score=0.42 cites=9 rcr=0.8133444060252014 recency=0.54 cite_rate=0.32 year=2022 — Sodium glucose cotransporter-2 inhibitors protect the cardiorenal axis: Update on recent mechanistic insights related to kidney physiology.

### omega-3 supplementation cardiovascular prevention

- `33876607` impact_score=0.25 cites=0 rcr=0.0 recency=0.47 cite_rate=0.10 year=2021 — Omega-3 supplements do not prevent cardiovascular disease.
- `32600510` impact_score=0.25 cites=2 rcr=0.09870107736446017 recency=0.42 cite_rate=0.10 year=2020 — Omega-3 Fatty Acid Supplements for the Prevention of Cardiovascular Disease.
- `33660821` impact_score=0.28 cites=3 rcr=0.2513125711190367 recency=0.47 cite_rate=0.12 year=2021 — Omega-3 fatty acids supplementation on major cardiovascular outcomes: an umbrella review of meta-analyses of observational studies and randomized controlled trials.
- `22493410` impact_score=0.32 cites=17 rcr=0.6158369477752996 recency=0.15 cite_rate=0.23 year=2012 — Omega-3 fatty acids and secondary prevention of cardiovascular disease-is it just a fish tale?: comment on “Efficacy of omega-3 fatty acid supplements (eicosapentaenoic acid and docosahexaenoic acid) in the secondary prevention of cardiovascular disease”.
- `33092130` impact_score=0.33 cites=8 rcr=0.3809956508830709 recency=0.42 cite_rate=0.23 year=2020 — All-Cause Mortality and Cardiovascular Death between Statins and Omega-3 Supplementation: A Meta-Analysis and Network Meta-Analysis from 55 Randomized Controlled Trials.

### exercise and insulin sensitivity

- `17467109` impact_score=0.24 cites=12 rcr=0.32354201275078315 recency=0.10 cite_rate=0.14 year=2007 — Effect of insulin sensitivity on severity of heart failure.
- `20955773` impact_score=0.27 cites=12 rcr=0.43932590988652087 recency=0.14 cite_rate=0.17 year=2011 — Insulin sensitization by voluntary exercise in aging rats is mediated through hepatic insulin sensitizing substance (HISS).
- `32125032` impact_score=0.33 cites=7 rcr=0.46560245976133385 recency=0.42 cite_rate=0.21 year=2020 — Potential role of angiotensin-(1-7) in the improvement of vascular insulin sensitivity after a bout of exercise.
- `31427876` impact_score=0.33 cites=9 rcr=0.5094773628665603 recency=0.37 cite_rate=0.23 year=2019 — Plasma Apelin Unchanged With Acute Exercise Insulin Sensitization.
- `27285860` impact_score=0.34 cites=16 rcr=0.5810519851783886 recency=0.25 cite_rate=0.28 year=2016 — Rac1 in Muscle Is Dispensable for Improved Insulin Action After Exercise in Mice.
- `29387730` impact_score=0.34 cites=13 rcr=0.6126760873626957 recency=0.29 cite_rate=0.26 year=2017 — Enhancing Exercise Responsiveness across Prediabetes Phenotypes by Targeting Insulin Sensitivity with Nutrition.

### ketogenic diet epilepsy adults

- `16274334` impact_score=0.21 cites=6 rcr=0.14699236484948275 recency=0.10 cite_rate=0.10 year=2005 — Use of the ketogenic diet as a treatment for epilepsy refractory to drug treatment.
- `36637840` impact_score=0.31 cites=3 rcr=0.3615948625751835 recency=0.54 cite_rate=0.14 year=2022 — Intractable Seizures in Children With Type 1 Diabetes: Implications of the Ketogenic Diet.
- `26476148` impact_score=0.32 cites=14 rcr=0.5534668833910377 recency=0.22 cite_rate=0.24 year=2015 — Efficacy of the Ketogenic Diet for the Treatment of Refractory Childhood Epilepsy: Cerebrospinal Fluid Neurotransmitters and Amino Acid Levels.
- `10909595` impact_score=0.33 cites=4 rcr=0.1511362236327453 recency=0.10 cite_rate=0.49 year=None — [Ketogenic diet--an alternative therapy for epilepsy in adults].

### does aspirin reduce colorectal cancer risk?

- `34911904` impact_score=0.26 cites=2 rcr=0.10062387330891602 recency=0.47 cite_rate=0.10 year=2021 — [Aspirin for Chemoprevention of Colorectal Adenoma and Cancer].
- `33849967` impact_score=0.27 cites=2 rcr=0.1855350404426439 recency=0.47 cite_rate=0.10 year=2021 — Can Cost-effectiveness Analysis Inform Genotype-Guided Aspirin Use for Primary Colorectal Cancer Prevention?
- `36047054` impact_score=0.28 cites=2 rcr=0.18480019209021079 recency=0.54 cite_rate=0.10 year=2022 — Aspirin for Colorectal Cancer Prevention: Age Matters.
- `25252097` impact_score=0.28 cites=10 rcr=0.39747583336800363 recency=0.22 cite_rate=0.19 year=2015 — Can aspirin reduce the risk of colorectal cancer in people with diabetes? A population-based cohort study.
- `8085092` impact_score=0.34 cites=30 rcr=0.9310693813419252 recency=0.10 cite_rate=0.20 year=1994 — Aspirin and the prevention of colorectal cancer: a review of the evidence.

### p53 mutation and cancer prognosis

- `14758132` impact_score=0.29 cites=24 rcr=0.4832067631115576 recency=0.10 cite_rate=0.22 year=2004 — Simultaneous mutations in K-ras and TP53 are indicative of poor prognosis in sporadic colorectal cancer.
- `31924585` impact_score=0.31 cites=7 rcr=0.3151178419748959 recency=0.42 cite_rate=0.21 year=2020 — PRIMA-1MET cytotoxic effect correlates with p53 protein reduction in TP53-mutated chronic lymphocytic leukemia cells.
- `36660245` impact_score=0.42 cites=6 rcr=0.7709172539681233 recency=0.61 cite_rate=0.28 year=2023 — The High Expression of p53 Is Predictive of Poor Survival Rather TP53 Mutation in Esophageal Squamous Cell Carcinoma.

## Overall

- PMIDs scored: 130
- Median impact_score: 0.41
- Low impact_score (<0.35): 48 / 130
