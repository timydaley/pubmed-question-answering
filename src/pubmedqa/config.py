"""Central config. Override paths/models via environment variables.

Point PUBMEDQA_DATA at your external SSD so the index lives there.
"""
import os
from pathlib import Path

# --- Storage (put this on the external SSD) ---------------------------------
DATA_ROOT = Path(os.environ.get("PUBMEDQA_DATA", Path.home() / "pubmedqa_data"))
RAW_DIR = DATA_ROOT / "raw"
SQLITE_PATH = DATA_ROOT / "pubmed.sqlite"
LANCE_DIR = DATA_ROOT / "lancedb"
LANCE_TABLE = "articles"
LANCE_VERIFY_TABLE = "ncbi_verify"   # Phase 0b: downloaded NCBI vectors

# --- Models (MedCPT; PIN the revision for production reproducibility) --------
ARTICLE_ENCODER = "ncbi/MedCPT-Article-Encoder"
QUERY_ENCODER = "ncbi/MedCPT-Query-Encoder"
MEDCPT_REVISION = os.environ.get("MEDCPT_REVISION", "main")
EMBED_DIM = 768
ART_MAXLEN = 512   # MedCPT article encoder
QRY_MAXLEN = 64    # MedCPT query encoder

# --- LLM (local MLX on Apple Silicon) ---------------------------------------
LLM_BACKEND = os.environ.get("PUBMEDQA_LLM_BACKEND", "mlx")
LLM_MODEL = os.environ.get("PUBMEDQA_LLM", "mlx-community/Llama-3.1-8B-Instruct-4bit")
LLM_MAX_TOKENS = int(os.environ.get("PUBMEDQA_LLM_MAX_TOKENS", "2500"))
LLM_TEMPERATURE = float(os.environ.get("PUBMEDQA_LLM_TEMPERATURE", "0.0"))

# --- Retrieval (v1 = lean: RRF-only, cross-encoder OFF) ----------------------
RRF_K = 60
BM25_TOPK = 100
DENSE_TOPK = 100
USE_CROSS_ENCODER = False   # v1 lean; flip on in Phase 3 if latency allows
TOP_N_CONTEXT = 10
QUERY_OVERLAP_MIN = 1
QUERY_OVERLAP_BONUS = 0.02
KEYWORD_FILTER_ENABLED = True
KEYWORD_FILTER_MIN_REL = 0.65
KEYWORD_FILTER_BONUS = 0.04
EVIDENCE_TYPE_BONUS = 0.05
EVIDENCE_TYPE_PENALTY = 0.03
DEDUP_TITLE_SIM = 0.92
DEDUP_TOKEN_JACCARD = 0.80
BALANCED_CONTEXT_CLINICAL_QUOTA = 5
BALANCED_CONTEXT_MECH_QUOTA = 5
CLINICAL_QUERY_EVIDENCE_MULTIPLIER = 2.0
CLINICAL_QUERY_MECH_PENALTY = 0.06
CLINICAL_QUERY_CLINICAL_QUOTA = 7
CLINICAL_QUERY_MECH_QUOTA = 3

# --- Citation weighting (bounded booster; tuned empirically in Phase 2) ------
ALPHA = 0.10          # impact weight (booster, not override)
RELEVANCE_GATE = 0.0  # min normalized fused score before impact can reorder
IMPACT_FLOOR = 0.10   # cold-start floor: new/zero-citation papers still surface

# --- External sources --------------------------------------------------------
PUBMED_BASELINE_BASE = "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/"
ICITE_API = "https://icite.od.nih.gov/api/pubs"
# Precomputed MedCPT article embeddings: embeds_chunk_{0..37}.npy (N~1M x 768),
# pmids_chunk_{i}.json (aligned PMID list), pubmed_chunk_{i}.json (pmid -> {d,t,a,m}).
MEDCPT_EMBEDDINGS_BASE = "https://ftp.ncbi.nlm.nih.gov/pub/lu/MedCPT/pubmed_embeddings/"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def device() -> str:
    """Best available torch device on this machine (Metal on the M1 Max)."""
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def ensure_dirs() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
