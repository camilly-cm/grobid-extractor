from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fulltext_tei() -> str:
    return (FIXTURES / "fulltext.tei.xml").read_text(encoding="utf-8")


@pytest.fixture
def citation_tei() -> str:
    return (FIXTURES / "citation.tei.xml").read_text(encoding="utf-8")
