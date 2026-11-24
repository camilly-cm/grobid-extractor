"""Thin HTTP client for the GROBID REST API."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Sequence
from pathlib import Path

import requests

from .config import RequestOptions, Settings
from .endpoints import GrobidEndpoint, InputKind

logger = logging.getLogger(__name__)


class GrobidError(RuntimeError):
    """A request to GROBID failed."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GrobidUnavailableError(GrobidError):
    """The GROBID server could not be reached."""


class GrobidNoContentError(GrobidError):
    """GROBID answered 204: the request was valid but nothing was extracted
    (e.g. ``processReferences`` on a paper without a bibliography)."""


class GrobidClient:
    """Sends PDFs or raw citations to a GROBID server and returns TEI XML.

    Example::

        client = GrobidClient(Settings.from_env())
        tei = client.process_pdf("paper.pdf", GrobidEndpoint.FULLTEXT)
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        # requests.Session is not guaranteed thread-safe: keep one per thread.
        self._local = threading.local()

    # ------------------------------------------------------------------ health
    @property
    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
        return session

    def is_alive(self) -> bool:
        try:
            response = self._session.get(f"{self.settings.grobid_url}/api/isalive", timeout=5)
        except requests.RequestException:
            return False
        return response.ok and response.text.strip().lower() == "true"

    def version(self) -> str:
        response = self._session.get(f"{self.settings.grobid_url}/api/version", timeout=5)
        response.raise_for_status()
        return response.json().get("version", response.text)

    def ensure_alive(self) -> None:
        if not self.is_alive():
            raise GrobidUnavailableError(
                f"GROBID server is not reachable at {self.settings.grobid_url}. "
                "Start it with `docker compose up -d` and wait until it is healthy."
            )

    # ---------------------------------------------------------------- requests
    def process_pdf(
        self,
        pdf_path: str | Path,
        endpoint: GrobidEndpoint,
        options: RequestOptions | None = None,
    ) -> str:
        """Send one PDF to a PDF endpoint and return the TEI XML response."""
        if endpoint.input_kind is not InputKind.PDF:
            raise ValueError(f"{endpoint.name} expects citation strings, not a PDF.")
        pdf_path = Path(pdf_path)
        data = (options or self.settings.options).to_form_data()

        def send() -> requests.Response:
            with pdf_path.open("rb") as handle:
                files = {"input": (pdf_path.name, handle, "application/pdf")}
                return self._session.post(
                    self.settings.grobid_url + endpoint.path,
                    files=files,
                    data=data,
                    headers={"Accept": "application/xml"},
                    timeout=self.settings.timeout,
                )

        return self._request_with_retry(send, label=pdf_path.name)

    def process_citations(
        self,
        citations: str | Sequence[str],
        endpoint: GrobidEndpoint = GrobidEndpoint.CITATION_LIST,
        options: RequestOptions | None = None,
    ) -> str:
        """Send raw reference string(s) to a citation endpoint and return TEI XML.

        ``CITATION`` accepts exactly one string; ``CITATION_LIST`` accepts many.
        """
        if endpoint.input_kind is not InputKind.CITATIONS:
            raise ValueError(f"{endpoint.name} expects a PDF, not citation strings.")
        items = [citations] if isinstance(citations, str) else list(citations)
        items = [c.strip() for c in items if c and c.strip()]
        if not items:
            raise ValueError("No citation strings given.")
        if endpoint is GrobidEndpoint.CITATION and len(items) != 1:
            raise ValueError("CITATION takes a single string; use CITATION_LIST for several.")

        opts = options or self.settings.options
        data = [(key, value) for key, value in opts.to_form_data()
                if key in ("consolidateCitations", "includeRawCitations")]
        data.extend(("citations", item) for item in items)

        def send() -> requests.Response:
            return self._session.post(
                self.settings.grobid_url + endpoint.path,
                data=data,
                headers={"Accept": "application/xml"},
                timeout=self.settings.timeout,
            )

        return self._request_with_retry(send, label=f"{len(items)} citation(s)")

    def _request_with_retry(self, send, label: str) -> str:
        attempts = self.settings.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = send()
            except requests.ConnectionError as exc:
                raise GrobidUnavailableError(
                    f"Cannot connect to GROBID at {self.settings.grobid_url}: {exc}"
                ) from exc
            except requests.Timeout as exc:
                raise GrobidError(f"Timeout after {self.settings.timeout}s for {label}") from exc

            if response.status_code == 503 and attempt < attempts:
                logger.info("GROBID busy (503) for %s, retry %d/%d", label, attempt,
                            self.settings.max_retries)
                time.sleep(self.settings.retry_wait)
                continue
            if response.status_code == 204:
                raise GrobidNoContentError(f"GROBID extracted no content from {label}", 204)
            if not response.ok:
                detail = response.text.strip()[:300] or response.reason
                raise GrobidError(f"HTTP {response.status_code} for {label}: {detail}",
                                  response.status_code)
            response.encoding = "utf-8"
            return response.text
        raise GrobidError(f"GROBID still busy after {self.settings.max_retries} retries", 503)
