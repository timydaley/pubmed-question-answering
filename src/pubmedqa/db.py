"""SQLite store: papers + contentless FTS5 (BM25) + citations.

FTS5 uses content='papers' (external-content) so the text is stored once in
`papers`, not duplicated in the index — the disk-saving choice from the plan.
"""
import sqlite3
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    pmid      INTEGER PRIMARY KEY,
    title     TEXT,
    abstract  TEXT,
    journal   TEXT,
    year      INTEGER,
    mesh      TEXT,
    pubtypes  TEXT,
    retracted INTEGER DEFAULT 0
);
CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    title, abstract,
    content='papers', content_rowid='pmid', tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS citations (
    pmid           INTEGER PRIMARY KEY,
    citation_count INTEGER,
    rcr            REAL
);
"""

_COLS = ["pmid", "title", "abstract", "journal", "year", "mesh", "pubtypes", "retracted"]


def connect():
    config.ensure_dirs()
    con = sqlite3.connect(config.SQLITE_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con


def init_db(con):
    con.executescript(SCHEMA)
    con.commit()


def insert_papers(con, records):
    rows = [tuple(r[c] for c in _COLS) for r in records]
    con.executemany(
        "INSERT OR REPLACE INTO papers(pmid,title,abstract,journal,year,mesh,pubtypes,retracted)"
        " VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    return len(rows)


def rebuild_fts(con):
    """(Re)build the external-content FTS index from the papers table."""
    con.execute("INSERT INTO papers_fts(papers_fts) VALUES('rebuild');")
    con.commit()


def upsert_citations(con, rows):
    con.executemany(
        "INSERT OR REPLACE INTO citations(pmid,citation_count,rcr) VALUES (?,?,?)", rows)
    con.commit()


def bm25_search(con, fts_query, topk):
    """Return PMIDs ranked best-first. FTS5 bm25() is lower=better."""
    # external-content FTS5 exposes the content rowid as `rowid` (== pmid here).
    cur = con.execute(
        "SELECT rowid AS pmid, bm25(papers_fts) AS s FROM papers_fts "
        "WHERE papers_fts MATCH ? ORDER BY s LIMIT ?", (fts_query, topk))
    return [row[0] for row in cur.fetchall()]


def fetch_papers(con, pmids):
    if not pmids:
        return {}
    q = ",".join("?" * len(pmids))
    cur = con.execute(f"SELECT {','.join(_COLS)} FROM papers WHERE pmid IN ({q})", pmids)
    return {row[0]: dict(zip(_COLS, row)) for row in cur.fetchall()}


def fetch_citations(con, pmids):
    if not pmids:
        return {}
    q = ",".join("?" * len(pmids))
    cur = con.execute(
        f"SELECT pmid,citation_count,rcr FROM citations WHERE pmid IN ({q})", pmids)
    return {row[0]: {"citation_count": row[1], "rcr": row[2]} for row in cur.fetchall()}
