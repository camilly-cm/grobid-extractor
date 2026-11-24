import json
from unittest.mock import MagicMock

from grobid_extractor import GrobidEndpoint, GrobidError, OutputFormat, Settings, process_pdfs


def fake_client(tei, fail_on=()):
    client = MagicMock()
    client.settings = Settings(concurrency=2)

    def process_pdf(path, endpoint, options=None):
        if path.name in fail_on:
            raise GrobidError("HTTP 500: [NO_BLOCKS]", 500)
        return tei

    client.process_pdf.side_effect = process_pdf
    return client


def test_batch_writes_outputs_and_error_report(tmp_path, fulltext_tei):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    for name in ("good.pdf", "scanned.pdf"):
        (pdfs / name).write_bytes(b"%PDF")
    out = tmp_path / "out"

    report = process_pdfs(
        fake_client(fulltext_tei, fail_on={"scanned.pdf"}), GrobidEndpoint.FULLTEXT, pdfs, out,
        formats={OutputFormat.TEI, OutputFormat.JSON, OutputFormat.TEXT, OutputFormat.MARKDOWN},
    )

    target = out / "fulltext"
    assert report.count("ok") == 1
    assert report.count("error") == 1
    assert (target / "good.tei.xml").exists()
    assert json.loads((target / "good.json").read_text(encoding="utf-8"))["biblio"]["title"]
    assert "Blowflies colonize" in (target / "good.txt").read_text(encoding="utf-8")
    assert (target / "good.md").exists()
    errors = json.loads((target / "_errors.json").read_text(encoding="utf-8"))
    assert errors["errors"][0]["status_code"] == 500


def test_existing_results_are_skipped(tmp_path, fulltext_tei):
    (tmp_path / "a.pdf").write_bytes(b"%PDF")
    client = fake_client(fulltext_tei)
    process_pdfs(client, GrobidEndpoint.HEADER, tmp_path / "a.pdf", tmp_path / "out")
    report = process_pdfs(client, GrobidEndpoint.HEADER, tmp_path / "a.pdf", tmp_path / "out")
    assert report.count("skipped") == 1
    assert client.process_pdf.call_count == 1


def test_fulltext_only_formats_dropped_for_header(tmp_path, fulltext_tei):
    (tmp_path / "a.pdf").write_bytes(b"%PDF")
    process_pdfs(fake_client(fulltext_tei), GrobidEndpoint.HEADER, tmp_path / "a.pdf",
                 tmp_path / "out", formats={OutputFormat.JSON, OutputFormat.TEXT})
    files = sorted(p.name for p in (tmp_path / "out" / "header").iterdir())
    assert files == ["a.json"]
