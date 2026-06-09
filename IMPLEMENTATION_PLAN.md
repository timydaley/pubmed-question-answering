# PubMed Question-Answering — Implementation Plan (MacBook Pro / M1 Max / 32 GB)

> Goal: A **fully local** tool that answers medical/scientific questions by retrieving relevant
> PubMed papers, **weighted toward higher-impact (more-cited) papers** to bias answers toward
> scientific consensus — while preserving relevance. Local database, local LLM.
>
> **Target hardware: MacBook Pro, Apple M1 Max, 32 GB unified memory.** This document is tuned to
> that machine. The hardware is the dominant design constraint — see §0.

---

## 0. What the hardware forces us to decide (read this first)

The M1 Max / 32 GB target shapes the project, but the **single biggest unlock is not computing the
embeddings locally at all** — see limit #1.

1. **Embedding wall-clock time was the binding constraint — and we sidestep it.** Embedding ~24M
   abstracts with MedCPT (a 109M-param BERT) on the M1 Max GPU would take **days** of sustained load
   and thermal throttling. **So we don't.** NCBI publishes **precomputed MedCPT article embeddings
   for all of PubMed** (`ftp.ncbi.nlm.nih.gov/pub/lu/MedCPT/pubmed_embeddings/`); we **download**
   them. This makes **full-PubMed QA feasible on this laptop** and removes the reason to scope the
   corpus. Local embedding survives only as (a) a fallback and (b) the path for daily-delta papers
   not yet in the snapshot (a few thousand/day — trivial on MPS). See §3.
