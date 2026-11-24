"""Reduce GROBID full-text JSON to its narrative content."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

NON_NARRATIVE_KEYS: tuple[str, ...] = ("references", "figures_and_tables")
"""Top-level keys of the full-text JSON that carry no narrative text."""

PASSAGE_NOISE_KEYS: tuple[str, ...] = ("coords", "refs")
"""Per-passage keys (layout coordinates and citation offsets) dropped when cleaning."""

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _clean_passages(passages: Iterable[dict[str, Any]],
                    drop_keys: Iterable[str]) -> list[dict[str, Any]]:
    cleaned = []
    for passage in passages:
        text = normalize_text(passage.get("text", ""))
        if not text:
            continue
        item = {k: v for k, v in passage.items() if k not in drop_keys}
        item["text"] = text
        cleaned.append(item)
    return cleaned


def clean_document(
    document: dict[str, Any],
    drop_keys: Iterable[str] = NON_NARRATIVE_KEYS,
    drop_passage_keys: Iterable[str] = PASSAGE_NOISE_KEYS,
) -> dict[str, Any]:
    """Return a copy of a full-text JSON document without non-narrative content.

    Removes the top-level ``drop_keys``, strips per-passage ``drop_passage_keys``,
    normalises whitespace and discards empty passages. The input is not modified.
    """
    drop_keys = set(drop_keys)
    drop_passage_keys = set(drop_passage_keys)
    cleaned = {k: v for k, v in document.items() if k not in drop_keys}

    biblio = dict(cleaned.get("biblio") or {})
    if isinstance(biblio.get("abstract"), list):
        biblio["abstract"] = _clean_passages(biblio["abstract"], drop_passage_keys)
    if biblio:
        cleaned["biblio"] = biblio

    if isinstance(cleaned.get("body_text"), list):
        cleaned["body_text"] = _clean_passages(cleaned["body_text"], drop_passage_keys)
    return cleaned


def to_plain_text(document: dict[str, Any]) -> str:
    """Flatten a full-text JSON document into plain text: title, abstract, then sections."""
    biblio = document.get("biblio") or {}
    blocks: list[str] = []
    if biblio.get("title"):
        blocks.append(normalize_text(biblio["title"]))

    abstract = biblio.get("abstract")
    if isinstance(abstract, list):
        abstract = " ".join(p.get("text", "") for p in abstract)
    if abstract:
        blocks.append("Abstract\n" + normalize_text(abstract))

    current_section = None
    for passage in document.get("body_text") or []:
        text = normalize_text(passage.get("text", ""))
        if not text:
            continue
        section = passage.get("head_section")
        if section and section != current_section:
            blocks.append(normalize_text(section))
            current_section = section
        blocks.append(text)
    return "\n\n".join(blocks) + "\n"
