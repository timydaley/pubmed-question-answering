"""Question-aware evidence context selection.

Retrieval should cast a broad net; answer generation should see a smaller,
more direct, endpoint-matched, and evidence-tier-aware context.  This module is
intentionally heuristic for v1: no network calls and no extra model dependency.
"""
import re
from difflib import SequenceMatcher


CLINICAL_TYPES = {
    "meta-analysis", "systematic review", "randomized controlled trial",
    "clinical trial", "cohort", "case-control", "observational study",
}


def _text(p):
    return f"{p.get('title') or ''} {p.get('abstract') or ''} {p.get('pubtypes') or ''}".lower()


def _title(p):
    return (p.get("title") or "").lower()


def _has(text, *terms):
    return any(t in text for t in terms)


def _has_re(text, pattern):
    return re.search(pattern, text) is not None


CLINICAL_MANAGEMENT_TERMS = (
    "treatment", "treat", "therapy", "management", "manage", "prevention", "prevent",
    "control", "what helps", "what should be used", "first line", "standard of care",
    "medication", "medicine", "drug", "symptom", "nausea", "vomiting", "pain",
    "insomnia", "hypertension", "migraine",
)

ADJUNCTIVE_QUERY_TERMS = (
    "massage", "acupressure", "acupuncture", "moxibustion", "ginger", "hypnosis",
    "relaxation", "music therapy", "behavioral", "behavioural", "psychological",
    "supplement", "diet", "complementary", "alternative", "non-pharmacologic",
    "nonpharmacologic", "non-drug", "nondrug",
)

MANAGEMENT_EXPANSION_TERMS = (
    "treatment", "management", "guideline", "clinical practice guideline",
    "standard of care", "first line", "therapy", "prevention", "pharmacologic",
    "drug therapy", "randomized trial", "systematic review", "meta-analysis",
)

LOCAL_MANAGEMENT_SYNONYMS = (
    (
        re.compile(r"\b(chemo(?:therapy)?|antineoplastic)\b.*\b(nausea|vomiting|emesis)\b|\b(nausea|vomiting|emesis)\b.*\b(chemo(?:therapy)?|antineoplastic)\b"),
        ("chemotherapy-induced nausea and vomiting", "CINV", "antiemetic"),
    ),
)


def is_clinical_management_question(question):
    """Detect broad treatment/prevention/symptom-control questions."""
    q = (question or "").lower()
    if not q:
        return False
    if any(term in q for term in CLINICAL_MANAGEMENT_TERMS):
        return True
    # Family-use shorthand often omits "treatment" but names a symptom + clinical context.
    if _has(q, "nausea", "vomiting", "pain") and _has(q, "chemotherapy", "pregnancy", "diabetic", "neuropathy", "back"):
        return True
    return False


def explicit_adjunctive_query(question):
    q = (question or "").lower()
    return any(term in q for term in ADJUNCTIVE_QUERY_TERMS)


def behavioral_central_question(question):
    """Conditions where behavioral/rehab care may be standard, not adjunctive."""
    q = (question or "").lower()
    return _has(q, "insomnia", "depression", "anxiety", "back pain", "chronic pain", "pain treatment", "physical therapy", "rehabilitation")


def infer_intent(question):
    q = (question or "").lower()
    intents = set()
    if is_clinical_management_question(question):
        intents.add("clinical_management")
    if _has(q, "mechanism", "activation", "pathway", "signaling", "signalling"):
        intents.add("mechanism")
    if _has(q, "prognosis", "prognostic") or _has(q, "mortality", "survival") and not _has(q, "prevent", "prevention"):
        intents.add("prognosis_survival")
    if _has(q, "risk", "reduce", "prevention", "prevent", "incidence", "develop"):
        intents.add("risk_prevention")
    if _has(q, "outcome", "outcomes", "mortality", "cardiovascular", "kidney", "renal", "heart failure", "epilepsy", "seizure", "seizures", "efficacy", "effective"):
        intents.add("clinical_outcomes")
    if _has(q, "supplementation", "supplement"):
        intents.add("supplementation")
    if _has(q, "chemotherapy", "chemo") and _has(q, "nausea", "vomiting", "emesis", "antiemetic", "anti-emetic"):
        intents.add("cinv_management")
        intents.add("clinical_outcomes")
    if not intents:
        intents.add("general_clinical")
    return intents