2. **Unified memory is shared** between OS, the LLM (via Metal), the (tiny) query encoder, and the
   vector index. 32 GB is fine because at query time we run only the **MedCPT Query-Encoder once per
   question** plus an ~8–14B LLM; the heavy article encoder is never run at scale. → **No 70B
   models.** LanceDB IVF-**PQ** keeps the 24M-vector index searchable with a sub-GB RAM footprint
   (vectors stay mmap'd on disk).
3. **Servers are friction on a laptop.** Postgres+pgvector or Qdrant mean running/maintaining a DB
   server and RAM-hungry HNSW builds. → **Prefer embedded, memory-mapped, Mac-native stores
   (LanceDB + SQLite) with zero servers.**

**Consequences baked into this plan:**
- **Recommended path: download precomputed MedCPT embeddings → index all ~24M PubMed abstracts.**
  Scoped-slice + local-embedding is the documented fallback (no GPU / custom model). See §3.
- **Storage = SQLite (metadata + citations + BM25 via FTS5) + LanceDB (dense vectors).** No servers.
- **Decision:** keep the system **local**; use the cloud (**RunPod**) only to **embed + build the
  compressed index**, then download artifacts (§3.6/§3.7).
- **Scope:** **full ~24M PubMed** — the disk constraint is **resolved** (external SSD), so no corpus
  scoping is required.
- **Disk is no longer binding;** PQ vectors + contentless FTS5 are still good practice (smaller =
  faster), not survival measures — see §3.7.
- **Quantization stays the default** — **PQ for vectors** (37 GB → ~2–4 GB).
- **LLM default ≈ 8B (Metal/Ollama); 14B is the ceiling.**
- **Pin the exact MedCPT version** so downloaded article vectors match locally-encoded query vectors.

---

## 1. Answering the project's framing questions

| Question | Answer (M1 Max context) |
|---|---|
| **RAG + a vector DB?** | **Yes.** Dense retrieval feeding a local LLM that answers *with citations*. The vector DB is **LanceDB** (embedded, on-disk, memory-mapped) rather than a server. |
| **Tri-letter (trigram) index?** | **Not as the primary retriever.** The right lexical partner for dense search is **BM25**, which we get for free + embedded via **SQLite FTS5**. Trigram (optional) only for fuzzy drug/gene-name lookup. |
| **A combination?** | **Yes, the core design:** BM25 (FTS5) + dense (LanceDB/MedCPT) → **RRF fusion** → **cross-encoder rerank** → **bounded citation/impact re-score**. See §5. |
| **Other ideas?** | **Download precomputed MedCPT embeddings** (skip local embedding entirely); field-normalized impact (**RCR**, not raw counts); biomedical embeddings (**MedCPT**); MeSH soft-filtering; consensus/conflict surfacing; quantization. |

---

## 2. Key research findings (informs every decision below)

**Corpus — PubMed/MEDLINE**
- NLM publishes the **annual MEDLINE/PubMed baseline** (~40M records) as XML over FTP
  (`ftp.ncbi.nlm.nih.gov/pubmed/baseline/`), ~46 GB compressed, plus **daily update files**.
- Each record: PMID, title, **abstract**, authors, journal, **publication date**, **MeSH terms**,
  publication types (e.g. *Review*, *Meta-Analysis*, *RCT*), and retraction markers.
- We need this XML for **text + metadata + BM25** regardless of where vectors come from. We do
  **not** embed it locally (see §0/§3) — vectors are downloaded.

**Impact signal (the "weight toward highly cited" requirement)**
- PubMed XML has **no** citation counts. Source needed: PMID-keyed, **bulk-downloadable**, offline.
  - **NIH iCite / NIH Open Citation Collection** — *preferred*. Bulk download keyed by PMID; gives
    raw citation count **and the Relative Citation Ratio (RCR)** (field- and time-normalized;
    RCR 1.0 = median NIH-funded paper in that field). **Coverage is partial (~23M of ~40M, ~58%)**,
    weakest for older/non-English papers.
  - **OpenAlex** snapshot — gap-filler. Has `cited_by_count`, maps via PMID/DOI.
- **Decision:** primary = **iCite RCR + count**; OpenAlex offline gap-fill; tier + report coverage.
- iCite is partial globally; on the indexed corpus we **measure** actual coverage and tier the
  source (RCR → OpenAlex → neutral), reporting it per answer (§6).

**Embeddings — biomedical-specific, and already computed for us**
- **MedCPT** (NCBI): Query-Encoder + Article-Encoder (768-d) contrastively trained on 255M PubMed
  search-log query→article pairs, plus a **cross-encoder reranker**. SOTA zero-shot biomedical IR.
  **Only one size exists — 109M params (PubMedBERT-base, 768-d); there is no smaller/distilled
  MedCPT.** That's fine: with downloaded vectors we run only the tiny Query-Encoder at query time.
- **Precomputed article embeddings are published — download instead of compute:**
  - **NCBI**: MedCPT embeddings for **all of PubMed** at
    `ftp.ncbi.nlm.nih.gov/pub/lu/MedCPT/pubmed_embeddings/`.
  - **MedRAG** (`MedRAG/pubmed` on HuggingFace): a **23.9M-article** PubMed corpus (text snippets,
    ~296 tokens avg) with **precomputed MedCPT/Contriever/SPECTER** embeddings auto-downloaded.
  - **Why not a smaller embedding model** (e.g. `bge-small`/`MiniLM`): it would make our vectors
    incompatible with these free embeddings, forcing days of local re-embedding to save a few
    hundred MB. If smaller vectors are ever needed, use **PQ/int8 quantization** on the 768-d MedCPT
    vectors instead — same space, keeps the downloads.
  - **Cloud-embed (option C, RunPod — see §3.6)** for a custom slice/model **or to backfill papers
    newer than NCBI's snapshot**: a rented GPU embeds full PubMed in ~2–4 h for a few dollars. Local
    embedding survives only for the small daily delta + as a no-cloud fallback.

**Generation — local LLM on Metal**
- **Ollama** (llama.cpp + Metal) serves models using the M1 Max GPU and unified memory.
  Practical fits on 32 GB (q4_K_M): **Llama 3.1 8B (~5 GB)**, **Qwen2.5 7B/14B (~5/9 GB)**.
  14B is the realistic ceiling alongside the rest of the pipeline. The LLM only *synthesizes
  retrieved evidence with citations* — retrieval quality matters more than LLM size.

**Local stores — embedded, no servers**
- **LanceDB** — embedded, columnar (Arrow), memory-mapped, on-disk ANN (IVF-PQ), excellent on Apple
  Silicon, scales to millions with low RAM. **Primary vector store.** (FAISS IVF-PQ = alternative.)
- **SQLite** — embedded; holds metadata + the citation table, and **BM25 ranking via the FTS5
  extension**. Zero server, trivial backups (one file). (DuckDB = alternative for heavier analytics.)

---

## 3. Corpus acquisition (download vectors — full PubMed is now feasible)

Because the heavy embedding step is downloaded, not computed, **the whole ~24M-abstract PubMed
corpus fits on this laptop**. Corpus *scoping* is now an *option* (to save disk / shrink download),
not a forced constraint.

**Recommended path — download everything:**
1. **Text + metadata:** PubMed baseline + daily updates XML (or the MedRAG `pubmed` text corpus) →
   SQLite (with FTS5 BM25). Needed for display, BM25, and metadata filters.
2. **Vectors:** download **precomputed MedCPT embeddings** (NCBI FTP or MedRAG) → LanceDB.
3. **Citations:** iCite/NIH-OCC bulk (+ OpenAlex fill) → SQLite, joined by PMID.
4. **Pin the MedCPT version** used for the downloaded article vectors; use the matching
   Query-Encoder locally.

**Disk/RAM budget (full ~24M corpus — the new binding constraint is disk, not compute):**
| Quantity | Full ~24M corpus | Note |
|---|---|---|
| Precomputed vector **download** | **~30–75 GB** | depends on precision (fp16 ≈ 37 GB; fp32 ≈ 73 GB). One-time. Confirm exact size from the FTP/HF listing. |
| Vectors on disk (LanceDB) | ~37 GB fp16 (less with PQ/int8) | mmap'd; not all resident in RAM. |
| Query-time RAM for ANN | **sub-GB** with IVF-**PQ** | PQ codes are tiny; full vectors stay on disk. |
| SQLite text + FTS5 + metadata + citations | ~tens of GB | One file. |
| Raw baseline XML during ingest | streamed & discarded | Don't retain the ~250–350 GB decompressed. |
| **Total local footprint** | **~100+ GB** | The real cost now — check free SSD space (§13). |

**Optional scoping (only to shrink download/disk):** recent N years, or one domain by MeSH — index a
subset of the downloaded vectors. No longer needed for compute reasons.

**Fallback — local/cloud embedding** (only if precomputed vectors are unusable, you want a different
model/slice, or you must backfill papers newer than NCBI's snapshot): embed on a rented **RunPod**
GPU (detailed in **§3.6**) or locally (overnight, resumable). Kept for completeness; not the default.

### 3.5 Leanest viable v1 (ship this first — directly serves "keep it lightweight")

The full pipeline (§5) is the destination, not the starting point. **v1 deliberately omits the
heaviest *query-time* parts** and proves end-to-end value fast. (Corpus size is no longer the lever —
downloaded vectors make full PubMed cheap — so v1 can index the full corpus or a slice freely.)

| Included in v1 | Deferred (added later, behind config) |
|---|---|
| **Downloaded MedCPT vectors** (full corpus or a slice) | local/cloud re-embedding (fallback only) |
| **RRF hybrid: FTS5 BM25 + LanceDB dense** | **MedCPT cross-encoder rerank → Phase 3** (latency) |
| **Citation weighting** (RCR + count, bounded) | **pre-computed consensus/conflict signals → Phase 3** |
| Grounded LLM answer + **`[PMID]` citation validation** | MeSH soft-boost + query expansion (Phase 2) |
| 8B LLM on Metal | 14B option (only if fidelity needs it) |

Rationale: the cross-encoder and consensus NLI passes are the two biggest per-query costs on a
laptop; RRF + citation weighting already delivers the project's core promise (relevant + consensus-
weighted answers). Add weight only after v1 is measured and working.

### 3.6 Option C — Cloud embedding on RunPod (custom corpus / snapshot backfill)

Use this **only** when the precomputed download (§3 default) isn't enough:
- **Backfill the snapshot gap** — NCBI's precomputed vectors stop at a snapshot date; papers
  published after it have no vectors. If the gap is large (hundreds of thousands+), embed them in
  bulk on a rented GPU rather than grinding for days on the laptop.
- **Custom slice/model** — a different embedding model, full-text chunks, or a corpus PubMed doesn't
  cover.

> This is batch **inference** (forward passes through the pretrained MedCPT article encoder), **not
> training** — MedCPT is already trained; we only generate embeddings. The RunPod workflow is the
> same either way.

**GPU choice — MedCPT is a 109M-param BERT, so even a modest GPU is plenty:**
| GPU | VRAM | ~throughput\* | full ~24M | typical $/hr | full-corpus cost |
|---|---|---|---|---|---|
| RTX 4090 | 24 GB | ~2k docs/s | ~3–4 h | ~$0.34–0.69 | ~$1–3 |
| A40 / L40S | 48 GB | ~2.5k docs/s | ~2.5–3 h | ~$0.4–0.9 | ~$1–3 |
| A100 80 GB | 80 GB | ~4k docs/s | ~1.5–2 h | ~$1.2–1.9 | ~$3–4 |

\*Rough, seq-len ~512, fp16, batched — **benchmark on a 50k sample first**. For a backfill of ~1M
papers it's minutes and pennies; a single RTX 4090 is plenty and multi-GPU is unnecessary.

**Workflow:**
1. **Create a Network Volume** (~150 GB) in a region that has your chosen GPU — it persists the
   corpus + output vectors across pod restarts/spot-interruptions and mounts at `/workspace`.
2. **Deploy a GPU Pod** from the official **RunPod PyTorch** template (torch + CUDA preinstalled);
   attach the volume. (Community Cloud / spot is cheapest; the resumable script below tolerates
   interruption.)
3. **Get the corpus onto the pod:** either `wget`/FTP the PubMed baseline directly (pods have fast
   bandwidth) and parse it there, or prepare a `pmid,title,abstract` Parquet locally and upload via
   `runpodctl send` / `scp` / an S3 or HF bucket.
4. `pip install -U transformers safetensors pyarrow tqdm` (torch is already in the template).
5. **Run the embed script** (below) — fp16, batched, **one Parquet shard per batch on the volume** so
   a restart resumes by skipping existing shards.
6. **Output** = Parquet shards (`pmid:int64`, `vector:list<float16>[768]`), trivially merged/loaded
   into LanceDB.
7. **Transfer back:** `runpodctl send <dir>` → `runpodctl receive` on the laptop, or push to HF Hub /
   S3 and pull down. Load into LanceDB locally.
8. **Terminate the pod** to stop GPU billing; delete the volume when done (volume storage bills while
   it exists, ~$0.05–0.07/GB/mo).

**Sample embed script** (`embed_medcpt.py`) — resumable, fp16, `[CLS]` pooling (matches NCBI's
precomputed vectors so shards drop into the same index):
```python
import torch, pyarrow as pa, pyarrow.parquet as pq
from transformers import AutoTokenizer, AutoModel
from pathlib import Path

DEV, BATCH, MAXLEN = "cuda", 256, 512          # A100 handles BATCH 512+
SRC = "/workspace/corpus.parquet"              # columns: pmid, title, abstract
OUT = Path("/workspace/embeddings"); OUT.mkdir(exist_ok=True)

REV = "main"  # PIN this to the exact revision used for any NCBI vectors you mix with
tok   = AutoTokenizer.from_pretrained("ncbi/MedCPT-Article-Encoder", revision=REV)
model = AutoModel.from_pretrained("ncbi/MedCPT-Article-Encoder", revision=REV).to(DEV).half().eval()

rows = pq.read_table(SRC, columns=["pmid", "title", "abstract"]).to_pylist()
for i in range(0, len(rows), BATCH):
    shard = OUT / f"shard_{i:09d}.parquet"
    if shard.exists():                          # resume: skip already-done batches
        continue
    batch = rows[i:i + BATCH]
    pairs = [[r["title"] or "", r["abstract"] or ""] for r in batch]   # article enc takes [title, text]
    enc = tok(pairs, truncation=True, padding=True, max_length=MAXLEN, return_tensors="pt").to(DEV)
    with torch.no_grad():
        vecs = model(**enc).last_hidden_state[:, 0, :].float().cpu()    # [CLS] embedding
    pq.write_table(
        pa.table({"pmid":  [r["pmid"] for r in batch],
                  "vector": pa.array(vecs.tolist(), pa.list_(pa.float16(), 768))}),
        shard)
```

**Consistency rule (non-negotiable):** anything you embed on RunPod must use the **identical MedCPT
article-encoder revision** as any downloaded NCBI vectors it's mixed with, and queries must use the
matching **`ncbi/MedCPT-Query-Encoder`** locally — otherwise the vector spaces won't align and recall
collapses. Pin `revision=` everywhere.

**Build on the pod, bring back lean (the disk-saving move).** Don't just embed on RunPod — **assemble
and compress the whole index there**, so the laptop never stages the heavy intermediates:
1. On the pod: download/parse XML → build **SQLite + (contentless) FTS5**; embed (or download
   precomputed) → build a **PQ-compressed LanceDB**; join iCite/OpenAlex citations.
2. The pod absorbs the ~250 GB raw XML and ~37 GB raw fp16 vectors — **none of that touches the
   laptop**.
3. Transfer home only the **finished, compact artifacts** (~30–40 GB: PQ vectors + SQLite db) via
   `runpodctl` / S3 / HF.
4. Terminate the pod + delete the volume.

### 3.7 Local storage plan (full corpus on external SSD — disk constraint resolved)

**Decided:** the storage problem is solved (external SSD / sufficient disk), so we keep the **full
~24M PubMed corpus locally** with **no scoping required**. The query system stays fully
local/offline; cloud is only for the one-time embed + index build (§3.6).

Footprint (target: a **1–2 TB external NVMe**, leaving ample room):

| Component | fp16 / naïve | With PQ + contentless FTS5 | Technique |
|---|---|---|---|
| Vectors | ~37 GB | **~2–4 GB** | **LanceDB Product Quantization** (PQ ~64–128 B/vec); recall validated in Phase 0 |
| Abstract text + **FTS5** | ~40–60 GB | ~25–35 GB | **contentless / external-content FTS5** (no duplicate text copy) |
| Metadata + citations | a few GB | a few GB | — |
| Model weights (LLM + encoders) | ~6–12 GB | ~6–12 GB | — |
| **Local steady-state** | **~90–115 GB** | **~40–55 GB** | comfortable on a 1–2 TB SSD |

PQ + contentless FTS5 stay the default — not for survival now, but because smaller = faster loads and
ANN. Plenty of headroom for full text or future full-text chunks if desired later.

**Path placement:** put the LanceDB dir + SQLite db on the external SSD; point the app at it via
config. (Internal SSD also fine if it has ~100+ GB free.)

---

## 4. High-level architecture (all embedded, no servers)

```
                       ┌──────────────────── OFFLINE / INGEST (mostly downloads) ───────────────┐
  PubMed XML (FTP) ────┼─ stream-parse (lxml) → metadata+MeSH+pub-types → SQLite (+FTS5 BM25)     │
  or MedRAG text       │                                                                          │
  NCBI/MedRAG  ────────┼─ DOWNLOAD precomputed MedCPT vectors ──────────────► LanceDB (IVF-PQ)    │
  precomputed vectors  │      (no local embedding; pin MedCPT version)                            │
  iCite/NIH-OCC ───────┼─ citation count + RCR, join by PMID ─────────────► SQLite citations      │
  (+ OpenAlex fill)    │                                                                          │
  daily delta only ────┼─ embed NEW papers locally (MedCPT Article-Enc, MPS) → upsert LanceDB     │
                       └────────────────────────────────────────────────────────────────────────┘

                       ┌──────────────────── ONLINE / QUERY (single process) ──────────────────┐
  user question  ──►   │ 1. (opt) query expansion + MeSH mapping                                │
                       │ 2. embed query (MedCPT Query-Enc, MPS)                                 │
                       │ 3. retrieve: FTS5 BM25 top-k  ∥  LanceDB dense top-k  (+ filters)      │
                       │ 4. Reciprocal Rank Fusion → candidates                                 │
                       │ 5. cross-encoder rerank (MedCPT CrossEnc, MPS) — config-gated          │
                       │ 6. citation/impact re-score (bounded): RCR + recency + evidence tier   │
                       │ 7. assemble grounded prompt (top-N + metadata + impact + coverage)     │
                       │ 8. Ollama LLM (Metal) answers WITH inline [PMID] + caveats             │
                       │ 9. citation-validation: every [PMID] must be in the retrieved set      │
                       └────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Retrieval pipeline (the "combination")

**A — Lexical (BM25 via SQLite FTS5).** Exact terminology, gene/drug names, acronyms, rare tokens.
Embedded, no server; FTS5 provides BM25 ranking natively.

**B — Dense (semantic).** MedCPT Query-Encoder (MPS) → LanceDB ANN over MedCPT article vectors.
Catches paraphrase/synonymy ("heart attack" ↔ "myocardial infarction"). Note: **MedCPT inference
uses the GPU (MPS); LanceDB's ANN search runs on CPU** (Arrow/SIMD) — both are lightweight, and the
single query vector per request makes CPU-side search trivially fast. **IVF-PQ recall is validated
in Phase 0** (pick `nprobes` giving >95% recall vs. brute force).

**C — Fusion (RRF).** Reciprocal Rank Fusion merges A and B by rank (scale-free, robust). ~100–200
candidates.

**D — Cross-encoder rerank (NOT in v1 — Phase 3, behind a flag).** MedCPT CrossEnc (MPS) jointly
scores (query, abstract) for top ~50.
- **v1 ships with `use_cross_encoder=False` — RRF ranking is the baseline that goes out the door.**
  The cross-encoder is the single biggest per-query cost on this laptop; it's added only after v1
  works and only if the latency budget (target < ~500 ms end-to-end) allows.
- When enabled: **benchmark on this M1 Max first**, **batch on MPS**, cap input to ~50, and apply a
  **timeout fallback** to RRF ranking if the budget is exceeded.

**E — Impact re-score (consensus weighting), on a common 0–1 scale:**

```
final = relevance_norm                 # 0–1 (sigmoid/min-max over Stage D scores)
      + α · impact_norm                # 0–1; α default 0.1  (BOOSTER, not co-equal)
      + β · recency_factor             # 0–1; β default 0.05
      + γ · evidence_tier              # small boost: review/meta-analysis/RCT > case report
```
- **Normalize impact to 0–1** (sigmoid/percentile over RCR) so a big RCR can't swamp relevance.
- **Hard gate:** a result must clear a Stage-D relevance threshold *before* impact can reorder it —
  blocks famous-but-off-topic papers.
- **RCR** (field/time-normalized) rewards consensus influence, not age or field size.
- **Cold-start floor** `impact_norm = 0.1` for zero-citation papers, so timely work still surfaces.
- **Tiered impact source:** `iCite RCR → else OpenAlex count → else neutral`; tier is **logged and
  reported per answer**, never silently dropped.
- Defaults `α=0.1, β=0.05` are **empirically tuned in Phase 2** (§11), not guessed.

**F — Generation.** Pass top-N (≈8–12 on a laptop, to keep prompt/RAM modest) abstracts with metadata
(PMID, year, journal, RCR, study type, impact-coverage note) to the Ollama LLM; instruct it to answer
**only** from provided evidence, cite inline `[PMID]`, report agreement vs. conflict, and refuse when
evidence is thin.

**G — Citation validation.** After generation, check every `[PMID]` against the retrieved set;
flag/strip hallucinated citations.

---

## 6. Handling "scientific consensus" properly

1. **Field-normalized impact (RCR)** instead of raw counts.
2. **Coverage honesty.** iCite covers ~58% of all PubMed (better on a recent/scoped slice). Tier the
   source and **report coverage per answer** ("3/8 papers lack field-normalized impact; raw counts
   used"). Measure coverage on the chosen slice up front.
3. **Evidence hierarchy** — boost systematic reviews / meta-analyses / RCTs (from MeSH pub-types).
4. **Consensus surfacing — not LLM free-form.** Pre-compute pairwise agreement/contradiction over the
   top-N (a cheap NLI/cross-encoder pass on MPS) and feed the LLM a **structured** summary; prompt it
   to report agreement/conflict **only when explicit**, else "insufficient consensus data."
5. **Recency guard** so an old mega-cited paper doesn't bury current consensus.
6. **Retraction awareness** — filter/flag retracted papers (PubMed marks these).
7. **MedCPT coverage check** — verify recall on older/foundational papers; ensemble with a general
   encoder if weak.
8. **MeSH = soft boost, not a hard gate** — hybrid retrieval first; hard MeSH filter only as a last
   resort to avoid zero-result failures.

---

## 7. Storage, memory & performance on the M1 Max

**Unified-memory budget at query time (rough, must total < 32 GB with headroom):**
| Component | Approx. |
|---|---|
| macOS + apps | ~6–8 GB |
| Ollama LLM (8B q4) | ~5–6 GB (14B ≈ 9 GB) |
| MedCPT query + cross-encoder (MPS) | ~1–2 GB |
| LanceDB mmap + SQLite working set | ~2–4 GB |
| **Headroom** | remainder |
→ Fits with an 8B LLM (v1 default). 14B only if fidelity needs it *and* the cross-encoder isn't held
hot. These are estimates — **Phase 0 measures actual query-time resident memory** (query-encoder +
LLM, plus cross-encoder only when enabled) and documents the real total. macOS under load and
LanceDB mmap can be greedier than the table suggests; if the sum of model weights exceeds ~10 GB,
quantize the query-encoder or keep the cross-encoder off. **Never run full-corpus embedding and the
LLM simultaneously** — ingest is a strictly offline phase in v1.

**Ingest engineering (laptop-specific):**
- **Download, don't compute, the bulk vectors** — the big one-time cost is a ~30–75 GB transfer +
  building the LanceDB IVF-PQ index over them (CPU, hours), not GPU embedding. Make the download
  **resumable** (large files; verify checksums).
- **Stream-parse** XML with `lxml.iterparse`; keep only needed fields; never hold the whole file.
- **PMID alignment:** the downloaded vectors are keyed/ordered by PMID — verify every vector maps to
  a text/metadata row (and vice-versa); log/repair mismatches before building the index.
- **Quantize vectors** (fp16 default; PQ/int8 to shrink disk+RAM) — **recall validated in Phase 0**.
- **No HNSW-on-Postgres pain:** LanceDB IVF-PQ is disk-resident; ANN runs on CPU.

**Incremental daily updates (concrete DML):** deletions → soft-delete flag + query-time filter;
revisions → re-embed (Article-Enc on MPS) + **upsert** vector/metadata; new → embed + insert. Daily
volume is a few thousand papers — **trivial to embed locally**, so the article encoder stays
installed for the delta. Validate on one daily batch in Phase 1.

**No chunking for MVP:** one embedding per PMID over title+abstract (~500 tokens, MedCPT's native
granularity) → unambiguous `[PMID]` citation mapping. Revisit only if full text is added later.

---

## 8. Proposed tech stack (all local, Apple-Silicon friendly)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | `transformers`, `torch` (MPS), `lancedb`, `sqlite3` |
| Corpus parse | `lxml` streaming | hundreds of XML files without OOM |
| Vectors | **Precomputed MedCPT** (NCBI FTP / MedRAG), downloaded | 768-d; only the **Query-Encoder** (HF transformers, MPS) runs at query time; Article-Encoder only for daily delta |
| Cloud embed (optional) | **RunPod** GPU Pod (PyTorch template + network volume) | only for custom corpus / snapshot backfill; batch inference, ~$1–4 full corpus (§3.6) |
| Reranker | **MedCPT CrossEnc** (MPS), config-gated | precision boost when enabled |
| Vector store | **LanceDB** (embedded, IVF-PQ, mmap) | no server; FAISS = alternative |
| Metadata + BM25 + citations | **SQLite + FTS5** | one file, BM25 native; DuckDB = alternative |
| Citation data | iCite/NIH-OCC bulk (+ offline OpenAlex fill) | RCR + counts, PMID-keyed |
| LLM serving | **Ollama** (llama.cpp + **Metal**) | default ~8B q4; 14B ceiling; swappable |
| Orchestration | thin Python package + CLI | LangChain optional, not required |
| Interface | CLI first → optional FastAPI + minimal UI | |

---

## 9. Guardrails & concrete defaults

- **Citation weight is a bounded booster, not an override** — relevance gate before re-score;
  `α=0.1, β=0.05`, 0–1 normalized, empirically tuned (§5).
- **Coverage honesty** — tier impact source, report per answer (§6).
- **Cold-start floor** `0.1`, ablated (§5).
- **Cross-encoder** benchmarked on this M1 Max, batched, off-by-default, timeout fallback (§5).
- **Daily-update DML** specified, tested in Phase 1 (§7).
- **No abstract chunking** for MVP (§7).
- **Consensus signals pre-computed**, not LLM free-form (§6).
- **Citation-validation step** rejects hallucinated `[PMID]`s (§5G).
- **MeSH soft boost**, hard filter last resort (§6).
- **Long-tail tiers:** classify *direct-match / related / none*; if <3 direct matches, include up to
  5 labeled *related* papers and report the tier — not a blunt "insufficient evidence."
- **OpenAlex gap-fill offline** (bulk join, monthly refresh), log RCR/OpenAlex/neutral hit rates.
- **Quantization** validated by a recall study before relying on it (§11).
- **Vectors downloaded, not computed** — full ~24M PubMed indexed locally; pin the MedCPT version so
  downloaded article vectors match locally-encoded query vectors (§3).
- **Article encoder kept only for the daily delta**; verify PMID alignment between downloaded vectors
  and text/metadata before building the index (§7).
- **Disk is the new binding constraint** (~100+ GB) — confirm free SSD space before Phase 1 (§3/§13).

---

## 10. Milestones / phased build

> **Status: Phase 0 scaffolded** — runnable code in `src/pubmedqa/` + `scripts/p0_*.py`; see
> `README.md` for the run steps. (Phase 0a uses local embedding on one baseline file to prove the
> loop; Phase 0b verifies the precomputed-vector download aligns.)

**Phase 0 — Spike & verify the download path (de-risk; nothing else starts until this is done).**
**Download a sample of precomputed MedCPT vectors** (NCBI FTP / MedRAG) + matching text/metadata for
a subset, load into LanceDB, embed a query with the **local Query-Encoder**, run dense retrieval +
naive Ollama answer. **Confirm the downloaded article vectors and locally-encoded query vectors share
a space** (sane nearest neighbours). Measurements that **gate later decisions**:
- **Confirm precomputed-vector availability, exact size, precision, and PMID alignment.**
- **fp16 vs PQ/int8 recall** (nDCG@10) → pick storage precision before the full build.
- **LanceDB IVF-PQ `nprobes`** for >95% recall vs. brute force.
- **Query-time resident memory** (Query-Encoder + 8B LLM) → confirm the §7 budget.
- Local embedding throughput on MPS (only to size the **daily-delta** path, not the bulk).
Also: identify/source a **~50-question curated QA benchmark** (BioASQ/TREC-COVID or expert-authored).

**Phase 1 — v1 hybrid retrieval (lean), full corpus.** Download the **full** precomputed vector set +
text/metadata → LanceDB + SQLite. **Measure the snapshot gap** (papers newer than NCBI's vectors); if
large, **backfill via RunPod (§3.6)**, else embed the small gap locally. FTS5 BM25 + LanceDB dense +
**RRF only — cross-encoder stays OFF**. **Measure lexical-only and dense-only recall** (catch a
decorative BM25). Validate **daily-update DML** + soft-delete filtering on one update batch.
*(MeSH soft-boost and query expansion deferred to Phase 2.)*

**Phase 2 — Citation weighting + tuning.** Ingest iCite RCR/counts (+ offline OpenAlex fill), join by
PMID in SQLite. **Measure actual iCite/OpenAlex/neutral coverage across the corpus** and report it
per answer (full PubMed includes older/non-English papers where iCite is sparser). Implement Stage E;
**grid-search `α∈[0,0.3], β∈[0,0.1], γ∈[0,0.05]` + cold-start floor** against the benchmark objective
(maximize consensus-agreement subject to recall@5 > 80%). Add MeSH soft-boost.

**Phase 3 — Generation quality + (optional) rerank.** Grounded prompt + inline `[PMID]` +
**citation-validation**; measure hallucination rate → choose 8B vs. 14B. Add pre-computed
consensus/conflict signals and long-tail tiering. **Now** evaluate enabling the MedCPT cross-encoder
against the latency budget; ship it only if it fits.

**Phase 4 — Harden at full-corpus scale.** Re-confirm quantization/IVF-PQ params on the full ~24M
index, tune ANN recall/latency, production daily incremental updates, disk/backup management.
(No bulk local embedding needed — vectors are downloaded.)

**Phase 5 — Interface & polish.** CLI → optional FastAPI + minimal UI; config for model/`α/β`/scope;
caching.

---

## 11. Evaluation

Three layers + a contamination policy. **Datasets to use, and how much to trust them, depend on what
each component already saw** — see the contamination map below.

**Layer 1 — Retrieval (IR metrics: Recall@k, nDCG@k, MRR).**
- Use **BioASQ qrels** (gold relevant PMIDs; in-corpus since we index full PubMed) to tune fusion.
- ⚠️ **Use a recent BioASQ year (post-2023)** as the *clean* held-out signal — BioASQ/TREC-COVID/
  NFCorpus were MedCPT's own zero-shot eval sets, so older-year recall flatters MedCPT.

**Layer 2 — End-to-end QA accuracy (automatic, exact-match).**
- **MIRAGE** suite (PubMedQA, BioASQ-Y/N, MedQA, MedMCQA, MMLU-Med) → accuracy. Our corpus *is* the
  MedRAG PubMed snapshot, so numbers are comparable to the published MedRAG results.
- **Report RAG − no-RAG delta, not absolutes** — the LLM (Llama 3.1) likely memorized MedQA/MMLU/
  PubMedQA in pretraining, which inflates the no-RAG baseline. Lean on PubMedQA/BioASQ (answer hinges
  on a *retrievable* abstract). Build a small **fresh probe set from post-LLM-cutoff papers** for a
  genuinely uncontaminated signal.

**Layer 3 — Citation-weighting ablation (the differentiator).**
- **α-sweep `[0,0.3]` + ablation ladder** (dense → +BM25 → +RRF → +citation-weighting → +rerank).
- **Robust to contamination by construction:** a *relative* comparison with everything fixed except α
  — MedCPT-eval-overlap and LLM-memorization are constant across α and cancel, so the accuracy-vs-α
  *curve shape* is trustworthy even on "contaminated" sets. Objective: maximize consensus-agreement
  subject to recall@5 > 80%.

**Faithfulness & grounding.**
- **Citation hallucination rate** (already computed): % of cited `[PMID]`s in the retrieved set.
- **Local LLM-judge** scoped to *grounding* (is each claim supported by a shown retrieved abstract),
  not correctness — more objective, less judge-contamination. Use a **different/larger local model**
  than the one judged to avoid self-preference; treat results as directional.

**Contamination map (verified against the MedCPT paper):**
- MedCPT was **trained only on PubMed search logs** — no benchmark in training.
- MedCPT was **zero-shot evaluated on BioASQ, TREC-COVID, NFCorpus** (BEIR-bio) → optimistic there.
- MedCPT **never touched PubMedQA/MedQA/MedMCQA/MMLU-Med** (it's a retriever) → those are MedCPT-clean.
- The **LLM** is the dominant contamination risk for QA accuracy → mitigated via delta + fresh probe.

**Hardware metrics tracked throughout:** peak unified-memory, query latency, ANN recall vs. exact,
thermal/throttle on sustained ingest.

---

## 12. Read-only critique cycle

A read-only subagent gave a prioritized adversarial critique of the prior (server-oriented) plan; all
findings were folded in and then re-tuned for the M1 Max / 32 GB target: iCite ~58% coverage →
tiered + reported impact; α/β normalization + empirical tuning; cross-encoder latency controls;
daily-update DML; MedCPT recency/language-bias check; MeSH soft-boost; no-chunking; pre-computed
consensus signals; citation validation; long-tail tiering; offline OpenAlex; quantization &
recall studies; QA benchmark sourced early; cold-start floor. The hardware rewrite additionally
replaced **Postgres/Qdrant servers with embedded LanceDB + SQLite**, **scoped the corpus to a few
million abstracts**, made **quantization and resumable, benchmarked ingest defaults**, and **capped
the LLM at ~14B (default 8B) on Metal**.

A **second** read-only critique then reviewed this hardware-targeted plan with an explicit
*lightweight* lens. Folded-in changes:
- **Stop assuming, start measuring.** Embedding time restated as a realistic **5–15+ h** estimate
  that **gates slice size after a Phase-0 50k-batch benchmark**; query-time memory and thermal
  behavior measured in Phase 0 (§3/§7/§10).
- **Leaner v1 (new §3.5):** ship **RRF-only (cross-encoder OFF)**, citation weighting, citation
  validation on a **~1M slice**; defer cross-encoder, consensus NLI, MeSH/query-expansion.
- **Validate-early gates moved into Phase 0:** fp16-vs-int8 recall and LanceDB IVF-PQ `nprobes`
  (was Phase 4) — re-embedding is too expensive to defer.
- **Measure iCite coverage on the actual slice before Phase 2**; narrow slice if neutral-tier > 20%.
- **Concrete α/β/γ tuning objective** (grid search; maximize consensus-agreement s.t. recall@5>80%).
- **Live ingest memory monitor + ceiling** to avoid swap; **checkpoint every ~100k**.
- Clarified **LanceDB ANN is CPU-side** (lightweight) while MedCPT runs on MPS.

**Subsequent design change (download precomputed embeddings):** the user proposed offloading the
embedding compute. Research found NCBI publishes **precomputed MedCPT embeddings for all of PubMed**
(and MedRAG packages a 23.9M-article corpus with them). The plan now **downloads vectors instead of
computing them**, which **dissolves the corpus-scoping constraint** — full ~24M PubMed is feasible on
the laptop. Local embedding is demoted to (a) the daily-delta path and (b) a no-cloud fallback. The
binding constraint shifts from **compute** to **disk (~100+ GB)** and a one-time large download.
Confirmed **no smaller MedCPT exists** (109M only) — irrelevant now, since only the tiny Query-Encoder
runs at query time, and switching models would forfeit the free embeddings.

**RunPod cloud-embedding added (§3.6):** concrete workflow (GPU choice, network volume, resumable
fp16 `[CLS]` embed script, transfer-back, teardown) for the cases the download doesn't cover —
**backfilling papers newer than NCBI's snapshot** and custom corpora/models. Framed as batch
inference, not training; ~$1–4 for the full corpus on a single mid-tier GPU. Pinned-revision
consistency rule added so cloud-built vectors align with downloaded ones and local queries.

**Deployment decision + disk strategy (§0/§3.6/§3.7):** user chose **keep system local, cloud only
for embedding**, driver = **tight laptop disk**. Clarified that cloud embedding saves compute, not
local disk; added **"build on the pod, bring back lean"** (assemble + PQ-compress the index on RunPod,
download ~30–40 GB of finished artifacts) and a **disk-minimization** plan (PQ vectors ~2–4 GB +
contentless FTS5; external SSD or recent-years scope as the two paths). Considered full-cloud
deployment and **rejected** it (recurring cost + loss of local/offline/private) per the user's choice.

**Disk constraint resolved (§3.7):** user confirmed storage is solved (external SSD). Plan now locks
to the **full ~24M-corpus, fully-local** path with **no scoping**; PQ + contentless FTS5 kept as
defaults for speed rather than necessity.

**Final v1 decisions:** **8B LLM (fast)** and **RRF-only retrieval (lean, cross-encoder OFF)**. All
major design questions are now closed (§13); remaining items are implementation details settled
during Phase 0/1. Next deliverable is the Phase 0 runbook.

---

## 13. Open questions for the user

All major decisions are now resolved:
1. ~~Disk / scope~~ — **resolved:** storage solved (external SSD), **full ~24M PubMed**, no scoping (§3.7).
2. ~~LLM size~~ — **resolved: 8B (fast)** is the default; 14B documented as an optional upgrade only.
3. ~~Cross-encoder in v1~~ — **resolved: RRF-only (lean)**; cross-encoder deferred to Phase 3, ships
   only if it later fits the latency budget.
4. **Build on RunPod or download precomputed?** Both end the same — lean toward **download precomputed
   for the bulk, RunPod only for the post-snapshot backfill** (§3.6). Final call at Phase 0/1.
