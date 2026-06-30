"""Hybrid retrieval: BM25 (FTS5) + dense (LanceDB) -> RRF -> bounded citation re-score.

v1 is lean: no cross-encoder. Citation impact is a *bounded booster* applied only
after a relevance gate, so a famous-but-off-topic paper can't surface (plan §5E).
"""
import math
import re
from datetime import datetime
from difflib import SequenceMatcher
from functools import lru_cache
from . import config, db, embed, vectorstore
from .generate import _load_mlx


_STOPWORDS = {
    "and", "or", "the", "for", "with", "without", "from", "into", "does",
    "do", "did", "use", "using", "risk", "risks", "study", "studies", "effect",
    "effects", "may", "might", "can", "could", "help", "helps", "reduce",
    "reduced", "reducing", "association", "associated", "patient", "patients",
}

# Small but high-value biomedical alias map.  These short symbols are easy to
# drop with generic token-length filters, but losing them can turn a precise
# query ("p53 mutation...") into a broad one ("mutation cancer prognosis").
_BIOMED_ENTITY_ALIASES = {
    "p53": ("p53", "tp53"),
    "tp53": ("p53", "tp53"),
    "her2": ("her2", "erbb2"),
    "erbb2": ("her2", "erbb2"),
    "pd1": ("pd1", "pd 1", "pd-1", "pdcd1"),
    "pdcd1": ("pd1", "pd 1", "pd-1", "pdcd1"),
    "pdl1": ("pdl1", "pd l1", "pd-l1", "cd274"),
    "cd274": ("pdl1", "pd l1", "pd-l1", "cd274"),
    "egfr": ("egfr", "erbb1"),
    "erbb1": ("egfr", "erbb1"),
}


def _is_biomed_short_token(tok):
    """Keep short biomedical symbols such as p53, il6, cd4, b7, etc."""
    return len(tok) >= 2 and any(c.isalpha() for c in tok) and any(c.isdigit() for c in tok)


def _query_terms(text):
    toks = [t for t in re.findall(r"[A-Za-z0-9]+", text.lower())
            if len(t) > 3 or _is_biomed_short_token(t)]
    return [t for t in toks if t not in _STOPWORDS]


def _expand_alias_terms(terms):
    out = []
    seen = set()
    for t in terms:
        aliases = _BIOMED_ENTITY_ALIASES.get(t, (t,))
        for a in aliases:
            # FTS tokenization will split punctuation, so query the compact form.
            compact = re.sub(r"[^a-z0-9]+", "", a.lower())
            if compact and compact not in seen:
                seen.add(compact)
                out.append(compact)
    return out


def _fts_query(text):
    """Build a safe FTS5 MATCH string: OR of quoted salient tokens."""
    toks = _expand_alias_terms(_query_terms(text))
    return " OR ".join(f'"{t}"' for t in toks) if toks else None


def _content_text(paper):
    return f"{paper.get('title','')} {paper.get('abstract','')}".strip().lower()


def _overlap_count(text, terms):
    if not terms:
        return 0
    return sum(1 for t in terms if t in text)


def _phrase_key(text):
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _phrase_present(text, phrase):
    key = f" {_phrase_key(text)} "
    pkey = _phrase_key(phrase)
    return bool(pkey) and f" {pkey} " in key


def _required_exact_phrases(question, focus):
    """Return query phrases where loose token matching is unsafe.

    Example: for "vitamin D supplementation...", matching only "vitamin" promotes
    vitamin A/C papers. Require the exact vitamin form when the question names one.
    """
    phrases = []
    for m in re.finditer(r"\bvitamin\s+([a-z0-9]+)\b", question.lower()):
        phrases.append(f"vitamin {m.group(1)}")
    # Also honor any extracted focus phrase that repeats one of these exact forms.
    for term in focus or []:
        if re.fullmatch(r"vitamin\s+[a-z0-9]+", term.lower()) and term.lower() not in phrases:
            phrases.append(term.lower())
    return phrases


