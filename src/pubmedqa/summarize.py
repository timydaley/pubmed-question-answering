"""Summarize a set of cited PubMed papers.

This module is for the second-stage workflow: given a list of citation PMIDs,
load the papers, read their abstracts, and synthesize an overall grounded summary
with inline [PMID] citations.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, Optional, Union

from . import config, db, parse_pubmed
from .generate import _load_mlx, _validate_citations, cited_pmids

SYSTEM = (
    "You are a careful biomedical evidence synthesizer. Summarize ONLY the provided "
    "PubMed abstracts. Cite every factual claim inline as [PMID]. Do not invent "
    "details not present in the abstracts. Use cautious language for observational, retrospective, "
    "case-control, mechanistic, animal, or cell-line evidence; do not imply causality or clinical benefit unless randomized trial evidence supports it. If the set is heterogeneous, summarize "
    "themes and disagreements rather than forcing a single conclusion."
)


def unique_pmids(pmids: Iterable[int]) -> list[int]:
    """Return PMIDs as unique integers preserving input order."""
    seen = set()
    out = []
    for pmid in pmids:
        try:
            pmid = int(pmid)
        except Exception:
            continue
        if pmid not in seen:
            seen.add(pmid)
            out.append(pmid)
    return out


def fetch_pubmed_records(pmids: Iterable[int], batch_size: int = 100, sleep: float = 0.12) -> dict[int, dict]:
    """Fetch PubMed XML records for PMIDs and return parsed paper dicts."""
    pmids = unique_pmids(pmids)
    out = {}
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(map(str, batch)),
            "retmode": "xml",
        })
        url = f"{config.EFETCH_URL}?{params}"
        with urllib.request.urlopen(url, timeout=60) as r:
            records = parse_pubmed.parse_efetch_xml(r.read())
        out.update({int(r["pmid"]): r for r in records})
        if i + batch_size < len(pmids):
            time.sleep(sleep)
    return out


def load_papers(pmids: Iterable[int], fetch_missing: bool = True, require_abstract: bool = False) -> list[dict]:
    """Load papers from local SQLite, optionally filling missing rows/abstracts via efetch."""
    pmids = unique_pmids(pmids)
    if not pmids:
        return []

    con = db.connect()
    local = db.fetch_papers(con, pmids)
    missing = []
    for pmid in pmids:
        p = local.get(pmid, {})
        if not p.get("title") or (require_abstract and not p.get("abstract")):
            missing.append(pmid)

    fetched = fetch_pubmed_records(missing) if fetch_missing and missing else {}
    if fetched:
        # Persist fetched metadata for future summaries/retrieval reports.
        db.insert_papers(con, fetched.values())

    papers = []
    for pmid in pmids:
        paper = {**local.get(pmid, {"pmid": pmid}), **fetched.get(pmid, {})}
        if paper.get("title") or paper.get("abstract"):
            papers.append(paper)
    return papers


def _context(papers: list[dict], max_abstract_chars: int = 5000) -> str:
    blocks = []
    for p in papers:
        abstract = p.get("abstract") or ""
        if len(abstract) > max_abstract_chars:
            abstract = abstract[:max_abstract_chars] + "...[truncated]"
        blocks.append(_paper_block(p, abstract=abstract))
    return "\n\n".join(blocks)


def _paper_block(p: dict, abstract: Optional[str] = None) -> str:
    abstract = p.get("abstract") or "" if abstract is None else abstract
    return (
        f"[{p['pmid']}] ({p.get('year') or '?'}, {p.get('journal') or ''}; "
        f"types={p.get('pubtypes') or ''})\n"
        f"Title: {p.get('title') or ''}\n"
        f"Abstract: {abstract}"
    )


def _notes_context(papers: list[dict], notes: dict[int, str]) -> str:
    blocks = []
    for p in papers:
        blocks.append(
            f"[{p['pmid']}] ({p.get('year') or '?'}, {p.get('journal') or ''}; "
            f"types={p.get('pubtypes') or ''})\n"
            f"Title: {p.get('title') or ''}\n"
            f"Evidence note: {notes.get(int(p['pmid']), '').strip()}"
        )
    return "\n\n".join(blocks)


def _build_prompt(papers: list[dict], tokenizer, topic: Optional[str] = None,
                  markdown: bool = True, context_text: Optional[str] = None) -> str:
    topic_line = f"Topic / synthesis goal: {topic}\n\n" if topic else ""
    if markdown:
        structure = (
            "Write a detailed evidence synthesis using exactly these markdown sections:\n"
            "## Overall summary\n"
            "## Paper-specific findings\n"
            "## Cross-paper synthesis\n"
            "## Evidence quality\n"
            "## Agreements and conflicts\n"
            "## Gaps / cautions\n"
            "## Takeaway\n\n"
        )
    else:
        structure = (
            "Write a detailed evidence synthesis using exactly these sections:\n"
            "Overall summary:\nPaper-specific findings:\nCross-paper synthesis:\nEvidence quality:\n"
            "Agreements and conflicts:\nGaps / cautions:\nTakeaway:\n\n"
        )
    pmid_list = ", ".join(str(p["pmid"]) for p in papers)
    n_papers = len(papers)
    user = (
        f"PUBMED EVIDENCE:\n{context_text if context_text is not None else _context(papers)}\n\n"
        f"{topic_line}"
        f"{structure}"
        "Requirements:\n"
        "- Every factual claim must include inline [PMID] citations.\n"
        f"- In 'Paper-specific findings', write EXACTLY {n_papers} bullets total: one bullet for each PMID in this checklist and no extra bullets: {pmid_list}.\n"
        "- Each paper-specific bullet must name the paper or topic, state the specific result/finding from the abstract/evidence note, and cite that PMID exactly once.\n"
        "- Do not repeat a PMID in multiple paper-specific bullets. Do not create bullets for imagined subtopics or repeated variants of the same paper.\n"
        "- In 'Cross-paper synthesis', write 1-3 concise paragraphs comparing patterns across papers; do not list every PMID again and do not merely repeat the bullets.\n"
        "- Distinguish human clinical evidence from mechanistic, animal, or cell-line evidence.\n"
        "- Describe study design, population/cancer type/model, endpoint, and direction of effect when the abstract provides them.\n"
        "- Do not call evidence high quality unless the abstract supports that; prefer precise descriptions such as randomized trial, cohort, retrospective study, systematic review, or cell-line study.\n"
        "- For observational associations, say associated with rather than proves/causes/reduces, and mention possible residual confounding.\n"
        "- Do not infer patient-level clinical benefit from mechanistic, animal, or cell-line studies alone.\n"
        "- In 'Agreements and conflicts', summarize only the main agreements/conflicts in 3-6 bullets; do not repeat every paper-specific bullet.\n"
        "- Mention whether the evidence set is narrow, indirect, conflicting, or insufficient.\n"
        "- Keep the summary grounded only in the provided abstracts."
    )
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def _mlx_generate_text(prompt: str, max_tokens: int) -> str:
    model, tokenizer = _load_mlx()
    try:
        from mlx_lm import generate as mlx_generate
        from mlx_lm.sample_utils import make_sampler
    except ImportError as e:
        raise RuntimeError("MLX backend not installed. Run: pip install -r requirements.txt") from e
    return mlx_generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        sampler=make_sampler(temp=config.LLM_TEMPERATURE),
        verbose=False,
    )


def _paper_note_prompt(paper: dict, tokenizer, topic: Optional[str] = None) -> str:
    topic_line = f"Topic: {topic}\n" if topic else ""
    user = (
        f"{topic_line}"
        f"Paper:\n{_paper_block(paper)}\n\n"
        "Write one compact evidence note for this paper only using exactly these labeled fields: "
        "Design, Population/model, Endpoint, Main result, Limitations. "
        "Use terse phrases or 1 sentence per field. Do not add extra fields. "
        f"Cite only [{paper['pmid']}]."
    )
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def paper_evidence_notes(papers: list[dict], topic: Optional[str] = None,
                         max_tokens_per_paper: int = 220) -> dict[int, str]:
    """Create one grounded evidence note per paper for map-reduce synthesis."""
    if config.LLM_BACKEND != "mlx":
        raise RuntimeError(f"Unsupported LLM backend: {config.LLM_BACKEND}. Expected 'mlx'.")
    model, tokenizer = _load_mlx()
    notes = {}
    for p in papers:
        prompt = _paper_note_prompt(p, tokenizer, topic=topic)
        try:
            from mlx_lm import generate as mlx_generate
            from mlx_lm.sample_utils import make_sampler
        except ImportError as e:
            raise RuntimeError("MLX backend not installed. Run: pip install -r requirements.txt") from e
        text = mlx_generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=max_tokens_per_paper,
            sampler=make_sampler(temp=config.LLM_TEMPERATURE),
            verbose=False,
        ).strip()
        notes[int(p["pmid"])] = _validate_citations(text, {int(p["pmid"])})
    return notes


def write_evidence_notes_json(path: Union[str, Path], papers: list[dict], notes: dict[int, str],
                              topic: Optional[str] = None) -> None:
    """Write map-stage evidence notes for inspection/debugging."""
    by_pmid = {int(p["pmid"]): p for p in papers}
    payload = {
        "topic": topic,
        "paper_count": len(papers),
        "notes": [
            {
                "pmid": pmid,
                "title": by_pmid.get(pmid, {}).get("title"),
                "year": by_pmid.get(pmid, {}).get("year"),
                "journal": by_pmid.get(pmid, {}).get("journal"),
                "pubtypes": by_pmid.get(pmid, {}).get("pubtypes"),
                "note": note,
            }
            for pmid, note in notes.items()
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def summarize_papers(papers: list[dict], topic: Optional[str] = None, markdown: bool = True,
                     map_reduce: bool = False, map_reduce_threshold: int = 12,
                     notes_out: Optional[Union[str, Path]] = None) -> str:
    """Generate an overall cited summary for already-loaded paper dicts.

    For larger paper sets, map-reduce first creates one evidence note per paper,
    then synthesizes those notes. This prevents long-context summaries from
    degenerating into title lists or repeated bullets.
    """
    if config.LLM_BACKEND != "mlx":
        raise RuntimeError(f"Unsupported LLM backend: {config.LLM_BACKEND}. Expected 'mlx'.")
    if not papers:
        raise ValueError("No papers available to summarize")

    model, tokenizer = _load_mlx()
    context_text = None
    notes = None
    if map_reduce or len(papers) >= map_reduce_threshold:
        notes = paper_evidence_notes(papers, topic=topic)
        if notes_out:
            write_evidence_notes_json(notes_out, papers, notes, topic=topic)
        context_text = _notes_context(papers, notes)

    prompt = _build_prompt(papers, tokenizer, topic=topic, markdown=markdown,
                           context_text=context_text)
    text = _mlx_generate_text(prompt, max_tokens=config.LLM_MAX_TOKENS)
    return _validate_citations(text.strip(), {int(p["pmid"]) for p in papers})


def summarize_pmids(pmids: Iterable[int], topic: Optional[str] = None,
                    fetch_missing: bool = True, require_abstract: bool = False,
                    markdown: bool = True, map_reduce: bool = False,
                    map_reduce_threshold: int = 12,
                    notes_out: Optional[Union[str, Path]] = None) -> tuple[str, list[dict]]:
    """Load PMIDs, summarize them, and return (summary, papers_used)."""
    papers = load_papers(pmids, fetch_missing=fetch_missing, require_abstract=require_abstract)
    return summarize_papers(papers, topic=topic, markdown=markdown,
                            map_reduce=map_reduce,
                            map_reduce_threshold=map_reduce_threshold,
                            notes_out=notes_out), papers


def cited_pmids_from_text(text: str) -> list[int]:
    """Extract [PMID] citations from arbitrary answer text."""
    return unique_pmids(cited_pmids(text or ""))