def retrieval_query(question):
    """Conservative transparent expansion for broad management questions."""
    intents = infer_intent(question)
    q = (question or "").strip()
    if "clinical_management" not in intents:
        return q

    additions = []
    q_lower = q.lower()
    for pattern, synonyms in LOCAL_MANAGEMENT_SYNONYMS:
        if pattern.search(q_lower):
            additions.extend(synonyms)
    additions.extend(MANAGEMENT_EXPANSION_TERMS)

    # Preserve explicit adjunctive intent: don't drown a ginger/acupressure/etc.
    # query in generic standard-care terms, but still add review/trial anchors.
    if explicit_adjunctive_query(q):
        additions = ["randomized trial", "systematic review", "meta-analysis"]

    seen = set(re.findall(r"[a-z0-9]+(?: [a-z0-9]+)*", q_lower))
    unique = []
    for term in additions:
        key = term.lower()
        if key not in seen and key not in unique:
            unique.append(term)
    return " ".join([q] + unique)


def evidence_tier(p):
    t = _text(p)
    pub = (p.get("pubtypes") or "").lower()
    title = _title(p)
    if "guideline" in pub or "practice guideline" in pub or _has(title, "guideline", "guidelines", "consensus", "recommendations"):
        return "guideline_or_consensus", 4.2
    if "meta-analysis" in pub or "meta-analysis" in title or "meta analysis" in title:
        return "meta_analysis", 4.0
    if "systematic review" in pub or "systematic review" in title:
        return "systematic_review", 3.8
    if "randomized controlled trial" in pub or "randomized" in title or "randomised" in title:
        return "randomized_trial", 3.6
    if "cohort" in title or "cohort" in t:
        return "cohort", 2.8
    if "case-control" in title or "case control" in title or "case-control" in t:
        return "case_control", 2.5
    if "review" in pub or "review" in title:
        return "review", 2.0
    if _has(t, "cell", "cells", "mouse", "mice", "rat", "rats", "murine", "in vitro", "pathway", "mechanism"):
        return "mechanistic", 1.0
    if _has(pub, "editorial", "comment", "letter", "news"):
        return "editorial", 0.6
    return "other", 1.2


def intervention_tags(paper):
    """Lightweight evidence/intervention taxonomy for selection metadata."""
    t = _text(paper)
    pub = (paper.get("pubtypes") or "").lower()
    title = _title(paper)
    tags = set()

    if _has(pub, "guideline", "practice guideline", "consensus") or _has(title, "guideline", "consensus", "recommendation"):
        tags.add("guideline_or_consensus")
    if _has(pub, "systematic review", "meta-analysis") or _has(title, "systematic review", "meta-analysis", "meta analysis"):
        tags.add("systematic_review_or_meta_analysis")
    if _has(pub, "randomized controlled trial", "clinical trial") or _has(title, "randomized", "randomised", "controlled trial"):
        tags.add("randomized_trial")
    if _has(pub, "cohort", "case-control", "observational") or _has(t, "cohort", "case-control", "observational"):
        tags.add("observational")
    if _has(t, "cell", "cells", "mouse", "mice", "rat", "rats", "murine", "in vitro", "pathway", "mechanism"):
        tags.add("mechanistic")
    if _has(t, "diagnosis", "diagnostic", "screening", "biomarker"):
        tags.add("diagnostic")
    if _has(t, "risk", "incidence", "prognosis", "prognostic", "survival", "mortality"):
        tags.add("risk_factor")

    if _has(t, "ondansetron", "granisetron", "palonosetron", "5-ht3", "metoclopramide", "dexamethasone", "aprepitant", "fosaprepitant", "nk1", "olanzapine", "drug", "pharmacologic", "pharmacological", "pharmacotherapy", "medication"):
        tags.add("pharmacologic")
    if _has(t, "surgery", "surgical", "procedure", "ablation", "implantation", "stent", "operation"):
        tags.add("procedure_or_surgery")
    if _has(t, "behavioral", "behavioural", "psychological", "cognitive behavioral", "cbt", "hypnosis", "relaxation", "expectancy"):
        tags.add("behavioral_or_psychological")
    if _has(t, "physical therapy", "physiotherapy", "rehabilitation", "exercise", "training", "manual therapy"):
        tags.add("physical_therapy_or_rehab")
    if _has(t, "diet", "dietary", "supplement", "ginger", "vitamin", "omega-3", "fish oil", "nutrition"):
        tags.add("diet_or_supplement")
    if _has(t, "massage", "acupressure", "acupuncture", "moxibustion", "music therapy", "complementary", "alternative"):
        tags.add("complementary_or_alternative")
    if _has(t, "device", "stimulation", "implant", "monitor"):
        tags.add("device")
    return sorted(tags)