def _required_entity_groups(question, focus):
    """Return alias groups that must be present in candidate text.

    If the query names a specific biomedical symbol/gene, require a match to that
    entity or one of its aliases. This prevents p53/TP53 queries from degrading to
    generic mutation/prognosis retrieval.
    """
    text = f"{question or ''} {' '.join(focus or [])}".lower()
    compact_tokens = set(re.findall(r"[a-z0-9]+", text))
    groups = []
    seen = set()
    for key, aliases in _BIOMED_ENTITY_ALIASES.items():
        alias_compacts = {re.sub(r"[^a-z0-9]+", "", a.lower()) for a in aliases}
        if compact_tokens & alias_compacts or any(_phrase_present(text, a) for a in aliases):
            canonical = tuple(sorted(alias_compacts))
            if canonical not in seen:
                seen.add(canonical)
                groups.append(tuple(a.lower() for a in aliases))
    return groups


def _entity_group_present(text, aliases):
    return any(_phrase_present(text, alias) for alias in aliases)


def _required_concept_groups(question):
    """Return endpoint concept stems that should survive broad lexical matching."""
    text = (question or "").lower()
    groups = []
    if re.search(r"\bprognos(?:is|tic)?\b", text):
        groups.append(("prognos", "survival", "outcome", "mortality"))
    return groups


def _concept_group_present(text, stems):
    text = (text or "").lower()
    return any(stem in text for stem in stems)


def _strict_fts_query(required_entities, required_concepts):
    """Build an AND query for required entity/concept groups.

    This provides a lexical anchor for exact biomedical symbols plus endpoint
    concepts, while the normal OR query still supplies broad recall.
    """
    groups = []
    for aliases in required_entities:
        toks = sorted({re.sub(r"[^a-z0-9]+", "", a.lower()) for a in aliases})
        toks = [t for t in toks if t]
        if toks:
            groups.append("(" + " OR ".join(f'\"{t}\"' for t in toks) + ")")
    for stems in required_concepts:
        toks = []
        if "prognos" in stems:
            toks.extend(["prognosis", "prognostic", "survival", "outcome", "mortality"])
        else:
            toks.extend(stems)
        toks = sorted({re.sub(r"[^a-z0-9]+", "", t.lower()) for t in toks if t})
        if toks:
            groups.append("(" + " OR ".join(f'\"{t}\"' for t in toks) + ")")
    return " AND ".join(groups) if len(groups) >= 2 else None


def _norm_title(title):
    title = (title or "").lower()
    title = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", title)).strip()
    return title


def _title_tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def _title_similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _is_duplicate(candidate, kept):
    ctitle = _norm_title(candidate.get("title", ""))
    if not ctitle:
        return True
    cabs = (candidate.get("abstract") or "").strip().lower()
    if len(ctitle) < 8 and len(cabs) < 40:
        return True
    ctoks = _title_tokens(ctitle)
    for k in kept:
        ktitle = _norm_title(k.get("title", ""))
        if not ktitle:
            continue
        if ctitle == ktitle:
            return True
        if _title_similarity(ctitle, ktitle) >= config.DEDUP_TITLE_SIM:
            return True
        ktoks = _title_tokens(ktitle)
        if ctoks and ktoks:
            j = len(ctoks & ktoks) / max(1, len(ctoks | ktoks))
            if j >= config.DEDUP_TOKEN_JACCARD:
                return True
    return False


