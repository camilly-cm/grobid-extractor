"""Turn GROBID TEI responses into JSON-ready dicts and Markdown, per endpoint."""

from __future__ import annotations

import io
import logging
from typing import Any

from grobid_client.format.TEI2LossyJSON import TEI2LossyJSONConverter
from grobid_client.format.TEI2Markdown import TEI2MarkdownConverter

from .endpoints import GrobidEndpoint
from .tei import parse_bibl_structs, parse_header

logger = logging.getLogger(__name__)


def tei_to_dict(tei: str, endpoint: GrobidEndpoint) -> dict[str, Any]:
    """Structured representation of a TEI response.

    * ``FULLTEXT``: grobid-client's lossy JSON (``biblio``, ``body_text``,
      ``figures_and_tables``, ``references``).
    * ``HEADER``: title, authors, affiliations, abstract, keywords, identifiers.
    * ``REFERENCES`` / ``CITATION`` / ``CITATION_LIST``: ``{"references": [...]}``.
    """
    if endpoint is GrobidEndpoint.FULLTEXT:
        document = TEI2LossyJSONConverter().convert_tei_file(io.BytesIO(tei.encode("utf-8")))
        if document is None:
            raise ValueError("TEI could not be converted to JSON (empty or malformed)")
        return document
    if endpoint is GrobidEndpoint.HEADER:
        return {"biblio": parse_header(tei)}
    return {"references": parse_bibl_structs(tei)}


def tei_to_markdown(tei: str, endpoint: GrobidEndpoint) -> str:
    """Human-readable Markdown for a TEI response."""
    if endpoint in (GrobidEndpoint.FULLTEXT, GrobidEndpoint.HEADER):
        markdown = TEI2MarkdownConverter().convert_tei_file(io.BytesIO(tei.encode("utf-8")))
        if markdown is None:
            raise ValueError("TEI could not be converted to Markdown")
        return markdown
    return references_to_markdown(parse_bibl_structs(tei))


def references_to_markdown(references: list[dict[str, Any]]) -> str:
    lines = ["# References", ""]
    for number, ref in enumerate(references, 1):
        parts = [", ".join(ref.get("authors", [])), ref.get("title", ""), ref.get("venue", "")]
        if ref.get("year"):
            parts.append(ref["year"])
        text = ". ".join(p for p in parts if p)
        doi = ref.get("identifiers", {}).get("doi")
        if doi:
            text += f". DOI: {doi}"
        lines.append(f"{number}. {text}")
    return "\n".join(lines) + "\n"
