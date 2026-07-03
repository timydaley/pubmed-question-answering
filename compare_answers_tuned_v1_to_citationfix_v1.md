Comparing baseline_with_answers_full_allchunks_evidselect_tuned_v1.json -> baseline_with_answers_full_allchunks_evidselect_tuned_citationfix_v1.json
questions: old=13 new=13 common=13

## Aggregate
| Metric | Old | New | Delta |
|---|---:|---:|---:|
| Avg retrieval latency (s) | 7.58 | 7.40 | -0.18 |
| Avg generation latency (s) | 9.76 | 9.60 | -0.16 |
| Citation warning rows | 0 | 0 | +0.00 |
| Invalid cited-PMID rows | 0 | 0 | +0.00 |
| Invalid PMID-anywhere rows | 0 | 0 | +0.00 |
| Unbracketed PMID rows | 1 | 0 | -1.00 |
| Citation normalization note rows | 0 | 1 | +1.00 |
| Manual citation extraction mismatches | 0 | 0 | +0.00 |
| Rows with Evidence basis | 13 | 13 | +0.00 |
| Rows with review flags | 1 | 1 | +0.00 |

## GLP-1 agonists and cardiovascular outcomes
generation: 8.253s -> 7.198s (-1.05s)
answer chars: 2114 -> 2242 (+128.00)
Evidence basis: True -> True
cited PMIDs: 0 -> 3; overlap 0/3 union
added citations: 29439603, 30676706, 35546664
review flags: ['causal term:causes'] -> ['causal term:causes']
old short answer: GLP-1 receptor agonists may reduce the risk of death from cardiovascular causes and fatal or non-fatal stroke in patients with type 2 diabetes mellitus, but their effect on fatal or non-fatal myocardial infarction is unc…
new short answer: GLP-1 receptor agonists may reduce the risk of death from cardiovascular causes and fatal or non-fatal stroke in patients with type 2 diabetes mellitus, but their effect on fatal or non-fatal myocardial infarction is unc…

## SGLT2 inhibitors kidney outcomes
generation: 10.385s -> 10.224s (-0.16s)
answer chars: 2222 -> 2222 (+0.00)
Evidence basis: True -> True
cited PMIDs: 5 -> 5; overlap 5/5 union
old short answer: SGLT2 inhibitors are associated with reduced risk of kidney-related outcomes, including acute kidney injury, end-stage kidney disease, and composite kidney events, in patients with type 2 diabetes mellitus.
new short answer: SGLT2 inhibitors are associated with reduced risk of kidney-related outcomes, including acute kidney injury, end-stage kidney disease, and composite kidney events, in patients with type 2 diabetes mellitus.

## aspirin for primary prevention cardiovascular disease
generation: 5.873s -> 5.786s (-0.09s)
answer chars: 2210 -> 2210 (+0.00)
Evidence basis: True -> True
cited PMIDs: 3 -> 3; overlap 3/3 union
old short answer: The evidence suggests that aspirin may be associated with a reduced risk of nonfatal myocardial infarction and stroke, and colorectal cancer, but also increases the risk of gastrointestinal and intracranial bleeding. The…
new short answer: The evidence suggests that aspirin may be associated with a reduced risk of nonfatal myocardial infarction and stroke, and colorectal cancer, but also increases the risk of gastrointestinal and intracranial bleeding. The…