@lru_cache(maxsize=256)
def _focus_terms(question):
    if not config.KEYWORD_FILTER_ENABLED:
        return []
    try:
        model, tokenizer = _load_mlx()
        try:
            from mlx_lm import generate as mlx_generate
            from mlx_lm.sample_utils import make_sampler
        except ImportError:
            raise RuntimeError("mlx-lm not installed")
        messages = [
            {"role": "system", "content": (
                "Extract the 1 or 2 most important search keywords from a medical question. "
                "Prefer a disease name and a drug/intervention name when both are present. "
                "Return only lowercase keywords or short noun phrases separated by commas. "
                "Do not explain, and do not include filler words."
            )},
            {"role": "user", "content": f"Question: {question}"},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        text = mlx_generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=16,
            sampler=make_sampler(temp=0.0),
            verbose=False,
        ).strip().lower()
        terms = [t.strip(" .,:;\n\t") for t in re.split(r"[,;/]+", text) if t.strip()]
        cleaned = []
        for t in terms:
            t = re.sub(r"[^a-z0-9\-\s]", "", t).strip()
            if 2 <= len(t) <= 40:
                cleaned.append(t)
        if cleaned:
            # Prefer a disease + drug/intervention pair if the model provided one.
            disease_like = [t for t in cleaned if any(x in t for x in (
                "cancer", "diabetes", "disease", "syndrome", "tumor", "tumour",
                "carcin", "cardio", "obesity", "arthritis", "asthma", "infection",
                "metformin", "insulin", "aspirin", "statin", "drug", "therapy",
                "treatment", "vaccine", "metast", "prostate", "breast", "gastric",
                "colorectal", "esophageal", "oesophageal",
            ))]
            if len(disease_like) >= 2:
                return disease_like[:2]
            if len(disease_like) == 1:
                others = [t for t in cleaned if t != disease_like[0]]
                return [disease_like[0]] + others[:1]
            return cleaned[:2]
    except Exception:
        pass

    # heuristic fallback
    toks = [t for t in re.findall(r"[A-Za-z0-9]+", question.lower()) if len(t) > 3]
    stop = {
        "and", "or", "the", "for", "with", "without", "from", "into", "does", "do",
        "did", "use", "using", "risk", "risks", "study", "studies", "effect",
        "effects", "may", "might", "can", "could", "help", "helps", "reduce",
        "reduced", "reducing", "association", "associated", "patient", "patients",
    }
    toks = [t for t in toks if t not in stop]
    return toks[:2]


def _rrf(rank_lists, k=config.RRF_K):
    scores = {}
    for ranks in rank_lists:
        for pos, pmid in enumerate(ranks):
            scores[pmid] = scores.get(pmid, 0.0) + 1.0 / (k + pos + 1)
    return scores


def _paper_age_years(paper):
    year = paper.get("year")
    try:
        year = int(year)
    except Exception:
        return None
    current = datetime.now().year
    if year < 1800 or year > current + 1:
        return None
    return max(0.5, current - year + 1)


def _recency_norm(paper):
    """Map publication recency to 0..1, with recent papers protected from zero-citation bias."""
    age = _paper_age_years(paper)
    if age is None:
        return config.IMPACT_FLOOR
    return max(config.IMPACT_FLOOR, min(1.0, math.exp(-age / config.RECENCY_HALF_LIFE_YEARS)))


def _citation_rate_norm(cit, paper):
    """Age-adjusted citation signal so recent papers are not unfairly penalized."""
    if not cit or cit.get("citation_count") is None:
        return config.IMPACT_FLOOR
    age = _paper_age_years(paper) or 1.0
    rate = max(0.0, float(cit.get("citation_count") or 0)) / age
    return max(
        config.IMPACT_FLOOR,
        min(1.0, math.log1p(rate) / math.log1p(config.CITATION_RATE_TARGET_PER_YEAR)),
    )


def _rcr_or_citation_norm(cit):
    """Map raw impact to 0..1. RCR preferred; else log citation count."""
    if not cit:
        return config.IMPACT_FLOOR
    rcr = cit.get("rcr")
    if rcr is not None:
        return 1.0 / (1.0 + math.exp(-(rcr - 1.0)))   # sigmoid centered at field median
    c = cit.get("citation_count")
    if c is not None:
        return max(config.IMPACT_FLOOR, min(1.0, math.log1p(c) / math.log1p(1000)))
    return config.IMPACT_FLOOR


def _impact_norm(cit, paper=None):
    """Citation+recency impact score in 0..1.

    Combines field-normalized impact (RCR when available), citation velocity, and
    publication recency. This preserves the v1 principle that impact is only a
    bounded secondary booster while avoiding a hard bias against recent papers
    that have not had time to accumulate citations.
    """
    paper = paper or {}
    base = _rcr_or_citation_norm(cit)
    rate = _citation_rate_norm(cit, paper)
    recency = _recency_norm(paper)
    score = (
        config.IMPACT_RCR_WEIGHT * base
        + config.IMPACT_CITATION_RATE_WEIGHT * rate
        + config.IMPACT_RECENCY_WEIGHT * recency
    )
    return max(config.IMPACT_FLOOR, min(1.0, score))


