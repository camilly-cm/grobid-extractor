from unittest.mock import MagicMock

import pytest

from grobid_extractor import (
    GrobidClient,
    GrobidEndpoint,
    GrobidError,
    GrobidNoContentError,
    Settings,
)


def make_response(status=200, text="<TEI/>"):
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    response.text = text
    response.reason = "reason"
    return response


@pytest.fixture
def client(monkeypatch):
    grobid = GrobidClient(Settings(grobid_url="http://grobid:8070", retry_wait=0, max_retries=2))
    session = MagicMock()
    monkeypatch.setattr(GrobidClient, "_session", property(lambda self: session))
    return grobid, session


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "a.pdf"
    path.write_bytes(b"%PDF-1.4")
    return path


def test_process_pdf_posts_to_selected_endpoint(client, pdf):
    grobid, session = client
    session.post.return_value = make_response(text="<TEI>ok</TEI>")

    assert grobid.process_pdf(pdf, GrobidEndpoint.HEADER) == "<TEI>ok</TEI>"
    assert session.post.call_args.args[0] == "http://grobid:8070/api/processHeaderDocument"
    assert "input" in session.post.call_args.kwargs["files"]


def test_retries_on_503(client, pdf):
    grobid, session = client
    session.post.side_effect = [make_response(503), make_response(200, "<TEI/>")]
    assert grobid.process_pdf(pdf, GrobidEndpoint.FULLTEXT) == "<TEI/>"
    assert session.post.call_count == 2


def test_http_error_raises(client, pdf):
    grobid, session = client
    session.post.return_value = make_response(500, "[NO_BLOCKS] PDF parsing resulted in empty")
    with pytest.raises(GrobidError, match="NO_BLOCKS") as info:
        grobid.process_pdf(pdf, GrobidEndpoint.FULLTEXT)
    assert info.value.status_code == 500


def test_wrong_input_kind_is_rejected(client, pdf):
    grobid, _ = client
    with pytest.raises(ValueError):
        grobid.process_pdf(pdf, GrobidEndpoint.CITATION)
    with pytest.raises(ValueError):
        grobid.process_citations("ref", GrobidEndpoint.FULLTEXT)
    with pytest.raises(ValueError):
        grobid.process_citations(["a", "b"], GrobidEndpoint.CITATION)


def test_citations_sent_as_repeated_field(client):
    grobid, session = client
    session.post.return_value = make_response(text="<listBibl/>")
    grobid.process_citations(["ref one", "ref two"], GrobidEndpoint.CITATION_LIST)
    data = session.post.call_args.kwargs["data"]
    assert [value for key, value in data if key == "citations"] == ["ref one", "ref two"]


def test_no_content_is_a_distinct_error(client, pdf):
    grobid, session = client
    session.post.return_value = make_response(204, "")
    with pytest.raises(GrobidNoContentError):
        grobid.process_pdf(pdf, GrobidEndpoint.REFERENCES)
