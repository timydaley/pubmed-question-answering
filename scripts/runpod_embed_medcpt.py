#!/usr/bin/env python3
"""RunPod cloud embedding (batch inference, NOT training) — plan §3.6.

Run this ON the RunPod pod (PyTorch template + network volume). It reads a
corpus Parquet, embeds with the MedCPT Article-Encoder on the GPU, and writes
one resumable Parquet shard per batch to the volume. Transfer shards home and
load into LanceDB.

    pip install -U transformers safetensors pyarrow
    python runpod_embed_medcpt.py
"""
import torch
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from transformers import AutoTokenizer, AutoModel

DEV, BATCH, MAXLEN, DIM = "cuda", 256, 512, 768   # A100 handles BATCH 512+
SRC = "/workspace/corpus.parquet"                 # columns: pmid, title, abstract
OUT = Path("/workspace/embeddings")
OUT.mkdir(exist_ok=True)

REV = "main"  # PIN to the same revision as any downloaded NCBI vectors you mix with
tok = AutoTokenizer.from_pretrained("ncbi/MedCPT-Article-Encoder", revision=REV)
model = (AutoModel.from_pretrained("ncbi/MedCPT-Article-Encoder", revision=REV)
         .to(DEV).half().eval())

rows = pq.read_table(SRC, columns=["pmid", "title", "abstract"]).to_pylist()
for i in range(0, len(rows), BATCH):
    shard = OUT / f"shard_{i:09d}.parquet"
    if shard.exists():                  # resume: skip completed batches
        continue
    batch = rows[i:i + BATCH]
    pairs = [[r["title"] or "", r["abstract"] or ""] for r in batch]
    enc = tok(pairs, truncation=True, padding=True, max_length=MAXLEN,
              return_tensors="pt").to(DEV)
    with torch.no_grad():
        emb = model(**enc).last_hidden_state[:, 0, :]              # [CLS]
        emb = torch.nn.functional.normalize(emb, p=2, dim=1)      # match local embed.py
    pq.write_table(
        pa.table({"pmid": [r["pmid"] for r in batch],
                  "vector": pa.array(emb.float().cpu().tolist(),
                                     pa.list_(pa.float16(), DIM))}),
        shard)
    print(f"shard {shard.name} ({i + len(batch)}/{len(rows)})")
