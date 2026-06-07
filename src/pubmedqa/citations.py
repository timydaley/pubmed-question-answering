"""Citation signal (citation_count + RCR).

Phase 0 uses the iCite *API* (fine for sample sizes). At full scale, replace with
the iCite/NIH-OCC *bulk* download joined by PMID (see plan §2/§6).
"""
import requests
from . import config, db


def fetch_icite(pmids, batch=200):
    rows = []
    for i in range(0, len(pmids), batch):
        chunk = pmids[i:i + batch]
        r = requests.get(config.ICITE_API,
                         params={"pmids": ",".join(str(p) for p in chunk)},
                         timeout=120)
        r.raise_for_status()
        for d in r.json().get("data", []):
            rows.append((d.get("pmid"),
                         d.get("citation_count"),
                         d.get("relative_citation_ratio")))
    return rows


def ingest(con, pmids):
    rows = fetch_icite(pmids)
    db.upsert_citations(con, rows)
    return len(rows)
