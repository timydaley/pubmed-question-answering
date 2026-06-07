"""LanceDB vector store (cosine).

Phase 0 (tens of thousands of vectors) runs brute-force — fast and exact.
At scale, call build_index() to create an IVF-PQ index (the disk/RAM-light
default from the plan); validate nprobes/recall in the Phase 0b study.

All functions take an optional `table` name so Phase 0b can use a separate
verify table without touching the main index.
"""
import lancedb
import pyarrow as pa
from . import config


def _db():
    config.ensure_dirs()
    return lancedb.connect(str(config.LANCE_DIR))


def _arrow(pmids, vectors):
    return pa.table({
        "pmid": pa.array(list(pmids), pa.int64()),
        "vector": pa.array([list(v) for v in vectors],
                           pa.list_(pa.float32(), config.EMBED_DIM)),
    })


def create(pmids, vectors, overwrite=True, table=config.LANCE_TABLE):
    return _db().create_table(table, data=_arrow(pmids, vectors),
                              mode="overwrite" if overwrite else "create")


def add(pmids, vectors, table=config.LANCE_TABLE):
    tbl = _db().open_table(table)
    tbl.add(_arrow(pmids, vectors))
    return tbl


def build_index(table=config.LANCE_TABLE, num_partitions=256, num_sub_vectors=96):
    """IVF-PQ index for scale. num_sub_vectors=96 -> ~96 bytes/vec (PQ)."""
    tbl = _db().open_table(table)
    tbl.create_index(metric="cosine", num_partitions=num_partitions,
                     num_sub_vectors=num_sub_vectors, vector_column_name="vector")
    return tbl


def search(query_vec, topk, table=config.LANCE_TABLE, nprobes=20):
    tbl = _db().open_table(table)
    q = tbl.search(list(query_vec)).metric("cosine").limit(topk).select(["pmid"])
    try:
        q = q.nprobes(nprobes)   # only meaningful once an IVF index exists
    except Exception:
        pass
    return [r["pmid"] for r in q.to_list()]
