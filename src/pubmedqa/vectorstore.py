"""LanceDB vector store (cosine).

Phase 0 (tens of thousands of vectors) runs brute-force — fast and exact.
At scale, call build_index() to create an IVF-PQ index (the disk/RAM-light
default from the plan); validate nprobes/recall in the Phase 0 study.
"""
import lancedb
import pyarrow as pa
from . import config


def _db():
    config.ensure_dirs()
    return lancedb.connect(str(config.LANCE_DIR))


def _table(pmids, vectors):
    return pa.table({
        "pmid": pa.array(list(pmids), pa.int64()),
        "vector": pa.array([v.tolist() for v in vectors],
                           pa.list_(pa.float32(), config.EMBED_DIM)),
    })


def create(pmids, vectors, overwrite=True):
    db = _db()
    return db.create_table(config.LANCE_TABLE, data=_table(pmids, vectors),
                           mode="overwrite" if overwrite else "create")


def add(pmids, vectors):
    tbl = _db().open_table(config.LANCE_TABLE)
    tbl.add(_table(pmids, vectors))
    return tbl


def build_index(num_partitions=256, num_sub_vectors=96):
    """IVF-PQ index for scale. num_sub_vectors=96 -> ~96 bytes/vec (PQ)."""
    tbl = _db().open_table(config.LANCE_TABLE)
    tbl.create_index(metric="cosine", num_partitions=num_partitions,
                     num_sub_vectors=num_sub_vectors, vector_column_name="vector")
    return tbl


def search(query_vec, topk, nprobes=20):
    tbl = _db().open_table(config.LANCE_TABLE)
    q = tbl.search(query_vec.tolist()).metric("cosine").limit(topk).select(["pmid"])
    try:
        q = q.nprobes(nprobes)   # only meaningful once an IVF index exists
    except Exception:
        pass
    return [r["pmid"] for r in q.to_list()]
