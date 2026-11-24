import pytest

from grobid_extractor import GrobidEndpoint, InputKind


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("fulltext", GrobidEndpoint.FULLTEXT),
        ("FULLTEXT", GrobidEndpoint.FULLTEXT),
        ("citation-list", GrobidEndpoint.CITATION_LIST),
        ("processHeaderDocument", GrobidEndpoint.HEADER),
    ],
)
def test_from_name(name, expected):
    assert GrobidEndpoint.from_name(name) is expected


def test_from_name_unknown():
    with pytest.raises(ValueError, match="Unknown GROBID endpoint"):
        GrobidEndpoint.from_name("nope")


def test_input_kind_and_path():
    assert GrobidEndpoint.REFERENCES.input_kind is InputKind.PDF
    assert GrobidEndpoint.CITATION.input_kind is InputKind.CITATIONS
    assert GrobidEndpoint.FULLTEXT.path == "/api/processFulltextDocument"


def test_cli_choices_round_trip():
    for choice in GrobidEndpoint.cli_choices():
        GrobidEndpoint.from_name(choice)
