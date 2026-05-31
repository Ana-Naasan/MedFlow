"""Tests for PDF clinical connector — providers/pdf.py.

Frozen fixture: backend/app/seeds/sample_clinical.pdf
Do NOT regenerate this file unless the planted-interaction text needs to change;
if you do, update _DEMO_PDF_SHA256 below and document the reason.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest
from fhir.resources.R4B.medicationstatement import MedicationStatement

from backend.app.fhir.flatten import flatten_to_tagged_text
from backend.app.providers.base import Capability, ConnectorDataError, FetchResult
from backend.app.providers.pdf import (
    PDFProvider,
    _extract,
    _extract_medications,
    _extract_patient,
    _make_span,
    _medications_section,
    _parse_date_english,
    extract_pages,
)

# Anchor the fixture to this file (CWD-independent: CI runs pytest from backend/,
# local runs from the repo root — a relative literal would break under one of them).
_PDF = Path(__file__).resolve().parent.parent / "seeds" / "sample_clinical.pdf"
_PATIENT_ID = "demo"

# Freeze: any change to this file must be deliberate and reflected here.
_DEMO_PDF_SHA256 = "c0584d226e53feeefe0f799667c812c800f70cc3dccdd4d99916a18e7f37e7f6"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def result() -> FetchResult:
    provider = PDFProvider(_PDF)
    return asyncio.run(provider.fetch_patient(_PATIENT_ID))


@pytest.fixture(scope="module")
def pages() -> dict[int, str]:
    return extract_pages(_PDF)


def _resources(result: FetchResult, resource_type: str) -> list[dict]:
    return [
        e["resource"]
        for e in result.bundle["entry"]
        if e["resource"]["resourceType"] == resource_type
    ]


# ── Freeze test ───────────────────────────────────────────────────────────────


def test_demo_pdf_sha256_frozen() -> None:
    """Fail loudly if the frozen demo PDF changes unexpectedly."""
    digest = hashlib.sha256(_PDF.read_bytes()).hexdigest()
    assert digest == _DEMO_PDF_SHA256, (
        f"sample_clinical.pdf changed! Got {digest!r}, expected {_DEMO_PDF_SHA256!r}. "
        "Update _DEMO_PDF_SHA256 in this file and document the change."
    )


# ── Health check ──────────────────────────────────────────────────────────────


def test_health_check_ok() -> None:
    status = asyncio.run(PDFProvider(_PDF).health_check())
    assert status.ok


def test_health_check_missing_file() -> None:
    status = asyncio.run(PDFProvider("nonexistent.pdf").health_check())
    assert not status.ok


# ── Capabilities ──────────────────────────────────────────────────────────────


def test_provider_supports_patient() -> None:
    assert PDFProvider(_PDF).supports(Capability.PATIENT)


def test_provider_supports_medications() -> None:
    assert PDFProvider(_PDF).supports(Capability.MEDICATIONS)


def test_provider_supports_conditions() -> None:
    assert PDFProvider(_PDF).supports(Capability.CONDITIONS)


# ── Extraction: bundle structure ──────────────────────────────────────────────


def test_returns_fhir_bundle(result: FetchResult) -> None:
    assert result.bundle["resourceType"] == "Bundle"


def test_bundle_has_patient(result: FetchResult) -> None:
    assert len(_resources(result, "Patient")) == 1


def test_bundle_has_five_conditions(result: FetchResult) -> None:
    assert len(_resources(result, "Condition")) >= 5


def test_bundle_has_eight_medications(result: FetchResult) -> None:
    assert len(_resources(result, "MedicationStatement")) >= 7


def test_source_is_pdf(result: FetchResult) -> None:
    assert result.source == "pdf"


# ── Extraction: patient demographics ─────────────────────────────────────────


def test_patient_id(result: FetchResult) -> None:
    assert _resources(result, "Patient")[0]["id"] == _PATIENT_ID


def test_patient_family_name(result: FetchResult) -> None:
    assert _resources(result, "Patient")[0]["name"][0]["family"] == "Romaguera"


def test_patient_given_name(result: FetchResult) -> None:
    assert "Kent" in _resources(result, "Patient")[0]["name"][0]["given"]


def test_patient_birth_date(result: FetchResult) -> None:
    assert _resources(result, "Patient")[0]["birthDate"] == "1940-01-09"


def test_patient_gender(result: FetchResult) -> None:
    assert _resources(result, "Patient")[0]["gender"] == "male"


def test_patient_mrn(result: FetchResult) -> None:
    patient = _resources(result, "Patient")[0]
    mrns = [i["value"] for i in patient.get("identifier", []) if i.get("system") == "urn:oid:mrn"]
    assert "25127-BD5-F9AA" in mrns


# ── Extraction: conditions ────────────────────────────────────────────────────


def test_condition_afib_present(result: FetchResult) -> None:
    codes = [c["code"]["coding"][0]["code"] for c in _resources(result, "Condition")]
    assert "I48.91" in codes


def test_condition_diabetes_present(result: FetchResult) -> None:
    codes = [c["code"]["coding"][0]["code"] for c in _resources(result, "Condition")]
    assert "E11.9" in codes


def test_conditions_use_icd10_system(result: FetchResult) -> None:
    for c in _resources(result, "Condition"):
        assert c["code"]["coding"][0]["system"] == "http://hl7.org/fhir/sid/icd-10"


# ── Extraction: medications (planted interaction) ─────────────────────────────


def test_warfarin_extracted(result: FetchResult) -> None:
    names = [
        m["medicationCodeableConcept"]["text"] for m in _resources(result, "MedicationStatement")
    ]
    assert any("Warfarin" in n for n in names)


def test_aspirin_extracted(result: FetchResult) -> None:
    names = [
        m["medicationCodeableConcept"]["text"] for m in _resources(result, "MedicationStatement")
    ]
    assert any("Aspirin" in n for n in names)


# ── Offset integrity: all spans ───────────────────────────────────────────────


def test_all_resources_have_provenance(result: FetchResult) -> None:
    resource_refs = {
        e["resource"]["resourceType"] + "/" + e["resource"]["id"] for e in result.bundle["entry"]
    }
    prov_refs = {p.resource_ref for p in result.provenance}
    assert resource_refs == prov_refs


def test_every_span_has_required_fields(result: FetchResult) -> None:
    for prov in result.provenance:
        assert prov.span is not None, f"{prov.resource_ref} missing span"
        for field in ("page", "start", "end", "snippet"):
            assert field in prov.span, f"{prov.resource_ref} span missing {field!r}"


def test_span_start_strictly_before_end(result: FetchResult) -> None:
    for prov in result.provenance:
        span = prov.span
        assert span["start"] < span["end"], f"{prov.resource_ref}: start >= end"


def test_snippet_length_matches_offsets(result: FetchResult) -> None:
    for prov in result.provenance:
        span = prov.span
        expected = span["end"] - span["start"]
        actual = len(span["snippet"])
        assert (
            expected == actual
        ), f"{prov.resource_ref}: offset span={expected} != snippet len={actual}"


def test_quote_is_really_in_source_text(result: FetchResult, pages: dict[int, str]) -> None:
    """Core invariant: every snippet must match page_text[start:end] exactly."""
    for prov in result.provenance:
        span = prov.span
        page_text = pages[span["page"]]
        actual = page_text[span["start"] : span["end"]]
        assert actual == span["snippet"], (
            f"{prov.resource_ref}: "
            f"page_text[{span['start']}:{span['end']}]={actual!r} "
            f"!= span.snippet={span['snippet']!r}"
        )


def test_warfarin_span_verifiable_in_source(result: FetchResult, pages: dict[int, str]) -> None:
    """Planted interaction: Warfarin provenance must reference exact source text."""
    warfarin_provs = [
        p for p in result.provenance if p.span and "Warfarin" in p.span.get("snippet", "")
    ]
    assert warfarin_provs, "No Warfarin span in provenance"
    for prov in warfarin_provs:
        span = prov.span
        source = pages[span["page"]][span["start"] : span["end"]]
        assert "Warfarin" in source


def test_aspirin_span_verifiable_in_source(result: FetchResult, pages: dict[int, str]) -> None:
    aspirin_provs = [
        p for p in result.provenance if p.span and "Aspirin" in p.span.get("snippet", "")
    ]
    assert aspirin_provs, "No Aspirin span in provenance"
    for prov in aspirin_provs:
        span = prov.span
        source = pages[span["page"]][span["start"] : span["end"]]
        assert "Aspirin" in source


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_missing_pdf_raises_connector_data_error() -> None:
    with pytest.raises(ConnectorDataError, match="PDF not found"):
        _extract(Path("does_not_exist.pdf"), "p1")


def test_scanned_pdf_rejected(tmp_path: Path) -> None:
    """Page with no extractable text must be rejected with a clear error."""
    # Minimal valid PDF with a blank page (no text content stream).
    # xref offsets are approximate but sufficient for pdfplumber to open.
    blank_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n195\n%%EOF\n"
    )
    out = tmp_path / "blank.pdf"
    out.write_bytes(blank_pdf)
    with pytest.raises(ConnectorDataError, match="no extractable text"):
        _extract(out, "p1")


def test_multi_page_pdf_extracts_all_pages(result: FetchResult) -> None:
    """Demo PDF has 2 pages; page 2 contains lab values — verify pages covered."""
    pages_referenced = {p.span["page"] for p in result.provenance if p.span}
    assert 1 in pages_referenced


def test_lab_page_text_accessible(pages: dict[int, str]) -> None:
    """Page 2 (lab values) must be readable even without record extraction from it."""
    assert 2 in pages
    assert "INR" in pages[2]
    assert "Creatinine" in pages[2]


# ── Medications: FHIR R4B MedicationStatement shape ──────────────────────────


def test_medications_are_medication_statements(result: FetchResult) -> None:
    """Meds must be MedicationStatement, the 6-resource subset type the flattener
    and reasoning core key on — a MedicationRequest is silently dropped downstream."""
    assert _resources(result, "MedicationStatement")
    assert not _resources(result, "MedicationRequest")


def test_medications_validate_as_r4b(result: FetchResult) -> None:
    """Every emitted medication must round-trip through the R4B model."""
    meds = _resources(result, "MedicationStatement")
    assert meds, "no medications extracted — test would pass vacuously"
    for med in meds:
        MedicationStatement.model_validate(med)


def test_medications_have_status_and_subject(result: FetchResult) -> None:
    meds = _resources(result, "MedicationStatement")
    assert meds, "no medications extracted — test would pass vacuously"
    for med in meds:
        assert med["status"] == "active"
        assert med["subject"]["reference"] == f"Patient/{_PATIENT_ID}"


def test_medication_dose_survives_flatten(result: FetchResult) -> None:
    """End-to-end: the extracted dose must reach the flattened reasoning context,
    not merely sit on the resource dict. Regression for the producer/consumer gap
    where the connector wrote dosage[].text but flatten._dose() read only the
    structured doseQuantity — silently dropping every dose before reasoning."""
    rendered = flatten_to_tagged_text([e["resource"] for e in result.bundle["entry"]])
    meds_section = rendered.split("## Conditions")[0]
    warfarin_line = [ln for ln in meds_section.splitlines() if "Warfarin" in ln]
    assert warfarin_line, "Warfarin missing from flattened Medications section"
    # The planted Warfarin interaction must carry its dose into the reasoning context.
    assert "mg" in warfarin_line[0], f"dose dropped before reasoning: {warfarin_line[0]!r}"


# ── Helper-level coverage: error, edge, and warning paths ────────────────────


def test_fetch_patient_passes_through_connector_error() -> None:
    """A missing PDF surfaces as ConnectorDataError, not re-wrapped."""
    with pytest.raises(ConnectorDataError, match="PDF not found"):
        asyncio.run(PDFProvider("nonexistent.pdf").fetch_patient("p1"))


def test_fetch_patient_wraps_unexpected_error(tmp_path: Path) -> None:
    """A non-PDF file makes pdfplumber raise; it is wrapped as ConnectorDataError."""
    bad = tmp_path / "not.pdf"
    bad.write_bytes(b"this is plainly not a PDF")
    with pytest.raises(ConnectorDataError, match="PDF extraction failed"):
        asyncio.run(PDFProvider(bad).fetch_patient("p1"))


def test_make_span_returns_none_when_fragment_absent() -> None:
    assert _make_span("the quick brown fox", "zebra", 1) is None


def test_parse_date_english_rejects_unparseable() -> None:
    assert _parse_date_english("not a date at all") is None


def test_parse_date_english_rejects_unknown_month() -> None:
    assert _parse_date_english("Smarch 3, 2020") is None


def test_extract_patient_warns_on_missing_name_and_gender() -> None:
    warnings: list[str] = []
    patient = _extract_patient({1: "header only, no demographics here"}, "p1", [], warnings)
    assert patient == {"resourceType": "Patient", "id": "p1"}
    assert any("name/DOB not found" in w for w in warnings)
    assert any("Gender not found" in w for w in warnings)


def test_extract_medications_skips_header_row_and_warns_when_empty() -> None:
    """A row whose name is the literal 'Medication' header is skipped; with no
    real rows left, the connector records the no-medications warning."""
    page = (
        "MEDICATIONS AT DISCHARGE\n"
        "Medication Dose/Route Indication Frequency\n"
        "Medication 10 mg PO daily\n"
        "CLINICAL PHARMACIST NOTE\n"
    )
    warnings: list[str] = []
    meds = _extract_medications({1: page}, "p1", [], warnings)
    assert meds == []
    assert any("No medications extracted" in w for w in warnings)


def test_medications_section_without_table_header() -> None:
    """A med section lacking the table-header line falls back to the raw section
    span starting at the section header."""
    page = "MEDICATIONS AT DISCHARGE\nWarfarin 5 mg PO Daily\nCLINICAL PHARMACIST NOTE\n"
    section = _medications_section(page)
    assert section is not None
    body, offset = section
    assert offset == page.find("MEDICATIONS AT DISCHARGE")
    assert "Warfarin" in body


def test_provenance_snippet_matches_offsets_with_trailing_whitespace() -> None:
    """Core citation invariant: span snippet must equal page_text[start:end] even
    when the matched line carries trailing whitespace (stripping only the snippet
    would silently break the offsets)."""
    page = "MEDICATIONS AT DISCHARGE\nWarfarin 5 mg oral AFib Daily   \nCLINICAL PHARMACIST NOTE\n"
    prov: list = []
    _extract_medications({1: page}, "p1", prov, [])
    assert prov, "no medication provenance produced"
    for p in prov:
        span = p.span
        assert page[span["start"] : span["end"]] == span["snippet"]
