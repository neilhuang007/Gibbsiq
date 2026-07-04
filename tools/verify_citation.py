"""Resolve a citation to canonical metadata via authoritative APIs.

Citation metadata in the reference pack must come from a resolvable identifier,
not from a re-typed or OCR'd bibliography. This tool takes a DOI or an arXiv id
and returns the canonical record, plus a BibTeX entry, so the ``.bib`` file and
every per-paper header are generated from the same verified source.

* DOIs are resolved through the Crossref REST API
  (``https://api.crossref.org/works/<doi>``), which returns structured authors,
  title, container, volume/issue/page, and date.
* arXiv ids are resolved through the arXiv Atom API
  (``http://export.arxiv.org/api/query?id_list=<id>``); if the record carries a
  published DOI, that DOI is resolved through Crossref as well so the final
  citation prefers the version of record.

Usage:
    python tools/verify_citation.py --doi 10.1063/1.5055860 --key camsari2019pbits
    python tools/verify_citation.py --arxiv 1809.04028 --key camsari2019pbits
    python tools/verify_citation.py --arxiv 2510.23972          # key auto-derived

Output is JSON on stdout: the normalized record and a ``bibtex`` string.
Requires network access.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CROSSREF = "https://api.crossref.org/works/"
DATACITE = "https://api.datacite.org/dois/"
ARXIV = "https://export.arxiv.org/api/query?id_list="
UA = "Gibbsiq-refcheck/1.0 (mailto:neilhuang007@gmail.com)"
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _get(url: str, attempts: int = 4) -> bytes:
    """Fetch ``url`` with polite retry on rate limits and transient timeouts.

    arXiv returns HTTP 429 and asks callers to wait a few seconds between
    requests; Crossref is occasionally slow. Back off and retry rather than
    failing the whole verification run on a transient hiccup.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read()
        except (urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            transient = isinstance(exc, (TimeoutError, OSError)) or (
                isinstance(exc, urllib.error.HTTPError) and exc.code in (429, 500, 503)
            )
            if not transient or attempt == attempts - 1:
                raise
            time.sleep(3 * (attempt + 1))
    raise last  # pragma: no cover


def _clean_title(title: str | None) -> str | None:
    """Strip embedded JATS/MathML/HTML markup Crossref sometimes returns.

    Crossref stores some titles with inline ``<mml:math>`` or ``<i>`` markup
    (e.g. PRX renders the ``p`` in "Stochastic p-Bits" as MathML). Drop the
    tags and collapse the resulting whitespace so the BibTeX title is plain
    text.
    """
    if not title:
        return title
    text = re.sub(r"<[^>]+>", "", title)
    return " ".join(text.split())


def resolve_doi(doi: str) -> dict:
    """Return a normalized record from Crossref for ``doi``."""
    data = json.loads(_get(CROSSREF + urllib.parse.quote(doi)))["message"]
    authors = [" ".join(p for p in (a.get("given"), a.get("family")) if p) for a in data.get("author", [])]
    date = (data.get("issued") or data.get("published") or {}).get("date-parts", [[None]])
    container = (data.get("container-title") or [None])[0]
    return {
        "source": "crossref",
        "doi": data.get("DOI"),
        "title": _clean_title((data.get("title") or [None])[0]),
        "authors": authors,
        "container": container,
        "volume": data.get("volume"),
        "issue": data.get("issue"),
        "page": data.get("page") or data.get("article-number"),
        "year": date[0][0] if date and date[0] else None,
        "type": data.get("type"),
    }


def _published_doi(attrs: dict) -> str | None:
    """Return a non-arXiv DOI that this preprint is a version of, if any."""
    for rel in attrs.get("relatedIdentifiers", []):
        if rel.get("relatedIdentifierType") != "DOI":
            continue
        if rel.get("relationType") not in {"IsVersionOf", "IsIdenticalTo", "IsPublishedIn"}:
            continue
        doi = (rel.get("relatedIdentifier") or "").lower()
        if doi and "arxiv" not in doi:
            return rel["relatedIdentifier"]
    return None


def resolve_arxiv(arxiv_id: str) -> dict:
    """Return a normalized record for ``arxiv_id`` via DataCite.

    arXiv mints a DataCite DOI (``10.48550/arXiv.<id>``) for every paper, and
    the DataCite API is reliable where the arXiv Atom API rate-limits
    aggressively. If DataCite records a published version of record, that DOI is
    resolved through Crossref instead, so the citation prefers the journal
    version. The arXiv Atom API is used only as a last-resort fallback.
    """
    try:
        attrs = json.loads(_get(DATACITE + urllib.parse.quote(f"10.48550/arXiv.{arxiv_id}")))["data"][
            "attributes"
        ]
    except Exception:  # noqa: BLE001 -- fall back to the Atom API below
        return _resolve_arxiv_atom(arxiv_id)

    published = _published_doi(attrs)
    if published:
        record = resolve_doi(published)
        record["arxiv"] = arxiv_id
        return record

    authors = [c.get("name") for c in attrs.get("creators", []) if c.get("name")]
    return {
        "source": "datacite",
        "doi": None,
        "arxiv": arxiv_id,
        "title": _clean_title((attrs.get("titles") or [{}])[0].get("title")),
        "authors": authors,
        "container": "arXiv preprint",
        "volume": None,
        "issue": None,
        "page": None,
        "year": attrs.get("publicationYear"),
        "type": "preprint",
    }


def _resolve_arxiv_atom(arxiv_id: str) -> dict:
    """Fallback: normalize a record from the arXiv Atom API."""
    root = ET.fromstring(_get(ARXIV + urllib.parse.quote(arxiv_id)))
    entry = root.find("a:entry", ATOM)
    if entry is None:
        raise RuntimeError(f"no arXiv entry for {arxiv_id}")
    doi_el = entry.find("arxiv:doi", ATOM)
    if doi_el is not None and doi_el.text:
        record = resolve_doi(doi_el.text.strip())
        record["arxiv"] = arxiv_id
        return record
    title = entry.find("a:title", ATOM)
    published = entry.find("a:published", ATOM)
    authors = [
        n.text.strip()
        for a in entry.findall("a:author", ATOM)
        if (n := a.find("a:name", ATOM)) is not None and n.text
    ]
    year = int(published.text[:4]) if published is not None and published.text else None
    return {
        "source": "arxiv",
        "doi": None,
        "arxiv": arxiv_id,
        "title": " ".join(title.text.split()) if title is not None and title.text else None,
        "authors": authors,
        "container": "arXiv preprint",
        "volume": None,
        "issue": None,
        "page": None,
        "year": year,
        "type": "preprint",
    }


def _surname(authors: list[str]) -> str:
    """Derive an ASCII surname slug from the first author for a BibTeX key.

    Crossref returns ``"Given Family"`` (surname last); DataCite returns
    ``"Family, Given"`` (surname first). Normalize both, then fold accents to
    ASCII so the key is portable (``Jelinčič`` -> ``jelincic``).
    """
    if not authors:
        return "ref"
    name = authors[0]
    surname = name.split(",")[0] if "," in name else name.split()[-1]
    folded = unicodedata.normalize("NFKD", surname)
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    return "".join(c for c in ascii_only if c.isalnum()).lower() or "ref"


def to_bibtex(record: dict, key: str) -> str:
    """Render a normalized record as a BibTeX entry."""
    is_preprint = record.get("type") == "preprint" or not record.get("doi")
    entry_type = "misc" if is_preprint else "article"
    fields = {
        "author": " and ".join(record["authors"]),
        "title": "{" + (record["title"] or "") + "}",
        "year": record.get("year"),
    }
    if is_preprint:
        fields["howpublished"] = f"arXiv:{record.get('arxiv')}"
        fields["eprint"] = record.get("arxiv")
        fields["archivePrefix"] = "arXiv"
    else:
        fields["journal"] = record.get("container")
        fields["volume"] = record.get("volume")
        fields["number"] = record.get("issue")
        fields["pages"] = record.get("page")
        fields["doi"] = record.get("doi")
        if record.get("arxiv"):
            fields["eprint"] = record.get("arxiv")
            fields["archivePrefix"] = "arXiv"
    lines = [f"@{entry_type}{{{key},"]
    for name, value in fields.items():
        if value:
            lines.append(f"  {name} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doi")
    group.add_argument("--arxiv")
    parser.add_argument("--key", default=None, help="BibTeX key (default: derived)")
    args = parser.parse_args(argv)

    record = resolve_doi(args.doi) if args.doi else resolve_arxiv(args.arxiv)
    key = args.key
    if key is None:
        key = f"{_surname(record['authors'])}{record.get('year') or ''}"
    record["bibtex"] = to_bibtex(record, key)
    record["bibtex_key"] = key
    # Force UTF-8 on stdout: author names carry non-ASCII (e.g. "Jelinčič")
    # that a Windows GBK console cannot encode.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    json.dump(record, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
