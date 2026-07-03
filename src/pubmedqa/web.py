"""Small local web UI for PubMed QA.

Intended deployment: bind to 127.0.0.1 and expose through Cloudflare Tunnel +
Cloudflare Access. Do not expose this app directly to the public internet.
"""
from __future__ import annotations

import asyncio
import traceback
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from . import db, evidence_select, generate, retrieve


APP_TITLE = "PubMed QA"
DEFAULT_TOP = 10
DEFAULT_RETRIEVE_POOL = 30
DEFAULT_EVIDENCE_CONTEXT = 8

app = FastAPI(title=APP_TITLE)
_answer_lock = asyncio.Lock()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    top: int = Field(DEFAULT_TOP, ge=1, le=25)
    retrieve_pool: int = Field(DEFAULT_RETRIEVE_POOL, ge=1, le=100)
    evidence_context: int = Field(DEFAULT_EVIDENCE_CONTEXT, ge=1, le=20)
    no_llm: bool = False


def _paper_summary(p: dict[str, Any]) -> dict[str, Any]:
    row = {
        "pmid": p.get("pmid"),
        "title": p.get("title"),
        "year": p.get("year"),
        "journal": p.get("journal"),
        "score": p.get("score"),
        "citation_count": p.get("citation_count"),
        "rcr": p.get("rcr"),
        "pubtypes": p.get("pubtypes"),
        "context_group": p.get("context_group"),
    }
    if p.get("evidence_selection"):
        row["evidence_selection"] = p.get("evidence_selection")
    return row


