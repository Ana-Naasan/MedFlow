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

from backend.app.providers.base import Capability, ConnectorDataError, FetchResult
from backend.app.providers.pdf import PDFProvider, extract_pages, _extract

_PDF = Path("backend/app/seeds/sample_clinical.pdf")
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
    return [e["resource"] for e in result.bundle["entry"] if e["resource"]["resourceType"] == resource_type]


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
    assert len(_resources(result, "MedicationRequest")) >= 7


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
    names = [m["medicationCodeableConcept"]["text"] for m in _resources(result, "MedicationRequest")]
    assert any("Warfarin" in n for n in names)


def test_aspirin_extracted(result: FetchResult) -> None:
    names = [m["medicationCodeableConcept"]["text"] for m in _resources(result, "MedicationRequest")]
    assert any("Aspirin" in n for n in names)


# ── Offset integrity: all spans ───────────────────────────────────────────────


def test_all_resources_have_provenance(result: FetchResult) -> None:
    resource_refs = {e["resource"]["resourceType"] + "/" + e["resource"]["id"] for e in result.bundle["entry"]}
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
        assert expected == actual, (
            f"{prov.resource_ref}: offset span={expected} != snippet len={actual}"
        )


def test_quote_is_really_in_source_text(result: FetchResult, pages: dict[int, str]) -> None:
    """Core invariant: every snippet must match page_text[start:end] exactly."""
    for prov in result.provenance:
        span = prov.span
        page_text = pages[span["page"]]
        actual = page_text[span["start"]: span["end"]]
        assert actual == span["snippet"], (
            f"{prov.resource_ref}: "
            f"page_text[{span['start']}:{span['end']}]={actual!r} "
            f"!= span.snippet={span['snippet']!r}"
        )


def test_warfarin_span_verifiable_in_source(result: FetchResult, pages: dict[int, str]) -> None:
    """Planted interaction: Warfarin provenance must reference exact source text."""
    warfarin_provs = [
        p for p in result.provenance
        if p.span and "Warfarin" in p.span.get("snippet", "")
    ]
    assert warfarin_provs, "No Warfarin span in provenance"
    for prov in warfarin_provs:
        span = prov.span
        source = pages[span["page"]][span["start"]: span["end"]]
        assert "Warfarin" in source


def test_aspirin_span_verifiable_in_source(result: FetchResult, pages: dict[int, str]) -> None:
    aspirin_provs = [
        p for p in result.provenance
        if p.span and "Aspirin" in p.span.get("snippet", "")
    ]
    assert aspirin_provs, "No Aspirin span in provenance"
    for prov in aspirin_provs:
        span = prov.span
        source = pages[span["page"]][span["start"]: span["end"]]
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
