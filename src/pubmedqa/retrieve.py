"""Hybrid retrieval: BM25 (FTS5) + dense (LanceDB) -> RRF -> bounded citation re-score.

v1 is lean: no cross-encoder. Citation impact is a *bounded booster* applied only
after a relevance gate, so a famous-but-off-topic paper can't surface (plan §5E).
"""
import math
import re
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


def _query_terms(text):
    toks = [t for t in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(t) > 3]
    return [t for t in toks if t not in _STOPWORDS]


def _fts_query(text):
    """Build a safe FTS5 MATCH string: OR of quoted salient tokens."""
    toks = _query_terms(text)
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


def _impact_norm(cit):
    """Map impact to 0..1. RCR (field-normalized) preferred; else log citations."""
    if not cit:
        return config.IMPACT_FLOOR
    rcr = cit.get("rcr")
    if rcr is not None:
        return 1.0 / (1.0 + math.exp(-(rcr - 1.0)))   # sigmoid centered at field median
    c = cit.get("citation_count")
    if c is not None:
        return max(config.IMPACT_FLOOR, min(1.0, math.log1p(c) / math.log1p(1000)))
    return config.IMPACT_FLOOR


def _evidence_text(paper):
    return f"{paper.get('pubtypes', '')} {paper.get('title', '')}".lower()


def _is_clinical_query(question):
    text = (question or "").lower()
    return any(t in text for t in (
        "risk", "reduce", "reduced", "prevent", "prevention", "incidence",
        "outcome", "outcomes", "mortality", "survival", "supplementation",
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
    clinical_query = _is_clinical_query(question)
    qv = embed.embed_query(question)
    dense = vectorstore.search(qv, config.DENSE_TOPK)

    ftsq = _fts_query(question)
    lexical = db.bm25_search(con, ftsq, config.BM25_TOPK) if ftsq else []

    focus_lexical = []
    if focus:
        fts_focus = _fts_query(" ".join(focus))
        if fts_focus:
            focus_lexical = db.bm25_search(con, fts_focus, config.BM25_TOPK)

    fused = _rrf([dense, lexical, focus_lexical])
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
        if required_phrases and not all(_phrase_present(content, phrase) for phrase in required_phrases):
            continue
        if focus and focus_overlap == 0 and rel < config.KEYWORD_FILTER_MIN_REL:
            continue
        if terms and overlap < config.QUERY_OVERLAP_MIN and rel < 0.55:
            continue
        pub_boost = _evidence_type_boost(_evidence_text(p), clinical_query=clinical_query)
        final = rel if rel < config.RELEVANCE_GATE else \
            rel + config.ALPHA * _impact_norm(cits.get(pmid)) + (overlap * config.QUERY_OVERLAP_BONUS) + (focus_overlap * config.KEYWORD_FILTER_BONUS) + pub_boost
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
                        "citation_count": c.get("citation_count"), "rcr": c.get("rcr")})
        candidate_pool = top_n * 4 if clinical_query else top_n * 2
        if len(deduped) >= candidate_pool:
            break
    return _balanced_context(deduped, top_n, clinical_query=clinical_query)