def broad_management_review_signal(paper):
    title = _title(paper)
    return _has(title,
        "guideline", "guidelines", "consensus", "recommendations",
        "management of", "optimizing prevention", "prevention and management",
        "treatment of", "therapeutic choices", "clinical practice",
        "standard of care", "place in therapy", "evidence-based review",
    )


def narrow_management_signal(paper):
    title = _title(paper)
    return _has(title,
        "pharmacogenetic", "pharmacogenomic", "protocol", "safety of", "adverse",
        "pediatric", "paediatric", "children", "child", "breakthrough", "refractory",
        "subgroup", "genetic polymorphism", "polymorphisms",
    )


def management_centrality_score(question, paper, tags=None):
    """Estimate centrality for broad clinical management evidence."""
    tags = set(tags or intervention_tags(paper))
    q = (question or "").lower()
    t = _text(paper)
    title = _title(paper)
    score = 0.0

    if "guideline_or_consensus" in tags:
        score += 3.0
    if "systematic_review_or_meta_analysis" in tags:
        score += 2.2
    if "randomized_trial" in tags:
        score += 1.8
    if "pharmacologic" in tags:
        score += 1.2
    if behavioral_central_question(question) and (tags & {"behavioral_or_psychological", "physical_therapy_or_rehab"}):
        score += 1.2
    if broad_management_review_signal(paper):
        score += 2.0
    if _has(title, "treatment", "therapy", "management", "prevention", "guideline", "standard of care", "first-line", "first line"):
        score += 1.0
    elif _has(t, "treatment", "therapy", "management", "prevention", "standard of care", "first-line", "first line"):
        score += 0.5
    if "cinv_management" in infer_intent(question) and pharmacologic_cinv_signal(paper):
        score += 2.0

    adjunctive_tags = {"complementary_or_alternative", "diet_or_supplement"}
    if not behavioral_central_question(question):
        adjunctive_tags.add("behavioral_or_psychological")
    adjunctive = bool(tags & adjunctive_tags)
    if adjunctive and not explicit_adjunctive_query(q):
        score -= 1.8
    if animal_or_cell_only_signal(paper):
        score -= 2.0
    if "mechanistic" in tags and not (tags & {"randomized_trial", "systematic_review_or_meta_analysis", "guideline_or_consensus"}):
        score -= 0.8
    if narrow_management_signal(paper) and not explicit_adjunctive_query(q):
        score -= 1.8
    if _has(title, "pilot", "feasibility"):
        score -= 0.8
    return round(score, 4)


