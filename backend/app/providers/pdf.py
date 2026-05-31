"""PDF clinical connector — extracts structured records from text-layer PDFs."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber

from backend.app.providers.base import (
    Capability,
    ConnectorDataError,
    FetchResult,
    HealthStatus,
    Provenance,
    Provider,
)

# ── Section markers ───────────────────────────────────────────────────────────

_DIAGNOSES_HEADER = "PRIMARY DIAGNOSES"
_MEDS_HEADER = "MEDICATIONS AT DISCHARGE"
_MEDS_END = "CLINICAL PHARMACIST NOTE"
_MEDS_TABLE_HEADER = re.compile(r"^Medication Dose/Route Indication Frequency$", re.MULTILINE)

# ── Per-field patterns ────────────────────────────────────────────────────────

_PATIENT_RE = re.compile(
    r"Patient:\s*(?P<name>.+?)\s+DOB:\s*(?P<dob>[A-Za-z]+ \d{1,2},? \d{4})"
)
_MRN_RE = re.compile(r"MRN:\s*(?P<mrn>[A-Z0-9\-]+)")
_GENDER_RE = re.compile(r"Gender:\s*(?P<gender>Male|Female|Other|Unknown)", re.IGNORECASE)
_CONDITION_LINE_RE = re.compile(
    r"^(?P<num>\d+)\.\s+(?P<text>.+?)\s+\((?P<icd>[A-Z]\d+(?:\.\d+)?)\)\s*$",
    re.MULTILINE,
)
# Matches a medication table row: name ... dose-unit route
_MED_LINE_RE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z ]+?)\s+"
    r"(?P<dose>\d[\d.]*\s*(?:mg|mEq|mcg|unit)\s+\w+)"
    r"\s+(?P<rest>.+)$",
    re.MULTILINE,
)
_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


# ── Public span type ──────────────────────────────────────────────────────────


@dataclass(slots=True, frozen=True)
class TextSpan:
    """Character-level location within a single PDF page's extracted text."""

    page: int    # 1-based page number
    start: int   # inclusive char offset in page text
    end: int     # exclusive char offset in page text
    snippet: str # the exact text at [start:end] — use for highlight verification


# ── Provider ──────────────────────────────────────────────────────────────────


class PDFProvider(Provider):
    """Extracts Patient, Condition, and MedicationRequest records from a text-layer PDF.

    Scanned (image-only) PDFs are rejected at extraction time.
    Character offsets in each Provenance.span point to exact source positions.
    """

    id = "pdf"
    capabilities = Capability.PATIENT | Capability.MEDICATIONS | Capability.CONDITIONS

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        try:
            return _extract(self._path, patient_id)
        except ConnectorDataError:
            raise
        except Exception as exc:
            raise ConnectorDataError(f"PDF extraction failed: {exc}") from exc

    async def health_check(self) -> HealthStatus:
        ok = self._path.exists()
        return HealthStatus(
            ok=ok,
            latency_ms=0.0,
            detail=str(self._path) if ok else f"File not found: {self._path}",
        )


# ── Extraction helpers ────────────────────────────────────────────────────────


def _extract(path: Path, patient_id: str) -> FetchResult:
    if not path.exists():
        raise ConnectorDataError(f"PDF not found: {path}")

    pages: dict[int, str] = {}
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                raise ConnectorDataError(
                    f"Page {i} has no extractable text — scanned PDF not supported"
                )
            pages[i] = text

    provenance: list[Provenance] = []
    warnings: list[str] = []

    patient = _extract_patient(pages, patient_id, provenance, warnings)
    conditions = _extract_conditions(pages, provenance)
    meds = _extract_medications(pages, provenance, warnings)

    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": (
            [{"resource": patient}]
            + [{"resource": c} for c in conditions]
            + [{"resource": m} for m in meds]
        ),
    }

    return FetchResult(
        bundle=bundle,
        source="pdf",
        fetched_at=datetime.now(UTC),
        partial=not conditions and not meds,
        warnings=warnings,
        provenance=provenance,
        coverage={
            "patient": {"requested": True, "returned": True},
            "conditions": {"requested": True, "returned": bool(conditions)},
            "medications": {"requested": True, "returned": bool(meds)},
        },
    )


def _make_span(text: str, fragment: str, page: int) -> TextSpan | None:
    idx = text.find(fragment)
    if idx < 0:
        return None
    return TextSpan(page=page, start=idx, end=idx + len(fragment), snippet=fragment)


def _span_dict(span: TextSpan) -> dict:
    return {"page": span.page, "start": span.start, "end": span.end, "snippet": span.snippet}


