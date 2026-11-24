"""GROBID REST endpoints supported by this project.

Pick one of these explicitly when calling the client, the pipeline or the CLI::

    ENDPOINT = GrobidEndpoint.FULLTEXT
"""

from __future__ import annotations

from enum import Enum


class InputKind(str, Enum):
    """What an endpoint expects in the request body."""

    PDF = "pdf"  # multipart field ``input`` with a PDF file
    CITATIONS = "citations"  # form field ``citations`` with raw reference strings


class GrobidEndpoint(str, Enum):
    """The main GROBID services (all are ``POST /api/<value>``)."""

    HEADER = "processHeaderDocument"
    """PDF -> title, authors, affiliations, abstract, keywords and identifiers."""

    FULLTEXT = "processFulltextDocument"
    """PDF -> header, body structure, figures, tables and parsed references."""

    REFERENCES = "processReferences"
    """PDF -> only the parsed bibliography."""

    CITATION = "processCitation"
    """One raw reference string -> that reference parsed into fields."""

    CITATION_LIST = "processCitationList"
    """Several raw reference strings -> each one parsed."""

    @property
    def input_kind(self) -> InputKind:
        if self in (GrobidEndpoint.CITATION, GrobidEndpoint.CITATION_LIST):
            return InputKind.CITATIONS
        return InputKind.PDF

    @property
    def path(self) -> str:
        return f"/api/{self.value}"

    @classmethod
    def from_name(cls, name: str) -> GrobidEndpoint:
        """Resolve a user-friendly name.

        Accepts the enum name (``fulltext``, ``citation_list``, case-insensitive,
        ``-`` or ``_``) or the raw GROBID service name (``processFulltextDocument``).
        """
        key = name.strip()
        for member in cls:
            if key == member.value:
                return member
        normalized = key.upper().replace("-", "_")
        try:
            return cls[normalized]
        except KeyError:
            choices = ", ".join(cls.cli_choices())
            raise ValueError(
                f"Unknown GROBID endpoint {name!r}. Choose one of: {choices}"
            ) from None

    @classmethod
    def cli_choices(cls) -> list[str]:
        return [m.name.lower().replace("_", "-") for m in cls]