def endpoint_score(question, paper, intents=None):
    intents = intents or infer_intent(question)
    t = _text(paper)
    title = _title(paper)
    score = 0.0
    penalties = []

    if "mechanism" in intents:
        if _has(t, "mechanism", "pathway", "signaling", "signalling", "activation", "ampk", "kinase"):
            score += 2.5
        if _has(t, "cell", "cells", "mouse", "mice", "rat", "rats", "in vitro"):
            score += 0.8

    if "risk_prevention" in intents:
        if _has(t, "risk", "incidence", "incident", "prevention", "prevent", "develop", "chemoprevention"):
            score += 2.0
        if _has(title, "risk", "incidence", "prevention", "prevent"):
            score += 1.0
        if _has(t, "survival", "after diagnosis", "post-diagnosis", "postdiagnosis", "prognos"):
            score -= 2.0
            penalties.append("survival/prognosis endpoint for risk/prevention question")
        if _has(t, "treatment", "therapy", "therapeutic") and not _has(t, "prevention", "prevent", "risk", "incidence"):
            score -= 0.8
            penalties.append("treatment endpoint for risk/prevention question")
        if _has(t, "cell", "cells", "mouse", "mice", "rat", "rats", "in vitro"):
            score -= 0.8
            penalties.append("mechanistic evidence for risk/prevention question")

    if "prognosis_survival" in intents:
        if _has(t, "prognosis", "prognostic", "survival", "mortality", "outcome"):
            score += 2.0
        if _has(title, "prognos", "survival", "mortality"):
            score += 1.0
        if _has(t, "cell", "cells", "in vitro"):
            score -= 0.8
            penalties.append("cell-line evidence for prognosis question")

    if "clinical_management" in intents:
        if _has(t, "treatment", "treat", "therapy", "management", "prevention", "prevent", "control", "guideline", "standard of care", "first line", "first-line"):
            score += 1.6
        if _has(title, "treatment", "therapy", "management", "prevention", "guideline", "recommendation"):
            score += 1.0
        if animal_or_cell_only_signal(paper):
            score -= 2.0
            penalties.append("animal/cell-line evidence for management question")

    if "clinical_outcomes" in intents:
        if _has(t, "outcome", "outcomes", "mortality", "major adverse", "hospitalization", "hospitalisation", "kidney", "renal", "egfr", "cardiovascular", "heart failure", "nausea", "vomiting", "emesis", "antiemetic", "anti-emetic"):
            score += 1.5
        if _has(t, "surrogate", "biomarker"):
            score -= 0.4
            penalties.append("surrogate endpoint")
        if animal_or_cell_only_signal(paper):
            score -= 2.5
            penalties.append("animal/cell-line evidence for clinical outcome question")
        elif _has(t, "cell", "cells", "mouse", "mice", "rat", "rats", "in vitro"):
            score -= 0.7
            penalties.append("mechanistic evidence for clinical outcome question")
        if safety_or_adverse_focus(paper) and not _has((question or "").lower(), "safety", "adverse", "harm", "risk"):
            score -= 1.0
            penalties.append("safety/adverse endpoint for non-safety question")

    if "cinv_management" in intents:
        if _has(t, "chemotherapy", "chemo", "antineoplastic") and _has(t, "nausea", "vomiting", "emesis", "antiemetic", "anti-emetic"):
            score += 2.0
        if pharmacologic_cinv_signal(paper):
            score += 2.6
        if _has(title, "treatment", "prevention", "management", "pharmacotherapy", "medical treatment"):
            score += 1.0
        if nonpharmacologic_cinv_signal(paper) and not _has((question or "").lower(), "non-pharmacologic", "nonpharmacologic", "massage", "acupressure", "acupuncture", "ginger", "behavioral", "behavioural", "hypnosis"):
            score -= 1.8
            penalties.append("non-pharmacologic CINV intervention for broad chemotherapy vomiting question")
        if _has(title, "children", "pediatric", "paediatric") and not _has((question or "").lower(), "child", "children", "pediatric", "paediatric"):
            score -= 1.0
            penalties.append("pediatric CINV evidence for broad/adult-unspecified question")

    return score, penalties


def required_exposure_terms(question):
    """High-value exposure/intervention/entity terms that must stay anchored."""
    q = (question or "").lower()
    groups = []
    patterns = [
        (("metformin",), r"\bmetformin\b"),
        (("aspirin",), r"\baspirin\b"),
        (("statin", "statins"), r"\bstatins?\b"),
        (("vitamin d", "vitamin d3", "cholecalciferol"), r"\bvitamin\s+d\b"),
        (("glp-1", "glp1", "glucagon-like peptide-1", "glucagon like peptide 1"), r"\bglp\s*-?\s*1\b|glucagon.like peptide.1"),
        (("beta blocker", "beta blockers", "beta-blocker", "beta-blockers"), r"\bbeta[- ]blockers?\b"),
        (("sglt2", "sglt-2", "sodium-glucose cotransporter-2", "sodium glucose cotransporter 2"), r"\bsglt\s*-?\s*2\b|sodium.glucose.*cotransporter.2"),
        (("omega-3", "omega 3", "n-3", "fish oil", "epa", "docosahexaenoic", "eicosapentaenoic"), r"\bomega\s*-?\s*3\b|\bn-3\b|fish oil"),
        (("ketogenic diet", "ketogenic"), r"\bketogenic\b"),
        (("exercise", "training", "physical activity"), r"\bexercise\b|physical activity"),
        (("p53", "tp53"), r"\bp53\b|\btp53\b"),
    ]
    for terms, pattern in patterns:
        if re.search(pattern, q):
            groups.append(terms)
    return groups


def exposure_score(question, paper):
    groups = required_exposure_terms(question)
    if not groups:
        return 0.0, []
    t = _text(paper)
    title = _title(paper)
    score = 0.0
    penalties = []
    for group in groups:
        present = any(term in t for term in group)
        title_present = any(term in title for term in group)
        if title_present:
            score += 1.5
        elif present:
            score += 0.8
        else:
            score -= 4.0
            penalties.append("missing required exposure/entity term: " + "/".join(group[:3]))
    return score, penalties


