#!/usr/bin/env python3
"""Judge retrieval relevance with an OpenAI-compatible LLM.

Reads an evaluation JSON from scripts/evaluate_retrieval.py, fetches local abstracts
from SQLite when available, optionally falls back to PubMed efetch, and asks a judge
model to score each question/paper pair.

Environment:
  OPENAI_API_KEY       required for --provider openai unless endpoint does not need auth
  OPENAI_BASE_URL      default: https://api.openai.com/v1
  PUBMEDQA_JUDGE_MODEL default: gpt-4.1-mini for OpenAI, or an MLX model for --provider mlx
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from functools import lru_cache

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pubmedqa import db  # noqa: E402


SYSTEM = """You are a strict biomedical retrieval evaluator.
Judge whether a PubMed paper is relevant evidence for answering the user's medical/scientific question.
Use only the provided title, abstract, and metadata. Do not assume facts not present.
Return ONLY valid JSON."""

EVIDENCE_TYPES = {
    "meta-analysis",
    "systematic_review",
    "randomized_trial",
    "cohort",
    "case_control",
    "review",
    "mechanistic",
    "editorial_or_news",
    "other",
}


def _local_papers(pmids):
    try:
        con = db.connect()
        return db.fetch_papers(con, pmids)
    except Exception:
        return {}


def _pubmed_fetch(pmids, batch_size=100):
    out = {}
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(map(str, batch)),
            "retmode": "xml",
        })
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{params}"
        with urllib.request.urlopen(url, timeout=30) as r:
            xml = r.read()
        root = ET.fromstring(xml)
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//MedlineCitation/PMID")
            if pmid_el is None or not pmid_el.text:
                continue
            pmid = int(pmid_el.text)
            title = "".join(article.findtext(".//ArticleTitle", default="") or "")
            abstract_parts = []
            for node in article.findall(".//Abstract/AbstractText"):
                label = node.attrib.get("Label")
                text = "".join(node.itertext())
                abstract_parts.append(f"{label}: {text}" if label else text)
            pubtypes = ["".join(n.itertext()) for n in article.findall(".//PublicationType")]
            year = article.findtext(".//JournalIssue/PubDate/Year")
            journal = article.findtext(".//Journal/Title", default="") or ""
            out[pmid] = {
                "pmid": pmid,
                "title": title,
                "abstract": "\n".join(abstract_parts),
                "journal": journal,
                "year": int(year) if year and year.isdigit() else None,
                "pubtypes": "; ".join(pubtypes),
            }
        time.sleep(0.12)  # be polite to NCBI
    return out


def _paper_text(paper):
    abstract = paper.get("abstract") or ""
    if len(abstract) > 6000:
        abstract = abstract[:6000] + "...[truncated]"
    return (
        f"PMID: {paper.get('pmid')}\n"
        f"Title: {paper.get('title') or ''}\n"
        f"Year: {paper.get('year') or ''}\n"
        f"Journal: {paper.get('journal') or ''}\n"
        f"Publication types: {paper.get('pubtypes') or ''}\n"
        f"Abstract: {abstract}"
    )


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _judge_user_prompt(question, paper):
    return f"""Question: {question}

Paper:
{_paper_text(paper)}

Score this paper for answering the exact question, not merely sharing keywords.
Use this strict 0-3 rubric:
- 3 = directly answers the exact question with human outcome evidence when the question is clinical/risk/outcome oriented. Examples: meta-analysis, systematic review, randomized trial, cohort, or case-control study of the same exposure/intervention and the same endpoint. For mechanistic questions, a 3 must directly test the named mechanism in an appropriate model.
- 2 = relevant but indirect or limited. Examples: narrative/background review, mechanistic or animal/cell evidence for a clinical question, related but narrower endpoint/subtype/population, treatment/survival evidence when the question asks incidence/risk/prevention, or the right exposure with only a proxy outcome.
- 1 = weak/background mention only. Examples: broad disease review, tangential mention of one query concept, editorial/news/commentary without substantive evidence, or only partial keyword overlap.
- 0 = off topic or does not provide useful evidence for the question.

Be conservative: do not give 3 for reviews without clear human outcome evidence, mechanistic studies answering clinical outcome questions, papers about a different disease endpoint, or papers about prognosis/survival when the question asks disease risk/incidence.
Set answers_question=true only for relevance=3.