def _citation_status(answer: str, pmids: list[int]) -> dict[str, Any]:
    valid_pmids = {int(p) for p in pmids}
    cited = generate.cited_pmids(answer or "")
    anywhere = generate.pmids_anywhere(answer or "")
    unbracketed = generate.unbracketed_pmids(answer or "")
    return {
        "cited_pmids": sorted(cited),
        "pmids_anywhere": sorted(anywhere),
        "unbracketed_pmids": sorted(unbracketed),
        "invalid_cited_pmids": sorted(cited - valid_pmids),
        "invalid_pmids_anywhere": sorted(anywhere - valid_pmids),
        "citation_format_warning": bool(unbracketed),
        "citation_validation_warning": "[citation-validation] WARNING" in (answer or ""),
        "citation_normalization_note": "[citation-validation] NOTE" in (answer or ""),
    }


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> str:
    user_email = request.headers.get("Cf-Access-Authenticated-User-Email", "")
    user_html = f"<span>Signed in as {user_email}</span>" if user_email else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{APP_TITLE}</title>
  <style>
    :root {{ color-scheme: light dark; --accent: #2563eb; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; line-height: 1.45; }}
    header {{ padding: 1rem 1.25rem; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; gap: 1rem; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 1.25rem; }}
    textarea {{ width: 100%; min-height: 5.5rem; font: inherit; padding: .75rem; box-sizing: border-box; }}
    button {{ background: var(--accent); color: white; border: 0; border-radius: .5rem; padding: .7rem 1rem; font: inherit; cursor: pointer; }}
    button:disabled {{ opacity: .55; cursor: wait; }}
    .row {{ display: flex; gap: .75rem; align-items: center; flex-wrap: wrap; margin: .75rem 0; }}
    .muted {{ color: #666; }}
    .answer, .papers {{ margin-top: 1.25rem; }}
    .answer {{ white-space: pre-wrap; border: 1px solid #ddd; border-radius: .75rem; padding: 1rem; }}
    .paper {{ border-top: 1px solid #ddd; padding: .75rem 0; }}
    .error {{ color: #b91c1c; font-weight: 600; }}
    code {{ background: rgba(127,127,127,.14); padding: .1rem .25rem; border-radius: .25rem; }}
  </style>
</head>
<body>
  <header>
    <strong>{APP_TITLE}</strong>
    <div class="muted">{user_html}</div>
  </header>
  <main>
    <p class="muted">Ask a biomedical/scientific question. Answers are generated locally on Tim's Mac from retrieved PubMed abstracts and are not medical advice.</p>
    <form id="ask-form">
      <textarea id="question" required maxlength="1000" placeholder="e.g. SGLT2 inhibitors kidney outcomes"></textarea>
      <div class="row">
        <label>Retrieve pool <input id="retrieve_pool" type="number" min="1" max="100" value="{DEFAULT_RETRIEVE_POOL}" /></label>
        <label>Evidence context <input id="evidence_context" type="number" min="1" max="20" value="{DEFAULT_EVIDENCE_CONTEXT}" /></label>
        <button id="ask-button" type="submit">Ask</button>
        <span id="status" class="muted"></span>
      </div>
    </form>
    <div id="error" class="error"></div>
    <section id="answer" class="answer" hidden></section>
    <section id="papers" class="papers"></section>
  </main>
<script>
const form = document.getElementById('ask-form');
const button = document.getElementById('ask-button');
const statusEl = document.getElementById('status');
const errorEl = document.getElementById('error');
const answerEl = document.getElementById('answer');
const papersEl = document.getElementById('papers');

function esc(s) {{ return String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}

form.addEventListener('submit', async (e) => {{
  e.preventDefault();
  errorEl.textContent = '';
  answerEl.hidden = true;
  answerEl.textContent = '';
  papersEl.innerHTML = '';
  button.disabled = true;
  statusEl.textContent = 'Retrieving and generating locally… this can take 15–30 seconds.';
  const t0 = performance.now();
  try {{
    const res = await fetch('/api/ask', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        question: document.getElementById('question').value,
        retrieve_pool: Number(document.getElementById('retrieve_pool').value),
        evidence_context: Number(document.getElementById('evidence_context').value),
        top: 10
      }})
    }});
    const contentType = res.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await res.json() : {{detail: await res.text()}};
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
    statusEl.textContent = `Done in ${{elapsed}}s. Retrieval ${{data.retrieval_seconds}}s, generation ${{data.generation_seconds ?? 'n/a'}}s.`;
    answerEl.hidden = false;
    answerEl.textContent = data.answer || '(retrieval only)';
    const selected = data.selected_evidence_papers || [];
    papersEl.innerHTML = `<h2>Selected evidence (${{selected.length}} papers)</h2>` + selected.map(p => `
      <div class="paper">
        <strong>[${{esc(p.pmid)}}]</strong> ${{esc(p.title)}}<br />
        <span class="muted">${{esc(p.year)}} · ${{esc(p.journal)}} · tier ${{esc(p.evidence_selection?.evidence_tier)}} · score ${{esc(p.evidence_selection?.score)}}</span>
      </div>`).join('');
  }} catch (err) {{
    errorEl.textContent = err.message || String(err);
    statusEl.textContent = '';
  }} finally {{
    button.disabled = false;
  }}
}});
</script>
</body>
</html>"""


@app.post("/api/ask")
async def ask(payload: AskRequest) -> JSONResponse:
    if _answer_lock.locked():
        raise HTTPException(status_code=429, detail="Another question is currently running. Please try again in a minute.")

    async with _answer_lock:
        try:
            t0 = time.perf_counter()
            con = db.connect()
            papers = retrieve.search(con, payload.question, top_n=payload.retrieve_pool)
            retrieval_s = time.perf_counter() - t0
            recorded = papers[: payload.top]
            selected = evidence_select.select_evidence(
                payload.question,
                papers,
                max_papers=payload.evidence_context,
            )

            answer = None
            generation_s = None
            citation_status = None
            if not payload.no_llm:
                if not selected:
                    raise HTTPException(status_code=404, detail="No relevant PubMed papers were selected for this question.")
                g0 = time.perf_counter()
                answer = generate.answer(payload.question, selected)
                generation_s = time.perf_counter() - g0
                citation_status = _citation_status(answer, [int(p["pmid"]) for p in selected])

            return JSONResponse({
                "question": payload.question,
                "retrieval_seconds": round(retrieval_s, 3),
                "generation_seconds": round(generation_s, 3) if generation_s is not None else None,
                "citation_status": citation_status,
                "papers": [_paper_summary(p) for p in recorded],
                "selected_evidence_papers": [_paper_summary(p) for p in selected],
                "answer": answer,
            })
        except HTTPException:
            raise
        except Exception as exc:
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error while answering: {type(exc).__name__}: {exc}",
                },
            )