def population_score(question, paper):
    q = (question or "").lower()
    t = _text(paper)
    title = _title(paper)
    score = 0.0
    penalties = []
    if "adult" in q:
        if _has(title, "adult", "adults"):
            score += 1.8
        elif _has(t, "adult", "adults"):
            score += 1.2
        if _has(title, "child", "children", "pediatric", "paediatric") and not _has(title, "adult", "adults"):
            score -= 5.0
            penalties.append("pediatric title for adult question")
        elif _has(t, "child", "children", "pediatric", "paediatric") and not _has(t, "adult", "adults"):
            score -= 3.0
            penalties.append("pediatric population for adult question")
        elif _has(title, "child", "children", "pediatric", "paediatric", "adolescent"):
            score -= 2.5
            penalties.append("mixed/younger title for adult question")
        elif _has(t, "child", "children", "pediatric", "paediatric", "adolescent"):
            score -= 1.5
            penalties.append("mixed/younger population for adult question")
    if "diabetes" in q or "sglt2" in q or "metformin" in q:
        if _has(t, "diabetes", "diabetic", "type 2"):
            score += 0.5
    if "chronic kidney" in q or "kidney" in q or "renal" in q:
        if _has(t, "kidney", "renal", "ckd", "egfr"):
            score += 0.5
    return score, penalties


def conflict_signal(paper):
    t = _text(paper)
    return bool(_has_re(t, r"\b(no|not|neither|lack of|failed to|did not|does not|without)\b") and
                _has(t, "benefit", "association", "significant", "reduce", "reduction", "effective", "effect"))


def animal_or_cell_only_signal(paper):
    """Likely animal/cell-line evidence with no clear human/clinical framing."""
    t = _text(paper)
    title = _title(paper)
    title_preclinical = _has(title, "mouse", "mice", "rat", "rats", "murine", "cell", "cells", "in vitro")
    title_human = _has(title, "human", "humans", "patient", "patients", "adult", "adults", "cohort", "trial", "clinical", "meta-analysis", "systematic review")
    if title_preclinical and not title_human:
        return True
    has_preclinical = _has(t, "cell", "cells", "mouse", "mice", "rat", "rats", "murine", "in vitro")
    has_human = _has(t, "human", "humans", "patient", "patients", "adult", "adults", "cohort", "trial", "clinical", "meta-analysis", "systematic review")
    return bool(has_preclinical and not has_human)


def safety_or_adverse_focus(paper):
    title = _title(paper)
    return _has(title, "safety", "adverse", "toxicity", "arterial stiffness", "endothelial function", "vascular", "morphology")


def pharmacologic_cinv_signal(paper):
    """Pharmacologic/antiemetic chemotherapy-induced nausea/vomiting evidence."""
    t = _text(paper)
    title = _title(paper)
    if _has(title, "massage", "acupressure", "acupuncture", "moxibustion", "ginger", "hypnosis", "relaxation", "music therapy", "behavioral", "behavioural", "expectancy", "psychological"):
        return False
    drug_signal = _has(
        t,
        "ondansetron", "granisetron", "palonosetron", "5-ht3", "5 ht3",
        "serotonin antagonist", "metoclopramide", "dexamethasone", "corticosteroid",
        "aprepitant", "fosaprepitant", "nk1", "neurokinin", "olanzapine",
        "prochlorperazine", "droperidol", "propofol",
    )
    management_title = _has(title, "pharmacotherapy", "medical treatment", "antiemetic", "anti-emetic")
    treatment_title = _has(title, "treatment", "prevention", "management") and _has(title, "chemotherapy", "nausea", "vomiting", "emesis")
    return bool(drug_signal or management_title or treatment_title)


def nonpharmacologic_cinv_signal(paper):
    """Non-drug supportive interventions that should not dominate broad CINV answers."""
    t = _text(paper)
    return _has(
        t,
        "massage", "acupressure", "acupuncture", "moxibustion", "ginger",
        "hypnosis", "relaxation", "music therapy", "behavioral intervention",
        "behavioural intervention", "expectancy", "psychological intervention",
    )


def _norm_title(title):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (title or "").lower())).strip()