Return JSON with exactly these keys:
- relevance: integer 0-3
- evidence_type: one of meta-analysis, systematic_review, randomized_trial, cohort, case_control, review, mechanistic, editorial_or_news, other
- answers_question: boolean
- population_or_model: short string, e.g. humans, mice, cells, mixed, unclear
- reason: one concise sentence explaining the score
"""


def _normalize_judgement(judged):
    """Coerce model output to the requested schema/rubric constraints."""
    try:
        rel = int(judged.get("relevance"))
    except Exception:
        rel = None
    if rel is not None:
        judged["relevance"] = max(0, min(3, rel))
        if judged["relevance"] < 3:
            judged["answers_question"] = False
        elif "answers_question" not in judged:
            judged["answers_question"] = True
    etype = str(judged.get("evidence_type") or "other").strip().lower().replace(" ", "_")
    aliases = {
        "meta_analysis": "meta-analysis",
        "systematic review": "systematic_review",
        "randomized trial": "randomized_trial",
        "randomized_controlled_trial": "randomized_trial",
        "case-control": "case_control",
        "clinical_trial": "randomized_trial",
        "journal_article": "other",
    }
    etype = aliases.get(etype, etype)
    judged["evidence_type"] = etype if etype in EVIDENCE_TYPES else "other"
    for key in ("answers_question", "population_or_model", "reason"):
        judged.setdefault(key, False if key == "answers_question" else "")
    return judged


def judge_one_openai(question, paper, model, base_url, api_key, timeout=60):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _judge_user_prompt(question, paper)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    url = base_url.rstrip("/") + "/chat/completions"
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        detail = resp.text[:1000]
        raise RuntimeError(f"{resp.status_code} error from judge API: {detail}")
    content = resp.json()["choices"][0]["message"]["content"]
    judged = _normalize_judgement(_extract_json(content))
    judged["model"] = model
    return judged


@lru_cache(maxsize=2)
def _load_mlx_judge(model):
    try:
        from mlx_lm import load
    except ImportError as e:
        raise RuntimeError("mlx-lm not installed. Run: pip install -r requirements.txt") from e
    return load(model)


def judge_one_mlx(question, paper, model, max_tokens=256):
    try:
        from mlx_lm import generate as mlx_generate
        from mlx_lm.sample_utils import make_sampler
    except ImportError as e:
        raise RuntimeError("mlx-lm not installed. Run: pip install -r requirements.txt") from e

    llm, tokenizer = _load_mlx_judge(model)
    user_prompt = _judge_user_prompt(question, paper)
    if "qwen3" in model.lower():
        # Qwen3 thinking traces can consume the token budget before JSON appears.
        user_prompt += "\n/no_think"
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    content = mlx_generate(
        llm,
        tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        sampler=make_sampler(temp=0.0),
        verbose=False,
    )
    judged = _normalize_judgement(_extract_json(content))
    judged["model"] = model
    return judged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="baseline_retrieval_v3.json")
    ap.add_argument("--out", default="judged_retrieval.json")
    ap.add_argument("--provider", choices=("openai", "mlx"), default="openai")
    ap.add_argument("--model", default=os.environ.get("PUBMEDQA_JUDGE_MODEL"),
                    help="Judge model. Defaults to gpt-4.1-mini for openai or mlx-community/Llama-3.1-8B-Instruct-4bit for mlx.")
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    ap.add_argument("--mlx-max-tokens", type=int, default=512)
    ap.add_argument("--limit-queries", type=int)
    ap.add_argument("--limit-papers", type=int)
    ap.add_argument("--fetch-pubmed", action="store_true", help="fetch missing abstracts from PubMed online")
    ap.add_argument("--sleep", type=float, default=0.0, help="sleep between judge API calls")
    args = ap.parse_args()

    if not args.model:
        args.model = "gpt-4.1-mini" if args.provider == "openai" else "mlx-community/Llama-3.1-8B-Instruct-4bit"

    if args.provider == "openai" and not args.api_key and "localhost" not in args.base_url and "127.0.0.1" not in args.base_url:
        raise SystemExit("OPENAI_API_KEY is not set. Export it or use --base-url for a local compatible endpoint.")

    payload = json.loads(Path(args.input).read_text())
    results = payload.get("results", [])
    if args.limit_queries:
        results = results[:args.limit_queries]

    all_pmids = []
    for r in results:
        papers = r.get("papers", [])[:args.limit_papers] if args.limit_papers else r.get("papers", [])
        all_pmids.extend(int(p["pmid"]) for p in papers if p.get("pmid"))
    local = _local_papers(sorted(set(all_pmids)))

    missing = [p for p in sorted(set(all_pmids)) if not (local.get(p, {}).get("abstract") or local.get(p, {}).get("title"))]
    fetched = _pubmed_fetch(missing) if args.fetch_pubmed and missing else {}

    judged_results = []
    for qi, r in enumerate(results, 1):
        question = r["question"]
        papers = r.get("papers", [])[:args.limit_papers] if args.limit_papers else r.get("papers", [])
        judged_papers = []
        print(f"[{qi}/{len(results)}] {question} ({len(papers)} papers)")
        for pi, p in enumerate(papers, 1):
            pmid = int(p["pmid"])
            paper = {**p, **local.get(pmid, {}), **fetched.get(pmid, {})}
            try:
                if args.provider == "mlx":
                    score = judge_one_mlx(question, paper, args.model, max_tokens=args.mlx_max_tokens)
                else:
                    score = judge_one_openai(question, paper, args.model, args.base_url, args.api_key)
            except Exception as e:
                score = {"error": str(e), "model": args.model}
            judged_papers.append({**p, "judge": score})
            rel = score.get("relevance", "ERR")
            print(f"  {pi:02d}. PMID {pmid}: relevance={rel} {score.get('evidence_type', '')}")
            if args.sleep:
                time.sleep(args.sleep)

        valid = [p["judge"] for p in judged_papers if "relevance" in p.get("judge", {})]
        rels = [float(j["relevance"]) for j in valid]
        judged_results.append({
            **r,
            "papers": judged_papers,
            "judge_summary": {
                "model": args.model,
                "mean_relevance": round(sum(rels) / len(rels), 3) if rels else None,
                "relevance_at_3plus": sum(1 for x in rels if x >= 3),
                "relevance_at_2plus": sum(1 for x in rels if x >= 2),
                "irrelevant_count": sum(1 for x in rels if x == 0),
                "judged_count": len(rels),
            },
        })

    out = {**payload, "judge": {"provider": args.provider, "model": args.model, "base_url": args.base_url if args.provider == "openai" else None}, "results": judged_results}
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")
    print("\nSummary:")
    for r in judged_results:
        print(f"- {r['question']}: {r['judge_summary']}")


if __name__ == "__main__":
    main()
