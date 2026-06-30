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
        f"{paper_req}"
        "- In 'Key papers', include 3-5 bullets, each naming the paper's main contribution.\n"
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
    """Extract PMID citations from [123], [123, 456], or [PMID:123] forms."""
    out = set()
    for bracket in re.findall(r"\[([^\]]+)\]", text or ""):
        for m in re.findall(r"\b\d{5,9}\b", bracket):
            out.add(int(m))
    return out


def _validate_citations(text, valid_pmids):
    cited = cited_pmids(text)
    hallucinated = cited - valid_pmids
    if hallucinated:
        text += (
            "\n\n[citation-validation] WARNING: cited PMIDs not in the retrieved "
            f"set (possible hallucination): {sorted(hallucinated)}"
        )
    return text