def _too_similar(paper, selected, threshold=0.90):
    title = _norm_title(paper.get("title"))
    if not title:
        return False
    for s in selected:
        st = _norm_title(s.get("title"))
        if st and SequenceMatcher(None, title, st).ratio() >= threshold:
            return True
    return False


def score_paper(question, paper):
    intents = infer_intent(question)
    tier, tier_score = evidence_tier(paper)
    tags = intervention_tags(paper)
    centrality = management_centrality_score(question, paper, tags) if "clinical_management" in intents else 0.0
    exposure, exposure_penalties = exposure_score(question, paper)
    endpoint, endpoint_penalties = endpoint_score(question, paper, intents=intents)
    pop, pop_penalties = population_score(question, paper)
    retrieval = float(paper.get("score") or 0.0)
    impact = float(paper.get("impact_score") or 0.0)
    direct = tier_score + exposure + endpoint + pop + min(retrieval, 2.0) * 0.35 + impact * 0.25
    if "clinical_management" in intents:
        direct += centrality

    # For clinical questions, keep mechanistic evidence available but below direct human evidence.
    if "mechanism" not in intents and tier == "mechanistic":
        direct -= 1.5
    if tier == "editorial":
        direct -= 1.0

    return {
        "pmid": paper.get("pmid"),
        "score": round(direct, 4),
        "evidence_tier": tier,
        "tier_score": tier_score,
        "exposure_score": round(exposure, 4),
        "endpoint_score": round(endpoint, 4),
        "population_score": round(pop, 4),
        "intervention_tags": tags,
        "management_centrality_score": centrality,
        "conflict_signal": conflict_signal(paper),
        "penalties": exposure_penalties + endpoint_penalties + pop_penalties,
        "intents": sorted(intents),
    }


