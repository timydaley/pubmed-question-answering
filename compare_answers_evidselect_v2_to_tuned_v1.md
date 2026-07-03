Comparing baseline_with_answers_full_allchunks_evidselect_v2.json -> baseline_with_answers_full_allchunks_evidselect_tuned_v1.json
questions: old=13 new=13 common=13

## Aggregate
| Metric | Old | New | Delta |
|---|---:|---:|---:|
| Avg retrieval latency (s) | 7.41 | 7.58 | +0.17 |
| Avg generation latency (s) | 10.99 | 9.76 | -1.23 |
| Citation warning rows | 0 | 0 | +0.00 |
| Invalid cited-PMID rows | 0 | 0 | +0.00 |
| Manual citation extraction mismatches | 0 | 0 | +0.00 |
| Rows with Evidence basis | 13 | 13 | +0.00 |
| Rows with review flags | 1 | 1 | +0.00 |

## GLP-1 agonists and cardiovascular outcomes
generation: 12.766s -> 8.253s (-4.51s)
answer chars: 2528 -> 2114 (-414.00)
Evidence basis: True -> True
cited PMIDs: 3 -> 0; overlap 0/3 union
removed citations: 30223891, 35030451, 35546664
review flags: ['causal term:causes'] -> ['causal term:causes']
old short answer: GLP-1 receptor agonists are associated with reduced risk of death from cardiovascular causes, fatal or non-fatal stroke, and a composite kidney outcome in patients with type 2 diabetes, but the evidence for cardiovascula…
new short answer: GLP-1 receptor agonists may reduce the risk of death from cardiovascular causes and fatal or non-fatal stroke in patients with type 2 diabetes mellitus, but their effect on fatal or non-fatal myocardial infarction is unc…

## SGLT2 inhibitors kidney outcomes
generation: 14.282s -> 10.385s (-3.90s)
answer chars: 2384 -> 2222 (-162.00)
Evidence basis: True -> True
cited PMIDs: 4 -> 5; overlap 3/6 union
added citations: 33663074, 36706745
removed citations: 36316605
old short answer: SGLT2 inhibitors are associated with reduced risk of kidney outcomes, including end-stage kidney disease, acute kidney injury, and kidney death, in patients with type 2 diabetes.
new short answer: SGLT2 inhibitors are associated with reduced risk of kidney-related outcomes, including acute kidney injury, end-stage kidney disease, and composite kidney events, in patients with type 2 diabetes mellitus.

## aspirin for primary prevention cardiovascular disease
generation: 11.179s -> 5.873s (-5.31s)
answer chars: 3688 -> 2210 (-1478.00)
Evidence basis: True -> True
cited PMIDs: 3 -> 3; overlap 0/6 union
added citations: 28577622, 31280821, 33221264
removed citations: 27341534, 35471507, 36541862
old short answer: The evidence suggests that low-dose aspirin may be associated with a small absolute risk reduction in major cardiovascular disease events, but the evidence is insufficient to recommend universal use or avoidance for prim…
new short answer: The evidence suggests that aspirin may be associated with a reduced risk of nonfatal myocardial infarction and stroke, and colorectal cancer, but also increases the risk of gastrointestinal and intracranial bleeding. The…

