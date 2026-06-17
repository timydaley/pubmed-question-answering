# PubMed Question-Answering — Revised Implementation Plan (Tighter v1)

> Goal: a **fully local-at-query-time** tool that answers medical/scientific questions by retrieving
> relevant PubMed papers, applying a **modest evidence/citation-aware ranking boost**, and using a
> **local LLM** to generate grounded answers with inline `[PMID]` citations.
>
> **Important framing for v1:** this system should **not** claim to infer scientific consensus.
> In v1, it is better described as **citation- and evidence-aware PubMed question answering**.

---

## 0. Product scope and framing

### v1 product claim
> Local PubMed question answering with citation- and evidence-aware retrieval.

### What v1 is
- A local search + answer tool over PubMed abstracts
- Grounded in retrieved papers
- Biased slightly toward stronger evidence and higher-impact work
- Offline at query time

### What v1 is not
- A consensus engine
- A clinical decision maker
- A substitute for physician judgment
- A full-text biomedical research platform

### Query-time requirement
**No network calls at runtime.**

### Build-time allowance
Internet is allowed only for:
- downloading PubMed data
- downloading precomputed embeddings
- downloading citation metadata
- downloading local models

---

## 1. Core design decisions

| Question | Decision |
|---|---|
| RAG + vector DB? | **Yes.** Hybrid retrieval feeding a local LLM. |
| Tri-letter / trigram index? | **No** as a primary strategy. Use **BM25 via SQLite FTS5**. |
| Combination? | **Yes:** BM25 + dense retrieval + RRF fusion. |
| Citation weighting? | **Yes, but bounded and secondary to relevance.** |
| Cross-encoder rerank in v1? | **No.** Defer until retrieval quality and latency are measured. |
| Daily updates in v1? | **No.** Use a fixed snapshot first. |
| Full text in v1? | **No.** Title + abstract only. |

---

## 2. Tighter v1 scope

### Must-have
- Local query interface (CLI first)
- Local metadata/text store
- Local vector store
- BM25 retrieval
- Dense retrieval
- Reciprocal Rank Fusion (RRF)
- Small evidence/citation-aware rerank boost
- Local LLM answer generation
- Citation validation against retrieved PMIDs
- Clear abstention / uncertainty behavior

### Explicitly out of scope for v1
- Daily PubMed updates
- OpenAlex gap-filling unless citation coverage is unusably bad
- Cross-encoder reranking
- MeSH expansion / query expansion
- Consensus/conflict subsystem
- Full-text indexing
- UI beyond a minimal CLI
- Complex eval-judge pipelines

---

## 3. Recommended v1 architecture

## Data layer
Use two embedded local stores:

1. **SQLite + FTS5**
   - PMID
   - title
   - abstract
   - year
   - journal
   - publication type
   - citation metadata
   - optional retraction flag

2. **LanceDB**
   - dense MedCPT vectors keyed by PMID

This keeps the system local, simple, and easy to back up.

## Retrieval layer
For each question:
1. Run **BM25** over title + abstract via FTS5
2. Run **dense retrieval** using MedCPT query encoder + LanceDB
3. Fuse rankings with **RRF**
4. Apply a **small bounded boost** for evidence/citation features
5. Pass top results to the LLM

## Generation layer
- Local Ollama model, default **8B**
- Prompt constrained to retrieved evidence only
- Inline `[PMID]` citations required
- Post-generation citation validation required

---

## 4. Corpus strategy

### v1 corpus policy
Use a **fixed PubMed snapshot** for v1.

Rationale:
- lowers operational complexity
- improves reproducibility
- avoids premature work on update pipelines
- makes evaluation easier

### Corpus content
Index **title + abstract** only.

### Embeddings
Use **downloaded precomputed MedCPT embeddings** for the indexed corpus whenever possible.

### Why this is the right v1 choice
- avoids bulk local embedding cost
- keeps the architecture aligned with likely production usage
- lets the laptop focus on retrieval and generation rather than large-scale indexing compute

### Full corpus vs slice
Default preference: **full corpus if disk/process are manageable**.
If ingest risk is too high, start with a **recent fixed slice** and scale after retrieval quality is proven.

---

## 5. Ranking strategy

## Principle
Relevance comes first. Citation/evidence features are only a **bounded booster**.

## Base retrieval
- BM25 rank
- dense rank
- RRF fused rank

## Evidence-aware boost
Apply a small additive boost only after a document is already relevant.

Suggested factors:
- **publication type**
  - systematic review / meta-analysis / RCT: positive boost
  - observational: smaller boost
  - case report: little or no boost
- **citation signal**
  - modest normalized citation or RCR-based boost
- **recency**
  - modest recency boost to prevent old landmark papers from dominating forever

## Rule to preserve relevance
A paper must clear a relevance threshold before these boosts can reorder it.

## v1 wording
Do **not** equate this with consensus.
It is only an **evidence-aware ranking preference**.

---

## 6. Safety and answer behavior

This project touches medical questions, so v1 needs explicit behavior constraints.

