"""Runtime configuration, read from environment variables and an optional ``.env`` file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class RequestOptions:
    """Optional GROBID request parameters (sent only to endpoints that accept them).

    See https://grobid.readthedocs.io/en/latest/Grobid-service/ for details.
    """

    consolidate_header: int = 0
    """0 = none, 1 = full via CrossRef/biblio-glutton, 2 = DOI only. Needs network on the server."""

    consolidate_citations: int = 0
    include_raw_citations: bool = False
    include_raw_affiliations: bool = False
    segment_sentences: bool = False
    generate_ids: bool = False
    tei_coordinates: tuple[str, ...] = ()
    """TEI elements to annotate with PDF coordinates, e.g. ("figure", "ref", "biblStruct")."""

    def to_form_data(self) -> list[tuple[str, str]]:
        data: list[tuple[str, str]] = [
            ("consolidateHeader", str(self.consolidate_header)),
            ("consolidateCitations", str(self.consolidate_citations)),
            ("includeRawCitations", "1" if self.include_raw_citations else "0"),
            ("includeRawAffiliations", "1" if self.include_raw_affiliations else "0"),
            ("segmentSentences", "1" if self.segment_sentences else "0"),
            ("generateIDs", "1" if self.generate_ids else "0"),
        ]
        data.extend(("teiCoordinates", element) for element in self.tei_coordinates)
        return data


@dataclass(frozen=True)
class Settings:
    """Connection settings for the GROBID server."""

    grobid_url: str = "http://localhost:8070"
    timeout: float = 180.0
    concurrency: int = 4
    max_retries: int = 5
    retry_wait: float = 5.0
    options: RequestOptions = field(default_factory=RequestOptions)

    @classmethod
    def from_env(cls, dotenv: bool = True) -> Settings:
        """Build settings from ``GROBID_*`` environment variables (and ``.env`` if present)."""
        if dotenv:
            load_dotenv()
        defaults = cls()
        return cls(
            grobid_url=os.getenv("GROBID_URL", defaults.grobid_url).rstrip("/"),
            timeout=float(os.getenv("GROBID_TIMEOUT", defaults.timeout)),
            concurrency=int(os.getenv("GROBID_CONCURRENCY", defaults.concurrency)),
            max_retries=int(os.getenv("GROBID_MAX_RETRIES", defaults.max_retries)),
            retry_wait=float(os.getenv("GROBID_RETRY_WAIT", defaults.retry_wait)),
        )
