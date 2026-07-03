"""Grounded answer via local MLX, with [PMID] citation validation."""
import re
from functools import lru_cache

from . import config

SYSTEM = (
    "You are a careful biomedical assistant. Answer ONLY from the provided abstracts. "
    "Cite every claim inline as [PMID]. Use cautious language for observational, retrospective, "
    "case-control, mechanistic, animal, or cell-line evidence: say associated with, not proves/causes/reduces, unless randomized trial evidence supports causality. If the evidence is insufficient or the abstracts "
    "conflict, say so explicitly. When sources disagree, weight your synthesis toward "
    "higher-impact (higher RCR / more cited) and higher-evidence-tier studies "
    "(systematic reviews, meta-analyses, RCTs). Produce a structured evidence summary, "
    "not free-form chat. Do not invent details not present in the abstracts."
)


def _context(papers):
    blocks = []
    for p in papers:
        blocks.append(
            f"[{p['pmid']}] ({p.get('year', '?')}, {p.get('journal', '')}; "
            f"RCR={p.get('rcr')}, cites={p.get('citation_count')}, "
            f"types={p.get('pubtypes', '')})\n"
            f"{p.get('title', '')}\n{p.get('abstract', '')}"
        )
    return "\n\n".join(blocks)


@lru_cache(maxsize=1)
def _load_mlx():
    try:
        from mlx_lm import load
    except ImportError as e:
        raise RuntimeError(
            "MLX backend not installed. Run: pip install -r requirements.txt"
        ) from e
    return load(config.LLM_MODEL)


def _build_prompt(question, papers, tokenizer, per_paper=False, markdown=True):
    if per_paper:
        paper_section = "Paper-by-paper notes:\n"
        paper_req = "- In 'Paper-by-paper notes', include 1 bullet for each retrieved paper with a 1-sentence summary and [PMID].\n"
    else:
        paper_section = ""
        paper_req = ""

    if markdown:
        paper_heading = "## Paper-by-paper notes\n" if per_paper else ""
        structure = (
            "Write a concise structured summary using exactly these markdown sections:\n"
            "## Short answer\n"
            "## Evidence basis\n"
            "## Evidence summary\n"
            f"{paper_heading}"
            "## Key papers\n"
            "## Uncertainty / conflicts\n"
            "## Bottom line\n\n"
        )
    else:
        structure = (
            "Write a concise structured summary using exactly these sections:\n"
            "Short answer:\n"
            "Evidence basis:\n"
            "Evidence summary:\n"
            f"{paper_section}"
            "Key papers:\n"
            "Uncertainty / conflicts:\n"
            "Bottom line:\n\n"
        )

    user = (
        f"ABSTRACTS:\n{_context(papers)}\n\n"
        f"QUESTION: {question}\n\n"
        f"{structure}"
        "Requirements:\n"
        "- Every factual claim must include inline [PMID] citations.\n"
        "- In 'Evidence basis', write one concise sentence describing the evidence type and population/context, e.g. randomized outcome trials, observational cohorts/meta-analyses, or mechanistic/cell-line evidence.\n"
        "- Explicitly distinguish risk/incidence/prevention from survival after diagnosis, treatment response, surrogate outcomes, and mechanistic findings.\n"
        f"{paper_req}"
        "- In 'Key papers', include 3-5 bullets, each naming the paper's main contribution. Prefer the strongest and most directly relevant human clinical evidence for clinical questions.\n"
        "- In 'Uncertainty / conflicts', explicitly mention weak evidence, old evidence, observational/confounded evidence, indirect mechanistic evidence, or disagreement.\n"
        "- For observational associations, do not answer with an unqualified 'yes'; say the retrieved evidence suggests an association and note residual confounding.\n"
        "- Do not infer clinical benefit from cell-line, animal, or mechanistic papers alone.\n"
        "- If the evidence is insufficient, say so clearly.\n"
        "- Keep the answer grounded only in the provided abstracts."
    )
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def answer(question, papers, per_paper=False, markdown=True):
    if config.LLM_BACKEND != "mlx":
        raise RuntimeError(
            f"Unsupported LLM backend: {config.LLM_BACKEND}. Expected 'mlx'."
        )

    model, tokenizer = _load_mlx()
    prompt = _build_prompt(question, papers, tokenizer, per_paper=per_paper, markdown=markdown)

    try:
        from mlx_lm import generate as mlx_generate
        from mlx_lm.sample_utils import make_sampler
    except ImportError as e:
        raise RuntimeError(
            "MLX backend not installed. Run: pip install -r requirements.txt"
        ) from e

    text = mlx_generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=config.LLM_MAX_TOKENS,
        sampler=make_sampler(temp=config.LLM_TEMPERATURE),
        verbose=False,
    )
    return _validate_citations(text.strip(), {p["pmid"] for p in papers})