### Required guardrails
- state that the tool is **not medical advice**
- answer only from retrieved evidence
- never invent citations
- abstain when evidence is weak or sparse
- mention uncertainty when evidence is limited
- mention disagreement when top papers conflict
- prefer descriptive summaries over prescriptive treatment advice

### Required output structure
Each answer should include:
1. short answer
2. brief evidence summary
3. inline `[PMID]` citations
4. uncertainty / caveat note when appropriate

---

## 7. Offline requirements

### Hard requirement
The system must work **fully offline at query time**.

### Allowed online setup tasks
- PubMed snapshot download
- embedding download
- citation metadata download
- local model download

### Non-goal
The setup/build process does **not** need to be fully offline in v1.

---

## 8. Data quality and integrity checks

This should be treated as a first-class workstream, not an afterthought.

### Required checks during build
- percent of PMIDs with matched metadata and vectors
- percent of records missing abstracts
- percent of records missing citation metadata
- duplicate PMID handling
- malformed XML / parse failure counts
- reproducible corpus snapshot identifier
- embedding snapshot / model revision recorded in build metadata

### Required build artifact report
Each build should emit a summary report containing:
- corpus snapshot/date
- document count
- vector count
- match rate
- missing-abstract rate
- missing-citation rate
- index parameters
- model revisions used

---

## 9. Implementation phases

## Phase 0 — core loop on a small subset
Goal: prove the architecture, not scale.

### Deliverables
- parse a small PubMed subset into SQLite
- create FTS5 index
- load vectors into LanceDB
- implement BM25 retrieval
- implement dense retrieval
- implement RRF fusion
- generate grounded local answers
- validate cited PMIDs

### Exit criteria
- retrieved papers are visibly relevant
- dense and BM25 retrieval both function
- answer cites only retrieved PMIDs
- latency and memory are acceptable on the target laptop

---

## Phase 1 — stable v1 snapshot build
Goal: create the first real usable local system.

### Deliverables
- fixed snapshot ingest pipeline
- repeatable local build
- hybrid retrieval over chosen corpus
- evidence/citation-aware bounded boost
- offline query path
- CLI interface
- build integrity report

### Exit criteria
- reproducible index build
- no runtime network dependency
- acceptable disk footprint
- acceptable query latency
- acceptable retrieval quality in spot checks

---

## Phase 2 — evaluation and tuning
Goal: measure and tune, not add major new subsystems.

### Evaluate
- Recall@k
- nDCG@k
- citation validity rate
- abstention behavior
- median and p95 latency
- peak memory usage

### Tune
- BM25 top-k
- dense top-k
- RRF parameters
- evidence boost weights
- citation boost weights
- recency boost weights

### Exit criteria
- retrieval quality meets target threshold
- citation hallucination is near zero
- system remains within laptop memory/latency budget

---

## Phase 3 — pick only one major extension
Do **one** of the following after v1 is stable:
- cross-encoder reranking
- daily updates
- stronger evidence/conflict modeling

Do not add all three at once.

---

## 10. Evaluation plan

Keep evaluation simple and decision-oriented.

### Retrieval metrics
- Recall@10 / Recall@20
- nDCG@10
- MRR if useful

### Generation metrics
- citation validity rate
- unsupported-claim rate from manual review
- abstention quality on weak-evidence queries

### Performance metrics
- median query latency
- p95 query latency
- peak memory usage
- index size on disk

### Release gates
Define explicit thresholds before shipping v1, e.g.:
- Recall@20 above target
- citation validity effectively 100%
- acceptable latency on the target laptop
- no runtime network dependency

Exact thresholds should be filled in after Phase 0 measurements.

---

## 11. Minimal tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Text/metadata store | SQLite + FTS5 |
| Vector store | LanceDB |
| Dense model | MedCPT query encoder |
| Article vectors | downloaded precomputed MedCPT embeddings |
| LLM | Ollama, default 8B |
| Interface | CLI first |

---

## 12. Minimal implementation order

Build in this order:
1. SQLite schema + FTS5
2. LanceDB vector load/search
3. BM25 retrieval
4. dense retrieval
5. RRF fusion
6. local answer generation
7. citation validation
8. evidence/citation boost
9. evaluation harness

This order minimizes wasted work and keeps the main loop testable early.

---

## 13. Key simplifications versus the previous plan

This revision intentionally narrows scope:
- replaces **“consensus”** with **“evidence-aware”**
- freezes to a **snapshot** instead of supporting updates in v1
- removes **cross-encoder reranking** from v1
- removes **consensus/conflict modeling** from v1
- removes **daily updates** from v1
- treats **offline query-time** as the hard requirement, not fully offline setup
- makes **data integrity checks** a formal deliverable
- keeps citation weighting **small and bounded**

---

## 14. Recommended immediate next step

Implement or refine **Phase 0** around the real v1 architecture:
- keep the current local prototype loop
- ensure the code path cleanly supports the downloaded-vector production flow
- add build integrity reporting early
- define evaluation thresholds once baseline measurements are in

This keeps the project ambitious enough to be useful, while greatly reducing v1 risk.