def _evidence_text(paper):
    return f"{paper.get('pubtypes', '')} {paper.get('title', '')}".lower()


def _is_clinical_query(question):
    text = (question or "").lower()
    return any(t in text for t in (
        "risk", "reduce", "reduced", "prevent", "prevention", "incidence",
        "outcome", "outcomes", "mortality", "survival", "prognosis", "prognostic", "supplementation",
        "primary prevention", "secondary prevention", "cardiovascular", "dementia",
        "infection", "infections",
    ))


def _is_mechanisticish(text):
    text = (text or "").lower()
    return any(t in text for t in (
        "cell", "cells", "cell line", "proliferation", "migration", "apoptosis",
        "tumor growth", "tumour growth", "xenograft", "mice", "mouse", "murine",
        "rat", "rats", "pathway", "mechanism", "mitochondrial", "expression",
        "upregulation", "downregulation", "in vitro", "in vivo",
    ))


def _evidence_type_boost(pubtypes_text, clinical_query=False):
    text = (pubtypes_text or "").lower()
    multiplier = config.CLINICAL_QUERY_EVIDENCE_MULTIPLIER if clinical_query else 1.0
    score = 0.0
    if any(t in text for t in ("systematic review", "meta-analysis", "metaanalysis")):
        score += config.EVIDENCE_TYPE_BONUS * multiplier
    if any(t in text for t in ("randomized", "randomised", "clinical trial", "controlled trial", "cohort", "case-control")):
        score += config.EVIDENCE_TYPE_BONUS * 0.8 * multiplier
    if any(t in text for t in ("review", "overview")):
        score += config.EVIDENCE_TYPE_BONUS * 0.4 * multiplier
    if clinical_query and _is_mechanisticish(text):
        score -= config.CLINICAL_QUERY_MECH_PENALTY
    if any(t in text for t in ("case report", "case series")):
        score -= config.EVIDENCE_TYPE_PENALTY * 1.2
    return max(-0.15, min(0.15, score))


def _is_clinicalish(pubtypes_text):
    text = (pubtypes_text or "").lower()
    return any(t in text for t in (
        "systematic review", "meta-analysis", "metaanalysis", "randomized", "randomised",
        "clinical trial", "controlled trial", "cohort", "case-control", "review", "overview",
    ))


def _with_context_group(paper):
    group = "clinical/review" if _is_clinicalish(_evidence_text(paper)) else "mechanistic/other"
    return {**paper, "context_group": group}


def _balanced_context(papers, top_n, clinical_query=False):
    clinical = []
    mech = []
    for p in papers:
        if _is_clinicalish(_evidence_text(p)):
            clinical.append(p)
        else:
            mech.append(p)
    clinical_quota = config.CLINICAL_QUERY_CLINICAL_QUOTA if clinical_query else config.BALANCED_CONTEXT_CLINICAL_QUOTA
    mech_quota = config.CLINICAL_QUERY_MECH_QUOTA if clinical_query else config.BALANCED_CONTEXT_MECH_QUOTA
    clinical = clinical[:clinical_quota]
    mech = mech[:mech_quota]

    out = []
    seen = set()
    for bucket in (clinical, mech):
        for p in bucket:
            pmid = p.get("pmid")
            if pmid in seen:
                continue
            seen.add(pmid)
            out.append(_with_context_group(p))
            if len(out) >= top_n:
                return out
    for p in papers:
        pmid = p.get("pmid")
        if pmid in seen:
            continue
        seen.add(pmid)
        out.append(_with_context_group(p))
        if len(out) >= top_n:
            break
    return out


