# Summary mode smoke results

Date: 2026-06-29

Environment:
- Data: `/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa`
- Python invoked via `./.venv/bin/python`
- Local MLX backend

## Runs

| Query | Mode | Top N | Retrieval | Answer gen | Second-pass summary | Notes |
|---|---|---:|---:|---:|---:|---|
| statins and risk of dementia | retrieved summary, no normal answer | 10 | 7.55s | n/a | 15.19s | Good citation validity; summary mostly consistent, but somewhat overstates protective pattern and says evidence quality is generally good despite observational mix. |
| does metformin reduce cancer risk? | normal answer + cited summary | 10 | 12.90s | 7.40s | 9.05s | No citation warnings. Normal answer starts too strongly with “Yes”; should use more cautious observational-association wording. |
| p53 mutation and cancer prognosis | top-20 retrieved + map-reduce | 20 | 15.41s | 14.69s | 68.46s | No citation warnings. Map-reduce gives broad coverage but cross-paper/conflict sections repeat many bullets; output appears near token limit and may omit final Takeaway. |
| GLP-1 agonists and cardiovascular outcomes | top-20 retrieved + map-reduce | 20 | 15.81s | 13.37s | 60.27s | No citation warnings. Good high-level answer. Second-pass summary is useful but generic in quality/gaps sections. |

## Observations

- Integrated `p0_ask.py --second-pass-summary` works for both `cited` and `retrieved` sources.
- `--summary-source cited` correctly requires normal answer generation.
- Top-20 map-reduce latency remains dominated by summary generation, not retrieval.
- The main quality issue is not citation hallucination; it is overconfident synthesis language and repeated cross-paper sections.

## Follow-up improvements

1. Make answer and summary prompts more cautious for observational association questions.
2. Use saved map-stage evidence notes to debug summary errors.
3. Tighten final synthesis prompt to avoid repeating all paper bullets in `Cross-paper synthesis` and `Agreements and conflicts`.
4. Consider increasing token budget only when needed, or add a hard instruction to keep synthesis sections concise.
