"""Batch processing: send a folder of PDFs to one GROBID endpoint and save the results."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .client import GrobidClient, GrobidError, GrobidNoContentError, GrobidUnavailableError
from .config import RequestOptions
from .endpoints import GrobidEndpoint, InputKind
from .tei import parse_bibl_structs
from .writers import FULLTEXT_ONLY, OutputFormat, output_path, write_json, write_outputs

logger = logging.getLogger(__name__)

DEFAULT_FORMATS = frozenset({OutputFormat.TEI, OutputFormat.JSON, OutputFormat.MARKDOWN})
ERRORS_FILE = "_errors.json"


@dataclass
class FileResult:
    source: str
    status: str  # "ok" | "empty" | "skipped" | "error"
    outputs: list[str] = field(default_factory=list)
    error: str | None = None
    status_code: int | None = None


@dataclass
class BatchReport:
    endpoint: str
    output_dir: str
    results: list[FileResult] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def errors(self) -> list[FileResult]:
        return [r for r in self.results if r.status == "error"]

    def summary(self) -> str:
        return (f"{self.endpoint}: {self.count('ok')} ok, {self.count('empty')} empty, "
                f"{self.count('skipped')} skipped, {self.count('error')} error(s) "
                f"-> {self.output_dir}")


def find_pdfs(input_path: Path, recursive: bool = False) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    pattern = "**/*" if recursive else "*"
    return sorted(p for p in input_path.glob(pattern)
                  if p.is_file() and p.suffix.lower() == ".pdf")


def resolve_formats(endpoint: GrobidEndpoint, formats: Iterable[OutputFormat]) -> set[OutputFormat]:
    selected = set(formats)
    if endpoint is not GrobidEndpoint.FULLTEXT:
        dropped = selected & FULLTEXT_ONLY
        if dropped:
            logger.warning("Formats %s only apply to FULLTEXT; ignoring them for %s.",
                           sorted(f.value for f in dropped), endpoint.name)
        selected -= FULLTEXT_ONLY
    return selected or {OutputFormat.TEI}


def process_pdfs(
    client: GrobidClient,
    endpoint: GrobidEndpoint,
    input_path: str | Path,
    output_dir: str | Path,
    formats: Iterable[OutputFormat] = DEFAULT_FORMATS,
    options: RequestOptions | None = None,
    overwrite: bool = False,
    recursive: bool = False,
    concurrency: int | None = None,
    on_progress: Callable[[FileResult], None] | None = None,
) -> BatchReport:
    """Process every PDF under ``input_path`` with ``endpoint``.

    Results go to ``output_dir/<endpoint>/``. Failures (e.g. scanned PDFs without a
    text layer) do not stop the batch; they are listed in ``_errors.json``.
    """
    if endpoint.input_kind is not InputKind.PDF:
        raise ValueError(f"{endpoint.name} takes citation strings; use process_citations().")

    input_path, output_dir = Path(input_path), Path(output_dir) / endpoint.name.lower()
    pdfs = find_pdfs(input_path, recursive)
    if not pdfs:
        raise FileNotFoundError(f"No PDF found in {input_path}")
    selected = resolve_formats(endpoint, formats)
    client.ensure_alive()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = BatchReport(endpoint=endpoint.value, output_dir=str(output_dir))

    def handle(pdf: Path) -> FileResult:
        stem = pdf.stem
        expected = [output_path(output_dir, stem, f) for f in selected]
        if not overwrite and all(p.exists() for p in expected):
            return FileResult(str(pdf), "skipped", [str(p) for p in expected])
        try:
            tei = client.process_pdf(pdf, endpoint, options)
            written = write_outputs(tei, endpoint, output_dir, stem, selected)
            return FileResult(str(pdf), "ok", [str(p) for p in written])
        except GrobidUnavailableError:
            raise
        except GrobidNoContentError as exc:
            return FileResult(str(pdf), "empty", error=str(exc), status_code=exc.status_code)
        except GrobidError as exc:
            return FileResult(str(pdf), "error", error=str(exc), status_code=exc.status_code)
        except Exception as exc:  # conversion bugs must not kill the batch
            logger.exception("Unexpected failure on %s", pdf.name)
            return FileResult(str(pdf), "error", error=f"{type(exc).__name__}: {exc}")

    workers = max(1, concurrency or client.settings.concurrency)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(handle, pdf): pdf for pdf in pdfs}
        for future in as_completed(futures):
            result = future.result()
            report.results.append(result)
            if on_progress:
                on_progress(result)

    report.results.sort(key=lambda r: r.source)
    _write_error_report(output_dir, report)
    return report


def _write_error_report(output_dir: Path, report: BatchReport) -> None:
    path = output_dir / ERRORS_FILE
    if not report.errors:
        path.unlink(missing_ok=True)
        return
    write_json(path, {
        "endpoint": report.endpoint,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "errors": [asdict(r) for r in report.errors],
    })


def process_citations(
    client: GrobidClient,
    citations: Sequence[str],
    output_file: str | Path | None = None,
    endpoint: GrobidEndpoint = GrobidEndpoint.CITATION_LIST,
    options: RequestOptions | None = None,
) -> list[dict]:
    """Parse raw reference strings. Optionally save the parsed list as JSON."""
    if endpoint is GrobidEndpoint.CITATION:
        parsed = [parse_bibl_structs(client.process_citations(c, endpoint, options))[0]
                  for c in citations]
    else:
        parsed = parse_bibl_structs(client.process_citations(citations, endpoint, options))
    if output_file:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        write_json(output_file, {"endpoint": endpoint.value, "references": parsed})
    return parsed


def load_citations(path: str | Path) -> list[str]:
    """Read one raw reference per non-empty line (or a JSON list of strings)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return [str(c) for c in json.loads(text)]
    return [line.strip() for line in text.splitlines() if line.strip()]