def _parse_date_english(raw: str) -> str | None:
    m = re.match(r"(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})", raw)
    if not m:
        return None
    month_num = _MONTHS.get(m.group("month").lower())
    if not month_num:
        return None
    return f"{m.group('year')}-{month_num}-{int(m.group('day')):02d}"


def _extract_patient(
    pages: dict[int, str],
    patient_id: str,
    provenance: list[Provenance],
    warnings: list[str],
) -> dict:
    p1 = pages.get(1, "")
    patient: dict = {"resourceType": "Patient", "id": patient_id}

    m = _PATIENT_RE.search(p1)
    if m:
        name_raw = m.group("name").strip()
        parts = name_raw.split()
        family = parts[-1] if parts else ""
        given = parts[:-1]
        patient["name"] = [{"family": family, "given": given}]
        dob = _parse_date_english(m.group("dob"))
        if dob:
            patient["birthDate"] = dob
        span = _make_span(p1, m.group(0), 1)
        if span:
            provenance.append(Provenance(
                resource_ref=f"Patient/{patient_id}",
                source_provider="pdf",
                source_record_id="1",
                span=_span_dict(span),
            ))
    else:
        warnings.append("Patient name/DOB not found in PDF")

    mrn_m = _MRN_RE.search(p1)
    if mrn_m:
        patient["identifier"] = [{"system": "urn:oid:mrn", "value": mrn_m.group("mrn")}]

    gender_m = _GENDER_RE.search(p1)
    if gender_m:
        patient["gender"] = gender_m.group("gender").lower()
    else:
        warnings.append("Gender not found in PDF")

    return patient


def _extract_conditions(
    pages: dict[int, str],
    provenance: list[Provenance],
) -> list[dict]:
    conditions: list[dict] = []
    for page_num, text in pages.items():
        for m in _CONDITION_LINE_RE.finditer(text):
            description = m.group("text").strip()
            icd_code = m.group("icd")
            condition_id = f"condition-{icd_code.replace('.', '-').lower()}"
            span = TextSpan(
                page=page_num,
                start=m.start(),
                end=m.end(),
                snippet=m.group(0).strip(),
            )
            conditions.append({
                "resourceType": "Condition",
                "id": condition_id,
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": icd_code}],
                    "text": description,
                },
            })
            provenance.append(Provenance(
                resource_ref=f"Condition/{condition_id}",
                source_provider="pdf",
                source_record_id=str(page_num),
                span=_span_dict(span),
            ))
    return conditions


def _extract_medications(
    pages: dict[int, str],
    provenance: list[Provenance],
    warnings: list[str],
) -> list[dict]:
    meds: list[dict] = []
    for page_num, text in pages.items():
        section = _medications_section(text)
        if section is None:
            continue
        section_text, section_offset = section
        for m in _MED_LINE_RE.finditer(section_text):
            name = m.group("name").strip()
            dose = m.group("dose").strip()
            rest = m.group("rest").strip()

            # Skip table header rows caught by the regex
            if name.lower().startswith("medication"):
                continue

            med_id = f"med-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}"
            raw_line = m.group(0)
            # Offset within page text = section_offset + offset within section
            abs_start = section_offset + m.start()
            abs_end = section_offset + m.end()
            span = TextSpan(
                page=page_num,
                start=abs_start,
                end=abs_end,
                snippet=raw_line.strip(),
            )
            meds.append({
                "resourceType": "MedicationRequest",
                "id": med_id,
                "medicationCodeableConcept": {"text": name},
                "dosageInstruction": [{"text": f"{dose} — {rest}"}],
            })
            provenance.append(Provenance(
                resource_ref=f"MedicationRequest/{med_id}",
                source_provider="pdf",
                source_record_id=str(page_num),
                span=_span_dict(span),
            ))

    if not meds:
        warnings.append("No medications extracted — check PDF format")
    return meds


def _medications_section(page_text: str) -> tuple[str, int] | None:
    """Return (section_text, start_offset_in_page) for the med table body, or None."""
    start = page_text.find(_MEDS_HEADER)
    if start < 0:
        return None
    end = page_text.find(_MEDS_END, start)
    section = page_text[start:end] if end >= 0 else page_text[start:]

    # Skip past the table header line
    hdr = _MEDS_TABLE_HEADER.search(section)
    if hdr:
        body_start = start + hdr.end()
        body = page_text[body_start:start + len(section)]
        return body, body_start

    return section, start


def extract_pages(path: str | Path) -> dict[int, str]:
    """Return {page_number: extracted_text} for all pages. Public for testing."""
    pages: dict[int, str] = {}
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages[i] = page.extract_text() or ""
    return pages