## beta blockers and mortality in heart failure
generation: 9.789s -> 11.028s (+1.24s)
answer chars: 2942 -> 2942 (+0.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 7; overlap 7/7 union
old short answer: Beta-blockers are associated with reduced mortality in patients with heart failure, with a consistent 30% reduction in mortality and a 40% reduction in hospitalizations in patients with class II through IV heart failure…
new short answer: Beta-blockers are associated with reduced mortality in patients with heart failure, with a consistent 30% reduction in mortality and a 40% reduction in hospitalizations in patients with class II through IV heart failure…

## does aspirin reduce colorectal cancer risk?
generation: 11.227s -> 13.973s (+2.75s)
answer chars: 2618 -> 2618 (+0.00)
Evidence basis: True -> True
cited PMIDs: 6 -> 6; overlap 6/6 union
old short answer: The retrieved evidence suggests an association between aspirin use and reduced risk of colorectal cancer, but the evidence is not uniform and some studies show no association.
new short answer: The retrieved evidence suggests an association between aspirin use and reduced risk of colorectal cancer, but the evidence is not uniform and some studies show no association.

## does metformin reduce cancer risk?
generation: 10.427s -> 8.116s (-2.31s)
answer chars: 2479 -> 1774 (-705.00)
Evidence basis: True -> True
cited PMIDs: 4 -> 7; overlap 4/7 union
added citations: 23753040, 24172091, 25664181
old short answer: The retrieved evidence suggests an association between metformin use and lower risk of developing lung cancer, but higher risk of high-grade prostate cancer and overall prostate cancer.
new short answer: The retrieved evidence suggests an association between metformin use and lower risk of lung cancer, breast cancer, and colorectal cancer, but the evidence is conflicting and insufficient for prostate cancer and ovarian c…

## exercise and insulin sensitivity
generation: 9.245s -> 7.48s (-1.76s)
answer chars: 2347 -> 1820 (-527.00)
Evidence basis: True -> True
cited PMIDs: 4 -> 3; overlap 2/5 union
added citations: 29387730
removed citations: 24861730, 25376729
old short answer: Regular exercise has a significant benefit on insulin sensitivity in adults with type 2 diabetes mellitus and may persist beyond 72 hours after the last exercise session [27535644]. Exercise is a valuable primary care an…
new short answer: Regular exercise has a significant benefit on insulin sensitivity in adults with type 2 diabetes mellitus (T2DM), and this may persist beyond 72 hours after the last exercise session [27535644].

## ketogenic diet epilepsy adults
generation: 9.345s -> 8.296s (-1.05s)
answer chars: 2348 -> 2037 (-311.00)
Evidence basis: True -> True
cited PMIDs: 5 -> 3; overlap 2/6 union
added citations: 10909595
removed citations: 18358881, 24380692, 24675110
old short answer: The ketogenic diet is associated with a potential efficacy rate of 42% in adults with intractable epilepsy, with a combined compliance rate of 45%. The diet may be more effective in adults with focal epilepsy.
new short answer: The ketogenic diet may be associated with improved seizure control in adults with intractable epilepsy, with reported efficacy rates ranging from 34% to 52%.

## mechanism of metformin AMPK activation
generation: 9.51s -> 10.853s (+1.34s)
answer chars: 1815 -> 1815 (+0.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 7; overlap 7/7 union
old short answer: Metformin activates AMP-activated protein kinase (AMPK) through multiple mechanisms, including mitochondria-derived reactive nitrogen species (RNS), inositol polyphosphate multikinase (IPMK), and AMPK-independent effects…
new short answer: Metformin activates AMP-activated protein kinase (AMPK) through multiple mechanisms, including mitochondria-derived reactive nitrogen species (RNS), inositol polyphosphate multikinase (IPMK), and AMPK-independent effects…

## omega-3 supplementation cardiovascular prevention
generation: 14.483s -> 10.914s (-3.57s)
answer chars: 3333 -> 2437 (-896.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 3; overlap 2/8 union
added citations: 16686171
removed citations: 19609891, 32600510, 32722395, 33092130, 36103100
old short answer: Omega-3 supplementation may reduce the risk of major cardiovascular events, myocardial infarction, and cardiovascular death, but the evidence is not conclusive and may be influenced by the type of omega-3 fatty acid supp…
new short answer: Omega-3 supplementation may reduce the risk of major adverse cardiovascular events (MACE), cardiovascular death, and myocardial infarction (MI), but the evidence is not conclusive for overall cardiovascular events and st…

## p53 mutation and cancer prognosis
generation: 11.42s -> 12.672s (+1.25s)
answer chars: 2639 -> 2639 (+0.00)
Evidence basis: True -> True
cited PMIDs: 7 -> 7; overlap 7/7 union
old short answer: The relationship between TP53 mutations and cancer prognosis is complex and influenced by various factors, including the type of cancer, the presence of other genetic alterations, and the expression of p53 isoforms.
new short answer: The relationship between TP53 mutations and cancer prognosis is complex and influenced by various factors, including the type of cancer, the presence of other genetic alterations, and the expression of p53 isoforms.

## statins and risk of dementia
generation: 10.382s -> 10.612s (+0.23s)
answer chars: 2418 -> 2418 (+0.00)
Evidence basis: True -> True
cited PMIDs: 5 -> 5; overlap 5/5 union
old short answer: The retrieved evidence suggests an association between statin use and a reduced risk of dementia, with some studies indicating a 10-20% risk decrement.
new short answer: The retrieved evidence suggests an association between statin use and a reduced risk of dementia, with some studies indicating a 10-20% risk decrement.

## vitamin D supplementation and respiratory infections
generation: 8.805s -> 8.407s (-0.40s)
answer chars: 2571 -> 2571 (+0.00)
Evidence basis: True -> True
cited PMIDs: 4 -> 4; overlap 4/4 union
old short answer: Vitamin D supplementation may have a moderate effect on reducing non-influenza respiratory viral infections, but the evidence is inconsistent regarding its effect on influenza and other respiratory infections.
new short answer: Vitamin D supplementation may have a moderate effect on reducing non-influenza respiratory viral infections, but the evidence is inconsistent regarding its effect on influenza and other respiratory infections.
