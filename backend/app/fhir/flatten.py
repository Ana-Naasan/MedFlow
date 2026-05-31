"""Render FHIR resources as tagged markdown for the reasoning engine.

Every data line is prefixed [ResourceType/id] so every claim is traceable.
Every category is always shown — present / stated-as-none / not-documented.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

# SNOMED codes for "no known allergy / no known drug allergy / no known food allergy"
_NKA_CODES: frozenset[str] = frozenset({"716186003", "409137002", "428607008"})

# (resourceType, section heading) — order defines output order
_CATEGORIES: list[tuple[str, str]] = [
    ("MedicationStatement", "Medications"),
    ("Condition", "Conditions"),
    ("Observation", "Labs & Symptoms"),
    ("AllergyIntolerance", "Allergies"),
    ("Procedure", "Procedures"),
]

_CATEGORY_TYPES: frozenset[str] = frozenset(rt for rt, _ in _CATEGORIES)


def flatten_to_tagged_text(resources: Iterable[dict]) -> str:
    """Render a list of FHIR resource dicts as tagged markdown.

    Every data line is prefixed [ResourceType/id].
    Every category (medications, conditions, labs, allergies, procedures) is
    always shown, even when empty, using one of three states:
      - present        → [Tag] <extracted values>
      - stated as none → [Tag] _(stated as none by source)_  (NKA allergy codes)
      - not documented → _(not documented)_

    Patient and other non-clinical resource types are silently ignored.
    """
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in resources:
        rt = r.get("resourceType", "")
        if rt in _CATEGORY_TYPES:
            by_type[rt].append(r)

    sections: list[str] = []
    for resource_type, heading in _CATEGORIES:
        sections.append(f"## {heading}")
        items = by_type.get(resource_type) or []
        if not items:
            sections.append("_(not documented)_")
        else:
            for item in items:
                rid = item.get("id", "unknown")
                tag = f"[{resource_type}/{rid}]"
                if _is_nka(resource_type, item):
                    sections.append(f"{tag} _(stated as none by source)_")
                else:
                    sections.append(f"{tag} {_render(resource_type, item)}")
        sections.append("")

    return "\n".join(sections).rstrip()


# ── Per-type renderers ────────────────────────────────────────────────────────


def _render(resource_type: str, r: dict) -> str:
    if resource_type == "MedicationStatement":
        name = _concept(r.get("medicationCodeableConcept"))
        status = r.get("status", "")
        dose_str = _dose(r)
        return f"{name}{dose_str} — {status}"

    if resource_type == "Condition":
        name = _concept(r.get("code"))
        clinical = _first_code(r.get("clinicalStatus"))
        verification = _first_code(r.get("verificationStatus"))
        return f"{name} — {clinical}, {verification}"

    if resource_type == "Observation":
        name = _concept(r.get("code"))
        value_str = _obs_value(r)
        date = _date(r.get("effectiveDateTime") or _nested(r, "effectivePeriod", "start"))
        return f"{name}: {value_str}{date}"

    if resource_type == "AllergyIntolerance":
        substance = _concept(r.get("code"))
        status = _first_code(r.get("clinicalStatus"))
        return f"{substance} — {status}"

    if resource_type == "Procedure":
        name = _concept(r.get("code"))
        status = r.get("status", "")
        date = _date(r.get("performedDateTime") or _nested(r, "performedPeriod", "start"))
        return f"{name} — {status}{date}"

    return resource_type  # fallback (unreachable for known category types)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _concept(obj: dict | None) -> str:
    """Extract display text from a FHIR CodeableConcept."""
    if not obj:
        return ""
    text = obj.get("text", "")
    if text:
        return text
    codings = obj.get("coding") or []
    if codings:
        return codings[0].get("display") or codings[0].get("code", "")
    return ""


def _first_code(obj: dict | None) -> str:
    """Extract the first code value from a CodeableConcept's coding list."""
    if not obj:
        return ""
    codings = obj.get("coding") or []
    return codings[0].get("code", "") if codings else ""


def _nested(obj: dict, *keys: str) -> str | None:
    """Safe chained dict get: _nested(r, 'effectivePeriod', 'start')."""
    cur: object = obj
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur if isinstance(cur, str) else None


def _date(raw: str | None) -> str:
    """Return ' (YYYY-MM-DD)' or '' when raw is absent."""
    if not raw:
        return ""
    return f" ({raw[:10]})"


def _dose(r: dict) -> str:
    """Extract a dose string from MedicationStatement.dosage[0].

    Prefers the structured ``doseAndRate[0].doseQuantity``; falls back to the
    free-text ``dosage[0].text`` so sources that carry a raw dose/route/indication
    line (e.g. the PDF connector) still surface their dose into the reasoning
    context instead of having it silently dropped.
    """
    dosages = r.get("dosage") or []
    if not dosages:
        return ""
    dosage = dosages[0]
    dose_rates = dosage.get("doseAndRate") or []
    if dose_rates:
        dq = dose_rates[0].get("doseQuantity") or {}
        val = dq.get("value")
        if val is not None:
            unit = dq.get("unit", "")
            return f" {val} {unit}".rstrip()
    text = dosage.get("text")
    if text:
        return f" ({text})"
    return ""


def _obs_value(r: dict) -> str:
    """Extract observation value: valueQuantity > valueString > valueCodeableConcept."""
    vq = r.get("valueQuantity")
    if vq:
        val = vq.get("value", "")
        unit = vq.get("unit", "")
        return f"{val} {unit}".strip()
    vs = r.get("valueString")
    if vs:
        return vs
    vc = r.get("valueCodeableConcept")
    if vc:
        return _concept(vc)
    return ""


def _is_nka(resource_type: str, r: dict) -> bool:
    """Return True if this AllergyIntolerance encodes a 'no known allergy' assertion."""
    if resource_type != "AllergyIntolerance":
        return False
    codings = (r.get("code") or {}).get("coding") or []
    return any(isinstance(c, dict) and c.get("code") in _NKA_CODES for c in codings)
