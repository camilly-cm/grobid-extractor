"""Scientific text extraction from PDFs using a GROBID server."""

from .cleaning import clean_document, to_plain_text
from .client import GrobidClient, GrobidError, GrobidNoContentError, GrobidUnavailableError
from .config import RequestOptions, Settings
from .endpoints import GrobidEndpoint, InputKind
from .pipeline import BatchReport, process_citations, process_pdfs
from .writers import OutputFormat

__all__ = [
    "BatchReport",
    "GrobidClient",
    "GrobidEndpoint",
    "GrobidError",
    "GrobidNoContentError",
    "GrobidUnavailableError",
    "InputKind",
    "OutputFormat",
    "RequestOptions",
    "Settings",
    "clean_document",
    "process_citations",
    "process_pdfs",
    "to_plain_text",
]

__version__ = "0.1.0"
