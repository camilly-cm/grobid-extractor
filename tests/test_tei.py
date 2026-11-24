from grobid_extractor.tei import parse_bibl_structs, parse_header


def test_parse_header(fulltext_tei):
    header = parse_header(fulltext_tei)
    assert header["title"] == "Synthetic study of blowflies in the Caatinga"
    assert header["authors"] == ["Ana Souza", "João Lima"]
    assert header["affiliations"] == ["Universidade Federal da Paraíba"]
    assert header["keywords"] == ["Calliphoridae", "forensic entomology"]
    assert header["abstract"] == "We describe blowflies collected in a semi-arid area."
    assert header["identifiers"]["doi"] == "10.1234/example.2014"
    assert header["year"] == "2014"


def test_references_skip_document_header(fulltext_tei):
    refs = parse_bibl_structs(fulltext_tei)
    assert len(refs) == 1
    ref = refs[0]
    assert ref["id"] == "b0"
    assert ref["title"] == "Flies and decomposition"
    assert ref["venue"] == "Journal of Flies"
    assert ref["pages"] == "1-10"
    assert ref["volume"] == "12"


def test_single_citation(citation_tei):
    (ref,) = parse_bibl_structs(citation_tei)
    assert ref["authors"] == ["A F Amarante"]
    assert ref["year"] == "1992"
    assert ref["identifiers"]["doi"].startswith("10.1016")
