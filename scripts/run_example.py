"""Minimal example: process the PDFs folder with an explicitly chosen GROBID endpoint.

Run from the repository root (with the venv active and GROBID running):

    python scripts/run_example.py
"""

from pathlib import Path

from grobid_extractor import GrobidClient, GrobidEndpoint, OutputFormat, Settings, process_pdfs

# --------------------------------------------------------------------------- #
# Choose the GROBID service here:
#   GrobidEndpoint.HEADER      -> title, authors, affiliations, abstract, keywords
#   GrobidEndpoint.FULLTEXT    -> header + body sections + figures/tables + references
#   GrobidEndpoint.REFERENCES  -> only the parsed bibliography
#   (CITATION / CITATION_LIST take raw strings: see process_citations())
ENDPOINT = GrobidEndpoint.FULLTEXT
# --------------------------------------------------------------------------- #

INPUT_DIR = Path("PDFS")
OUTPUT_DIR = Path("output")
FORMATS = {OutputFormat.TEI, OutputFormat.JSON, OutputFormat.CLEAN, OutputFormat.TEXT}


def main() -> None:
    client = GrobidClient(Settings.from_env())
    print(f"GROBID {client.version()} at {client.settings.grobid_url}")
    report = process_pdfs(
        client,
        ENDPOINT,
        INPUT_DIR,
        OUTPUT_DIR,
        formats=FORMATS,
        on_progress=lambda r: print(f"{r.status:>7}  {Path(r.source).name}"),
    )
    print(report.summary())


if __name__ == "__main__":
    main()
