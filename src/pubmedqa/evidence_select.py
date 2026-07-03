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


def infer_intent(question):
    q = (question or "").lower()
    intents = set()
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
    if not intents:
        intents.add("general_clinical")
    return intents


def evidence_tier(p):
    t = _text(p)
    pub = (p.get("pubtypes") or "").lower()
    title = _title(p)
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

    if "clinical_outcomes" in intents:
        if _has(t, "outcome", "outcomes", "mortality", "major adverse", "hospitalization", "hospitalisation", "kidney", "renal", "egfr", "cardiovascular", "heart failure"):
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
    exposure, exposure_penalties = exposure_score(question, paper)
    endpoint, endpoint_penalties = endpoint_score(question, paper, intents=intents)
    pop, pop_penalties = population_score(question, paper)
    retrieval = float(paper.get("score") or 0.0)
    impact = float(paper.get("impact_score") or 0.0)
    direct = tier_score + exposure + endpoint + pop + min(retrieval, 2.0) * 0.35 + impact * 0.25

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

    # For clinical questions, avoid overloading generation with mechanistic evidence.
    mech_cap = max_papers
    if "mechanism" not in intents:
        clinical = [p for p in selected if (p.get("evidence_selection") or {}).get("evidence_tier") != "mechanistic"]
        mech = [p for p in selected if (p.get("evidence_selection") or {}).get("evidence_tier") == "mechanistic"]
        if len(clinical) >= 2 and not _has((question or "").lower(), "safety", "adverse", "harm", "risk"):
            clinical = [p for p in clinical if not safety_or_adverse_focus(p)]
        mech_cap = 1 if len(clinical) >= 2 else 2
        if len(clinical) >= 2:
            mech = [p for p in mech if not animal_or_cell_only_signal(p)]
        selected = clinical + mech[:mech_cap]

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
            if meta.get("evidence_tier") == "mechanistic" and current_mech >= mech_cap:
                continue
            if animal_or_cell_only_signal(p) and len(selected) >= 2:
                continue
            if safety_or_adverse_focus(p) and len(selected) >= 2 and not _has((question or "").lower(), "safety", "adverse", "harm", "risk"):
                continue
        q = dict(p)
        q["evidence_selection"] = meta
        selected.append(q)
        selected_pmids.add(p.get("pmid"))

    return selected[:max_papers]