def cited_pmids(text):
    """Extract bracket-form PMID citations: [123], [123, 456], or [PMID:123]."""
    out = set()
    for bracket in re.findall(r"\[([^\]]+)\]", text or ""):
        for m in re.findall(r"\b\d{5,9}\b", bracket):
            out.add(int(m))
    return out


def pmids_anywhere(text):
    """Extract PMID-like numbers anywhere in text.

    This intentionally uses the PMID digit width (5-9 digits), so normal years,
    risk ratios, p-values, and confidence intervals are not treated as PMIDs.
    """
    return {int(m) for m in re.findall(r"\b\d{5,9}\b", text or "")}


def unbracketed_pmids(text):
    """PMID-like numbers present outside square-bracket citation spans."""
    text = text or ""
    outside = []
    pos = 0
    for match in re.finditer(r"\[[^\]]*\]", text):
        outside.append(text[pos:match.start()])
        pos = match.end()
    outside.append(text[pos:])
    return pmids_anywhere("\n".join(outside))


def _replace_pmids_outside_brackets(text, valid_pmids):
    """Convert valid bare/parenthesized PMID mentions outside brackets to [PMID]."""
    text = text or ""
    valid = {int(p) for p in valid_pmids}
    if not valid:
        return text

    def normalize_segment(segment):
        for pmid in sorted(valid, key=lambda x: len(str(x)), reverse=True):
            s = str(pmid)
            # Common model output in key-paper bullets: "(35546664)".
            segment = re.sub(rf"\(\s*(?:PMID\s*:?\s*)?{re.escape(s)}\s*\)", f"[{s}]", segment, flags=re.IGNORECASE)
            # Common prose form: "PMID 35546664" or "PMID:35546664".
            segment = re.sub(rf"\bPMID\s*:?\s*{re.escape(s)}\b", f"[{s}]", segment, flags=re.IGNORECASE)
            # Last resort for valid retrieved PMIDs only: bare PMID number.
            segment = re.sub(rf"(?<![\d\[])\b{re.escape(s)}\b(?![\d\]])", f"[{s}]", segment)
        return segment

    parts = []
    pos = 0
    for match in re.finditer(r"\[[^\]]*\]", text):
        parts.append(normalize_segment(text[pos:match.start()]))
        parts.append(match.group(0))
        pos = match.end()
    parts.append(normalize_segment(text[pos:]))
    return "".join(parts)


def _validate_citations(text, valid_pmids):
    valid_pmids = {int(p) for p in valid_pmids}
    original_unbracketed_valid = unbracketed_pmids(text) & valid_pmids
    text = _replace_pmids_outside_brackets(text, valid_pmids)
    cited = cited_pmids(text)
    hallucinated = cited - valid_pmids
    unbracketed = unbracketed_pmids(text)
    if original_unbracketed_valid:
        text += (
            "\n\n[citation-validation] NOTE: normalized retrieved PMIDs that were "
            f"not in [PMID] citation format: {sorted(original_unbracketed_valid)}"
        )
    if unbracketed:
        text += (
            "\n\n[citation-validation] WARNING: PMID-like numbers not in [PMID] "
            f"citation format: {sorted(unbracketed)}"
        )
    if hallucinated:
        text += (
            "\n\n[citation-validation] WARNING: cited PMIDs not in the retrieved "
            f"set (possible hallucination): {sorted(hallucinated)}"
        )
    return text