def search(con, question, top_n=config.TOP_N_CONTEXT):
    terms = _query_terms(question)
    focus = _focus_terms(question)
    required_phrases = _required_exact_phrases(question, focus)
    required_entities = _required_entity_groups(question, focus)
    required_concepts = _required_concept_groups(question)
    clinical_query = _is_clinical_query(question)
    qv = embed.embed_query(question)
    dense = vectorstore.search(qv, config.DENSE_TOPK)

    ftsq = _fts_query(question)
    lexical = db.bm25_search(con, ftsq, config.BM25_TOPK) if ftsq else []

    strict_lexical = []
    strictq = _strict_fts_query(required_entities, required_concepts)
    if strictq:
        strict_lexical = db.bm25_search(con, strictq, config.BM25_TOPK)

    focus_lexical = []
    if focus:
        fts_focus = _fts_query(" ".join(focus))
        if fts_focus:
            focus_lexical = db.bm25_search(con, fts_focus, config.BM25_TOPK)

    fused = _rrf([dense, lexical, focus_lexical, strict_lexical, strict_lexical])
    if not fused:
        return []

    hi = max(fused.values())
    cits = db.fetch_citations(con, list(fused.keys()))
    papers = db.fetch_papers(con, list(fused.keys()))

    ranked = []
    for pmid, s in fused.items():
        p = papers.get(pmid, {})
        content = _content_text(p)
        if len(content) < 40:
            continue
        overlap = _overlap_count(content, terms)
        focus_overlap = _overlap_count(content, focus)
        rel = s / hi if hi > 0 else 0.0
        title_text = (p.get("title") or "").lower()
        entity_overlap = sum(1 for aliases in required_entities if _entity_group_present(content, aliases))
        concept_overlap = sum(1 for stems in required_concepts if _concept_group_present(content, stems))
        title_entity_overlap = sum(1 for aliases in required_entities if _entity_group_present(title_text, aliases))
        title_concept_overlap = sum(1 for stems in required_concepts if _concept_group_present(title_text, stems))
        if required_phrases and not all(_phrase_present(content, phrase) for phrase in required_phrases):
            continue
        if required_entities and entity_overlap < len(required_entities):
            continue
        if required_concepts and concept_overlap < len(required_concepts):
            continue
        if focus and focus_overlap == 0 and rel < config.KEYWORD_FILTER_MIN_REL:
            continue
        if terms and overlap < config.QUERY_OVERLAP_MIN and rel < 0.55:
            continue
        pub_boost = _evidence_type_boost(_evidence_text(p), clinical_query=clinical_query)
        final = rel if rel < config.RELEVANCE_GATE else (
            rel
            + config.ALPHA * _impact_norm(cits.get(pmid), p)
            + (overlap * config.QUERY_OVERLAP_BONUS)
            + (focus_overlap * config.KEYWORD_FILTER_BONUS)
            + (entity_overlap * config.KEYWORD_FILTER_BONUS * 2.0)
            + (concept_overlap * config.KEYWORD_FILTER_BONUS)
            + (title_entity_overlap * config.KEYWORD_FILTER_BONUS)
            + (title_concept_overlap * config.KEYWORD_FILTER_BONUS)
            + pub_boost
        )
        ranked.append((pmid, final, rel, overlap, focus_overlap, pub_boost))
    ranked.sort(key=lambda x: x[1], reverse=True)

    deduped = []
    for pmid, final, rel, overlap, focus_overlap, pub_boost in ranked:
        p = papers.get(pmid, {"pmid": pmid})
        if _is_duplicate(p, [r for r in deduped]):
            continue
        c = cits.get(pmid, {})
        deduped.append({**p, "pmid": pmid, "score": final, "relevance": rel,
                        "overlap": overlap, "focus_overlap": focus_overlap,
                        "pub_boost": pub_boost,
                        "impact_score": _impact_norm(c, p),
                        "recency_score": _recency_norm(p),
                        "citation_rate_score": _citation_rate_norm(c, p),
                        "citation_count": c.get("citation_count"), "rcr": c.get("rcr")})
        candidate_pool = top_n * 4 if clinical_query else top_n * 2
        if len(deduped) >= candidate_pool:
            break
    return _balanced_context(deduped, top_n, clinical_query=clinical_query)