def select_evidence(question, papers, max_papers=8, min_papers=4):
    """Return a curated subset of retrieved papers for answer generation.

    The selector favors direct endpoint/population/evidence-tier matches and keeps
    limited diversity/conflict. It does not fetch new papers or call an LLM.
    """
    if not papers:
        return []
    if max_papers <= 0:
        return []

    scored = []
    for p in papers:
        meta = score_paper(question, p)
        scored.append((meta["score"], meta, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    intents = infer_intent(question)
    selected = []
    selected_pmids = set()

    def add(meta, p):
        if p.get("pmid") in selected_pmids:
            return False
        penalties = meta.get("penalties", [])
        if any(str(x).startswith("missing required exposure/entity term") for x in penalties):
            return False
        if "pediatric title for adult question" in penalties:
            return False
        if _too_similar(p, selected):
            return False
        q = dict(p)
        q["evidence_selection"] = meta
        selected.append(q)
        selected_pmids.add(p.get("pmid"))
        return True

    # First pass: strongest direct evidence.
    for _, meta, p in scored:
        if len(selected) >= max_papers:
            break
        add(meta, p)

    # Ensure at least one conflict/null study when available and not already selected.
    if len(selected) < max_papers and not any((s.get("evidence_selection") or {}).get("conflict_signal") for s in selected):
        for _, meta, p in scored:
            if meta["conflict_signal"] and meta["evidence_tier"] != "editorial":
                add(meta, p)
                break

    def is_adjunctive(p):
        tags = set((p.get("evidence_selection") or {}).get("intervention_tags") or intervention_tags(p))
        adjunctive_tags = {"complementary_or_alternative", "diet_or_supplement"}
        if not behavioral_central_question(question):
            adjunctive_tags.add("behavioral_or_psychological")
        return bool(tags & adjunctive_tags) and "pharmacologic" not in tags

    # For clinical questions, avoid overloading generation with mechanistic evidence.
    # For CINV management, pharmacologic/antiemetic papers are clinically relevant
    # even when the title/abstract heuristic labels them as mechanistic.
    mech_cap = max_papers
    if "mechanism" not in intents:
        if "cinv_management" in intents:
            clinical = [p for p in selected if (p.get("evidence_selection") or {}).get("evidence_tier") != "mechanistic" or pharmacologic_cinv_signal(p)]
            mech = [p for p in selected if (p.get("evidence_selection") or {}).get("evidence_tier") == "mechanistic" and not pharmacologic_cinv_signal(p)]
            nonpharm_cap = 1 if any(pharmacologic_cinv_signal(p) for p in clinical) else 2
            kept = []
            nonpharm_n = 0
            for p in clinical:
                if nonpharmacologic_cinv_signal(p) and not pharmacologic_cinv_signal(p):
                    if nonpharm_n >= nonpharm_cap:
                        continue
                    nonpharm_n += 1
                kept.append(p)
            clinical = kept
        else:
            clinical = [p for p in selected if (p.get("evidence_selection") or {}).get("evidence_tier") != "mechanistic"]
            mech = [p for p in selected if (p.get("evidence_selection") or {}).get("evidence_tier") == "mechanistic"]
        if len(clinical) >= 2 and not _has((question or "").lower(), "safety", "adverse", "harm", "risk"):
            clinical = [p for p in clinical if not safety_or_adverse_focus(p)]
        mech_cap = 1 if len(clinical) >= 2 else 2
        if len(clinical) >= 2:
            mech = [p for p in mech if not animal_or_cell_only_signal(p)]
        selected = clinical + mech[:mech_cap]

    # For broad management questions, adjunctive/complementary/supplement/behavioral
    # papers and narrow subgroup/special-scenario papers can be included but should
    # not dominate unless explicitly requested.
    if "clinical_management" in intents and not explicit_adjunctive_query(question):
        broad_or_core = [p for p in selected if not narrow_management_signal(p)]
        narrow = [p for p in selected if narrow_management_signal(p)]
        narrow_cap = 1 if len(broad_or_core) >= 4 else 2
        selected = broad_or_core + narrow[:narrow_cap]

        central = [p for p in selected if not is_adjunctive(p)]
        adjunctive = [p for p in selected if is_adjunctive(p)]
        adjunct_cap = 2 if len(central) >= 4 else 1 if central else 2
        selected = central + adjunctive[:adjunct_cap]

    # If pruning dropped too many, backfill by score while preserving clinical caps.
    selected_pmids = {p.get("pmid") for p in selected}
    for _, meta, p in scored:
        if len(selected) >= min(max_papers, max(min_papers, len(papers))):
            break
        if p.get("pmid") in selected_pmids:
            continue
        penalties = meta.get("penalties", [])
        if any(str(x).startswith("missing required exposure/entity term") for x in penalties):
            continue
        if "pediatric title for adult question" in penalties:
            continue
        if "mechanism" not in intents:
            current_mech = sum(1 for s in selected if (s.get("evidence_selection") or {}).get("evidence_tier") == "mechanistic")
            is_cinv_pharm = "cinv_management" in intents and pharmacologic_cinv_signal(p)
            if meta.get("evidence_tier") == "mechanistic" and current_mech >= mech_cap and not is_cinv_pharm:
                continue
            if "cinv_management" in intents and nonpharmacologic_cinv_signal(p) and not pharmacologic_cinv_signal(p):
                current_nonpharm = sum(1 for s in selected if nonpharmacologic_cinv_signal(s) and not pharmacologic_cinv_signal(s))
                if current_nonpharm >= 1 and any(pharmacologic_cinv_signal(s) for s in selected):
                    continue
            if animal_or_cell_only_signal(p) and len(selected) >= 2:
                continue
            if safety_or_adverse_focus(p) and len(selected) >= 2 and not _has((question or "").lower(), "safety", "adverse", "harm", "risk"):
                continue
            if "clinical_management" in intents and not explicit_adjunctive_query(question):
                current_central = sum(1 for s in selected if not is_adjunctive(s))
                current_adjunctive = sum(1 for s in selected if is_adjunctive(s))
                adj_cap = 2 if current_central >= 4 else 1 if current_central else 2
                candidate_tags = set(meta.get("intervention_tags") or [])
                adj_tags = {"complementary_or_alternative", "diet_or_supplement"}
                if not behavioral_central_question(question):
                    adj_tags.add("behavioral_or_psychological")
                candidate_adjunctive = bool(candidate_tags & adj_tags) and "pharmacologic" not in candidate_tags
                if candidate_adjunctive and current_adjunctive >= adj_cap:
                    continue
                current_broad = sum(1 for s in selected if not narrow_management_signal(s))
                current_narrow = sum(1 for s in selected if narrow_management_signal(s))
                narrow_cap = 1 if current_broad >= 4 else 2
                if narrow_management_signal(p) and current_narrow >= narrow_cap:
                    continue
        q = dict(p)
        q["evidence_selection"] = meta
        selected.append(q)
        selected_pmids.add(p.get("pmid"))

    return selected[:max_papers]
