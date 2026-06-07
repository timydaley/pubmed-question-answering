"""Stream-parse MEDLINE/PubMed baseline XML(.gz) into record dicts.

Memory-flat: clears each <PubmedArticle> (and its preceding siblings) after use,
so a multi-hundred-MB file parses in a constant, small footprint.
"""
import gzip
from lxml import etree


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def iter_articles(xml_gz_path):
    """Yield a dict per <PubmedArticle> in a baseline .xml.gz file."""
    with gzip.open(xml_gz_path, "rb") as fh:
        context = etree.iterparse(fh, events=("end",), tag="PubmedArticle")
        for _, elem in context:
            rec = _parse_article(elem)
            if rec is not None:
                yield rec
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context


def _parse_article(elem):
    pmid_el = elem.find(".//MedlineCitation/PMID")
    if pmid_el is None or not pmid_el.text:
        return None
    art = elem.find(".//MedlineCitation/Article")
    if art is None:
        return None

    title = _text(art.find("ArticleTitle"))

    # Abstract: concatenate all (possibly labeled) sections.
    parts = []
    for ab in art.findall(".//Abstract/AbstractText"):
        txt = _text(ab)
        if not txt:
            continue
        label = ab.get("Label")
        parts.append(f"{label}: {txt}" if label else txt)
    abstract = " ".join(parts)

    journal = _text(art.find(".//Journal/Title"))
    year_el = art.find(".//Journal/JournalIssue/PubDate/Year")
    year = int(year_el.text) if (year_el is not None and year_el.text
                                 and year_el.text.isdigit()) else None

    mesh = [_text(m.find("DescriptorName"))
            for m in elem.findall(".//MeshHeadingList/MeshHeading")]
    mesh = [m for m in mesh if m]

    pubtypes = [_text(p) for p in art.findall(".//PublicationTypeList/PublicationType")]
    retracted = 1 if any("Retract" in p for p in pubtypes) else 0

    return {
        "pmid": int(pmid_el.text),
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "year": year,
        "mesh": "; ".join(mesh),
        "pubtypes": "; ".join(pubtypes),
        "retracted": retracted,
    }
