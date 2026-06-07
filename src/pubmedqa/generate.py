"""Grounded answer via local Ollama (8B), with [PMID] citation validation."""
import re
import requests
from . import config

SYSTEM = (
    "You are a careful biomedical assistant. Answer ONLY from the provided abstracts. "
    "Cite every claim inline as [PMID]. If the evidence is insufficient or the abstracts "
    "conflict, say so explicitly. When sources disagree, weight your synthesis toward "
    "higher-impact (higher RCR / more cited) and higher-evidence-tier studies "
    "(systematic reviews, meta-analyses, RCTs)."
)


def _context(papers):
    blocks = []
    for p in papers:
        blocks.append(
            f"[{p['pmid']}] ({p.get('year', '?')}, {p.get('journal', '')}; "
            f"RCR={p.get('rcr')}, cites={p.get('citation_count')}, "
            f"types={p.get('pubtypes', '')})\n"
            f"{p.get('title', '')}\n{p.get('abstract', '')}")
    return "\n\n".join(blocks)


def answer(question, papers):
    prompt = (f"{SYSTEM}\n\nABSTRACTS:\n{_context(papers)}\n\n"
              f"QUESTION: {question}\n\nANSWER (with [PMID] citations):")
    r = requests.post(f"{config.OLLAMA_URL}/api/generate",
                      json={"model": config.LLM_MODEL, "prompt": prompt, "stream": False},
                      timeout=600)
    r.raise_for_status()
    text = r.json().get("response", "")
    return _validate_citations(text, {p["pmid"] for p in papers})


def _validate_citations(text, valid_pmids):
    cited = {int(m) for m in re.findall(r"\[(\d+)\]", text)}
    hallucinated = cited - valid_pmids
    if hallucinated:
        text += ("\n\n[citation-validation] WARNING: cited PMIDs not in the retrieved "
                 f"set (possible hallucination): {sorted(hallucinated)}")
    return text
