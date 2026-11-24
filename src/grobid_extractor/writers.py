"""Write extraction results to disk."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from .cleaning import clean_document, to_plain_text
from .converters import tei_to_dict, tei_to_markdown
from .endpoints import GrobidEndpoint


class OutputFormat(str, Enum):
    TEI = "tei"  # raw GROBID response (.tei.xml) - always the source of truth
    JSON = "json"  # structured JSON (.json)
    CLEAN = "clean"  # narrative-only JSON (.clean.json) - FULLTEXT only
    MARKDOWN = "md"  # readable Markdown (.md)
    TEXT = "txt"  # plain narrative text (.txt) - FULLTEXT only


SUFFIXES = {
    OutputFormat.TEI: ".tei.xml",
    OutputFormat.JSON: ".json",
    OutputFormat.CLEAN: ".clean.json",
    OutputFormat.MARKDOWN: ".md",
    OutputFormat.TEXT: ".txt",
}

FULLTEXT_ONLY = {OutputFormat.CLEAN, OutputFormat.TEXT}


def output_path(output_dir: Path, stem: str, fmt: OutputFormat) -> Path:
    return output_dir / f"{stem}{SUFFIXES[fmt]}"


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_outputs(
    tei: str,
    endpoint: GrobidEndpoint,
    output_dir: Path,
    stem: str,
    formats: set[OutputFormat],
) -> list[Path]:
    """Write every requested format for one TEI response. Returns the files written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def emit(fmt: OutputFormat, content: str) -> None:
        path = output_path(output_dir, stem, fmt)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    if OutputFormat.TEI in formats:
        emit(OutputFormat.TEI, tei)

    needs_dict = formats & {OutputFormat.JSON, OutputFormat.CLEAN, OutputFormat.TEXT}
    if needs_dict:
        document = tei_to_dict(tei, endpoint)
        if OutputFormat.JSON in formats:
            emit(OutputFormat.JSON, json.dumps(document, ensure_ascii=False, indent=2))
        if endpoint is GrobidEndpoint.FULLTEXT:
            cleaned = clean_document(document)
            if OutputFormat.CLEAN in formats:
                emit(OutputFormat.CLEAN, json.dumps(cleaned, ensure_ascii=False, indent=2))
            if OutputFormat.TEXT in formats:
                emit(OutputFormat.TEXT, to_plain_text(cleaned))

    if OutputFormat.MARKDOWN in formats:
        emit(OutputFormat.MARKDOWN, tei_to_markdown(tei, endpoint))
    return written
