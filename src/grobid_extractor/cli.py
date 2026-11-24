"""Command-line interface: ``grobid-extract --endpoint <name> ...``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .client import GrobidClient, GrobidError
from .config import RequestOptions, Settings
from .endpoints import GrobidEndpoint, InputKind
from .pipeline import (
    DEFAULT_FORMATS,
    FileResult,
    load_citations,
    process_citations,
    process_pdfs,
)
from .writers import OutputFormat

EXAMPLES = """
examples:
  grobid-extract --endpoint fulltext   --input PDFS --format json clean txt md
  grobid-extract --endpoint header     --input PDFS/paper.pdf
  grobid-extract --endpoint references --input PDFS --overwrite
  grobid-extract --endpoint citation   --citation "Smith J. 2020. A title. Nature 1:2-3."
  grobid-extract --endpoint citation-list --citations-file refs.txt
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grobid-extract",
        description="Extract structured text from scientific PDFs with GROBID.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--endpoint", "-e", required=True, choices=GrobidEndpoint.cli_choices(),
                        help="GROBID service to call")

    source = parser.add_argument_group("input (PDF endpoints)")
    source.add_argument("--input", "-i", type=Path, help="PDF file or folder of PDFs")
    source.add_argument("--recursive", "-r", action="store_true", help="search subfolders")

    cites = parser.add_argument_group("input (citation endpoints)")
    cites.add_argument("--citation", action="append", default=[],
                       help="raw reference string (repeatable)")
    cites.add_argument("--citations-file", type=Path,
                       help="text file with one reference per line, or a JSON list")

    out = parser.add_argument_group("output")
    out.add_argument("--output", "-o", type=Path, default=Path("output"),
                     help="output folder (default: ./output)")
    out.add_argument("--format", "-f", nargs="+", choices=[f.value for f in OutputFormat],
                     default=[f.value for f in DEFAULT_FORMATS],
                     help="formats to write (default: tei json md); clean/txt are FULLTEXT only")
    out.add_argument("--overwrite", action="store_true", help="reprocess existing results")

    grobid = parser.add_argument_group("GROBID options")
    grobid.add_argument("--url", help="GROBID server URL (default: $GROBID_URL or localhost:8070)")
    grobid.add_argument("--concurrency", "-c", type=int, help="parallel requests")
    grobid.add_argument("--consolidate-header", type=int, choices=[0, 1, 2], default=0)
    grobid.add_argument("--consolidate-citations", type=int, choices=[0, 1, 2], default=0)
    grobid.add_argument("--include-raw-citations", action="store_true")
    grobid.add_argument("--segment-sentences", action="store_true")

    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def _print_progress(result: FileResult) -> None:
    mark = {"ok": "OK  ", "empty": "NONE", "skipped": "SKIP", "error": "FAIL"}[result.status]
    line = f"[{mark}] {Path(result.source).name}"
    if result.error:
        line += f"  ->  {result.error[:120]}"
    print(line, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    # Windows consoles default to cp1252; titles often contain accents.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    endpoint = GrobidEndpoint.from_name(args.endpoint)
    env = Settings.from_env()
    options = RequestOptions(
        consolidate_header=args.consolidate_header,
        consolidate_citations=args.consolidate_citations,
        include_raw_citations=args.include_raw_citations,
        segment_sentences=args.segment_sentences,
    )
    settings = Settings(
        grobid_url=(args.url or env.grobid_url).rstrip("/"),
        timeout=env.timeout,
        concurrency=args.concurrency or env.concurrency,
        max_retries=env.max_retries,
        retry_wait=env.retry_wait,
        options=options,
    )
    client = GrobidClient(settings)

    try:
        if endpoint.input_kind is InputKind.PDF:
            if not args.input:
                parser.error(f"--input is required for {args.endpoint}")
            report = process_pdfs(
                client, endpoint, args.input, args.output,
                formats=[OutputFormat(f) for f in args.format],
                overwrite=args.overwrite, recursive=args.recursive,
                on_progress=_print_progress,
            )
            print(report.summary())
            return 1 if report.errors and not report.count("ok") else 0

        citations = list(args.citation)
        if args.citations_file:
            citations += load_citations(args.citations_file)
        if not citations:
            parser.error(f"--citation or --citations-file is required for {args.endpoint}")
        client.ensure_alive()
        out_file = args.output / endpoint.name.lower() / "citations.json"
        parsed = process_citations(client, citations, out_file, endpoint)
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        print(f"Saved {len(parsed)} parsed reference(s) -> {out_file}", file=sys.stderr)
        return 0
    except (GrobidError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
