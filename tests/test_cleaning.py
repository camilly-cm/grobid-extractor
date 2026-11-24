from grobid_extractor import GrobidEndpoint, clean_document, to_plain_text
from grobid_extractor.converters import tei_to_dict

DOC = {
    "level": "paragraph",
    "biblio": {"title": "T", "abstract": [{"id": 0, "text": " A  b ", "coords": [], "refs": []}]},
    "body_text": [
        {"id": "p1", "text": "First\n para", "coords": [1], "refs": [2], "head_section": "Intro"},
        {"id": "p2", "text": "   ", "head_section": "Intro"},
        {"id": "p3", "text": "Second", "head_section": "Methods"},
    ],
    "figures_and_tables": [{"id": "f1"}],
    "references": [{"id": "b0"}],
}


def test_clean_document_drops_non_narrative():
    cleaned = clean_document(DOC)
    assert "references" not in cleaned
    assert "figures_and_tables" not in cleaned
    assert [p["id"] for p in cleaned["body_text"]] == ["p1", "p3"]
    assert cleaned["body_text"][0] == {"id": "p1", "text": "First para", "head_section": "Intro"}
    assert cleaned["biblio"]["abstract"] == [{"id": 0, "text": "A b"}]
    assert "references" in DOC  # input is not modified


def test_to_plain_text():
    text = to_plain_text(clean_document(DOC))
    assert text == "T\n\nAbstract\nA b\n\nIntro\n\nFirst para\n\nMethods\n\nSecond\n"


def test_fulltext_conversion_round_trip(fulltext_tei):
    document = tei_to_dict(fulltext_tei, GrobidEndpoint.FULLTEXT)
    text = to_plain_text(clean_document(document))
    assert "Blowflies colonize carcasses" in text
    assert "Methods" in text
