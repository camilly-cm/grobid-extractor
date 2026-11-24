"""Small lxml-based helpers to read GROBID TEI.

Used for bibliographic structures (``biblStruct``), which the citation endpoints
return directly and which the ``processReferences`` endpoint returns inside a
``listBibl``.
"""

from __future__ import annotations

from typing import Any

from lxml import etree

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def parse_xml(tei: str | bytes) -> etree._Element:
    data = tei.encode("utf-8") if isinstance(tei, str) else tei
    parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True)
    root = etree.fromstring(data, parser=parser)
    if root is None:
        raise ValueError("Response is not valid XML")
    # GROBID is inconsistent: full documents use the TEI namespace, citation
    # endpoints return bare <biblStruct>. Drop element namespaces so one set of
    # XPath expressions works for both.
    for element in root.iter():
        if isinstance(element.tag, str):
            element.tag = etree.QName(element).localname
    return root


def _text(element: etree._Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _first(element: etree._Element, xpath: str) -> etree._Element | None:
    found = element.xpath(xpath)
    return found[0] if found else None


def _person_name(pers: etree._Element) -> str:
    forenames = [_text(f) for f in pers.xpath("forename")]
    surname = _text(_first(pers, "surname"))
    return " ".join(part for part in [*forenames, surname] if part)


def parse_bibl_struct(bibl: etree._Element) -> dict[str, Any]:
    """Convert one ``biblStruct`` into a flat dictionary."""
    analytic = _first(bibl, "analytic")
    monogr = _first(bibl, "monogr")
    imprint = _first(monogr, "imprint") if monogr is not None else None

    authors_xpath = "(analytic|monogr)/author/persName"
    authors = [name for name in (_person_name(p) for p in bibl.xpath(authors_xpath)) if name]
    title = _text(_first(analytic, "title")) if analytic is not None else ""
    venue = _text(_first(monogr, "title")) if monogr is not None else ""
    if not title:
        title, venue = venue, ""

    def bibl_scope(unit: str) -> str:
        if imprint is None:
            return ""
        scope = _first(imprint, f"biblScope[@unit='{unit}']")
        if scope is None:
            return ""
        if scope.get("from") or scope.get("to"):
            return "-".join(v for v in (scope.get("from"), scope.get("to")) if v)
        return _text(scope)

    date = _first(imprint, "date") if imprint is not None else None
    identifiers = {
        (idno.get("type") or "id").lower(): _text(idno)
        for idno in bibl.xpath(".//idno")
    }
    raw = _first(bibl, "note[@type='raw_reference']")

    record: dict[str, Any] = {
        "id": bibl.get(XML_ID, ""),
        "title": title,
        "authors": authors,
        "venue": venue,
        "year": (date.get("when", "")[:4] if date is not None else "") or _text(date)[:4],
        "volume": bibl_scope("volume"),
        "issue": bibl_scope("issue"),
        "pages": bibl_scope("page"),
        "publisher": _text(_first(imprint, "publisher")) if imprint is not None else "",
        "identifiers": identifiers,
    }
    if raw is not None:
        record["raw"] = _text(raw)
    return record


def parse_bibl_structs(tei: str | bytes) -> list[dict[str, Any]]:
    """Return every ``biblStruct`` in a TEI response (citation or references endpoint)."""
    root = parse_xml(tei)
    if etree.QName(root).localname == "biblStruct":
        structs = [root]
    else:
        # Skip the document's own header biblStruct (inside sourceDesc).
        structs = root.xpath("//biblStruct[not(ancestor::sourceDesc)]")
    return [parse_bibl_struct(b) for b in structs]


def parse_header(tei: str | bytes) -> dict[str, Any]:
    """Extract the main metadata from a header/fulltext TEI document."""
    root = parse_xml(tei)
    source = _first(root, "//sourceDesc/biblStruct")
    record = parse_bibl_struct(source) if source is not None else {}
    title = _first(root, "//titleStmt/title")
    abstract = _first(root, "//profileDesc/abstract")
    keywords = root.xpath("//profileDesc/textClass/keywords/term")
    affiliations = sorted({
        _text(org) for org in root.xpath("//sourceDesc//affiliation/orgName")
    } - {""})
    record.update(
        title=_text(title) or record.get("title", ""),
        abstract=_text(abstract),
        keywords=[_text(k) for k in keywords if _text(k)],
        affiliations=affiliations,
        language=root.get(XML_LANG, ""),
    )
    return record