## beta blockers and mortality in heart failure
generation: 11.028s -> 9.208s (-1.82s)
answer chars: 2942 -> 2942 (+0.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 7; overlap 7/7 union
old short answer: Beta-blockers are associated with reduced mortality in patients with heart failure, with a consistent 30% reduction in mortality and a 40% reduction in hospitalizations in patients with class II through IV heart failure…
new short answer: Beta-blockers are associated with reduced mortality in patients with heart failure, with a consistent 30% reduction in mortality and a 40% reduction in hospitalizations in patients with class II through IV heart failure…

## does aspirin reduce colorectal cancer risk?
generation: 13.973s -> 14.631s (+0.66s)
answer chars: 2618 -> 2618 (+0.00)
Evidence basis: True -> True
cited PMIDs: 6 -> 6; overlap 6/6 union
old short answer: The retrieved evidence suggests an association between aspirin use and reduced risk of colorectal cancer, but the evidence is not uniform and some studies show no association.
new short answer: The retrieved evidence suggests an association between aspirin use and reduced risk of colorectal cancer, but the evidence is not uniform and some studies show no association.

## does metformin reduce cancer risk?
generation: 8.116s -> 7.802s (-0.31s)
answer chars: 1774 -> 1774 (+0.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 7; overlap 7/7 union
old short answer: The retrieved evidence suggests an association between metformin use and lower risk of lung cancer, breast cancer, and colorectal cancer, but the evidence is conflicting and insufficient for prostate cancer and ovarian c…
new short answer: The retrieved evidence suggests an association between metformin use and lower risk of lung cancer, breast cancer, and colorectal cancer, but the evidence is conflicting and insufficient for prostate cancer and ovarian c…

## exercise and insulin sensitivity
generation: 7.48s -> 8.564s (+1.08s)
answer chars: 1820 -> 1820 (+0.00)
Evidence basis: True -> True
cited PMIDs: 3 -> 3; overlap 3/3 union
old short answer: Regular exercise has a significant benefit on insulin sensitivity in adults with type 2 diabetes mellitus (T2DM), and this may persist beyond 72 hours after the last exercise session [27535644].
new short answer: Regular exercise has a significant benefit on insulin sensitivity in adults with type 2 diabetes mellitus (T2DM), and this may persist beyond 72 hours after the last exercise session [27535644].

## ketogenic diet epilepsy adults
generation: 8.296s -> 8.66s (+0.36s)
answer chars: 2037 -> 2037 (+0.00)
Evidence basis: True -> True
cited PMIDs: 3 -> 3; overlap 3/3 union
old short answer: The ketogenic diet may be associated with improved seizure control in adults with intractable epilepsy, with reported efficacy rates ranging from 34% to 52%.
new short answer: The ketogenic diet may be associated with improved seizure control in adults with intractable epilepsy, with reported efficacy rates ranging from 34% to 52%.

## mechanism of metformin AMPK activation
generation: 10.853s -> 11.469s (+0.62s)
answer chars: 1815 -> 1815 (+0.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 7; overlap 7/7 union
old short answer: Metformin activates AMP-activated protein kinase (AMPK) through multiple mechanisms, including mitochondria-derived reactive nitrogen species (RNS), inositol polyphosphate multikinase (IPMK), and AMPK-independent effects…
new short answer: Metformin activates AMP-activated protein kinase (AMPK) through multiple mechanisms, including mitochondria-derived reactive nitrogen species (RNS), inositol polyphosphate multikinase (IPMK), and AMPK-independent effects…

## omega-3 supplementation cardiovascular prevention
generation: 10.914s -> 9.674s (-1.24s)
answer chars: 2437 -> 2437 (+0.00)
Evidence basis: True -> True
cited PMIDs: 3 -> 3; overlap 3/3 union
old short answer: Omega-3 supplementation may reduce the risk of major adverse cardiovascular events (MACE), cardiovascular death, and myocardial infarction (MI), but the evidence is not conclusive for overall cardiovascular events and st…
new short answer: Omega-3 supplementation may reduce the risk of major adverse cardiovascular events (MACE), cardiovascular death, and myocardial infarction (MI), but the evidence is not conclusive for overall cardiovascular events and st…

## p53 mutation and cancer prognosis
generation: 12.672s -> 13.001s (+0.33s)
answer chars: 2639 -> 2639 (+0.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 7; overlap 7/7 union
old short answer: The relationship between TP53 mutations and cancer prognosis is complex and influenced by various factors, including the type of cancer, the presence of other genetic alterations, and the expression of p53 isoforms.
new short answer: The relationship between TP53 mutations and cancer prognosis is complex and influenced by various factors, including the type of cancer, the presence of other genetic alterations, and the expression of p53 isoforms.

## statins and risk of dementia
generation: 10.612s -> 10.355s (-0.26s)
answer chars: 2418 -> 2418 (+0.00)
Evidence basis: True -> True
cited PMIDs: 5 -> 5; overlap 5/5 union
old short answer: The retrieved evidence suggests an association between statin use and a reduced risk of dementia, with some studies indicating a 10-20% risk decrement.
new short answer: The retrieved evidence suggests an association between statin use and a reduced risk of dementia, with some studies indicating a 10-20% risk decrement.

## vitamin D supplementation and respiratory infections
generation: 8.407s -> 8.17s (-0.24s)
answer chars: 2571 -> 2571 (+0.00)
Evidence basis: True -> True
cited PMIDs: 4 -> 4; overlap 4/4 union
old short answer: Vitamin D supplementation may have a moderate effect on reducing non-influenza respiratory viral infections, but the evidence is inconsistent regarding its effect on influenza and other respiratory infections.
new short answer: Vitamin D supplementation may have a moderate effect on reducing non-influenza respiratory viral infections, but the evidence is inconsistent regarding its effect on influenza and other respiratory infections.
