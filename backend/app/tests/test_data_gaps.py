"""Tests for fhir/data_gaps.py — three-state coverage classification and
confidence downgrade rules (issue #30).

Required tests per issue spec:
  - "missing category shows as gap"      → test_missing_category_shows_as_gap
  - "confidence drops on missing field"  → test_confidence_drops_on_missing_allergy_field
  - "covers vs returned empty"           → test group at the bottom
"""

from __future__ import annotations

from backend.app.dtos import Citation, Hypothesis
from backend.app.fhir.data_gaps import (
    COVERAGE_TO_FHIR,
    apply_gap_downgrades,
    compute_data_gaps,
    coverage_state,
    downgrade_for_gaps,
    gap_fhir_types,
)

# ── Shared resource fixtures ──────────────────────────────────────────────────

_MED = {
    "resourceType": "MedicationStatement",
    "id": "m1",
    "status": "active",
    "medicationCodeableConcept": {"text": "Aspirin"},
}

_COND = {
    "resourceType": "Condition",
    "id": "c1",
    "code": {"text": "Hypertension"},
}

_ALLERGY = {
    "resourceType": "AllergyIntolerance",
    "id": "a1",
    "code": {"coding": [{"system": "http://snomed.info/sct", "code": "372687004"}]},
    "clinicalStatus": {"coding": [{"code": "active"}]},
}

# SNOMED NKA code (no known allergy)
_NKA = {
    "resourceType": "AllergyIntolerance",
    "id": "nka",
    "code": {"coding": [{"system": "http://snomed.info/sct", "code": "716186003"}]},
}

_OBS = {
    "resourceType": "Observation",
    "id": "o1",
    "code": {"text": "Serum creatinine"},
    "valueQuantity": {"value": 1.2, "unit": "mg/dL"},
}


def _make_hyp(
    confidence: str = "high",
    cite_med: bool = True,
    hyp_id: str = "h1",
) -> Hypothesis:
    citations = []
    if cite_med:
        citations.append(Citation(kind="resource", ref="MedicationStatement/m1", label="Med"))
    return Hypothesis(
        id=hyp_id,
        title="Drug interaction hypothesis",
        why="Patient is on aspirin.",
        severity="moderate",
        confidence=confidence,
        citations=citations,
    )


# ── coverage_state ────────────────────────────────────────────────────────────


def test_coverage_state_present_medication() -> None:
    assert coverage_state("MedicationStatement", [_MED]) == "present"


def test_coverage_state_present_condition() -> None:
    assert coverage_state("Condition", [_COND]) == "present"


def test_coverage_state_not_documented_empty() -> None:
    assert coverage_state("AllergyIntolerance", []) == "not_documented"


def test_coverage_state_not_documented_wrong_type() -> None:
    assert coverage_state("AllergyIntolerance", [_MED]) == "not_documented"


def test_coverage_state_nka_stated_none() -> None:
    """Single NKA code → stated_none (source explicitly says no known allergy)."""
    assert coverage_state("AllergyIntolerance", [_NKA]) == "stated_none"


def test_coverage_state_all_nka_stated_none() -> None:
    """All entries NKA → stated_none."""
    nka2 = {**_NKA, "id": "nka2"}
    assert coverage_state("AllergyIntolerance", [_NKA, nka2]) == "stated_none"


def test_coverage_state_mixed_nka_and_real_is_present() -> None:
    """Even one non-NKA allergy → present (not stated_none)."""
    assert coverage_state("AllergyIntolerance", [_NKA, _ALLERGY]) == "present"


def test_coverage_state_real_allergy_is_present() -> None:
    assert coverage_state("AllergyIntolerance", [_ALLERGY]) == "present"


def test_coverage_state_nka_code_in_non_allergy_type_is_present() -> None:
    """NKA code in a non-AllergyIntolerance resource is NOT treated as stated_none."""
    non_allergy = {**_NKA, "resourceType": "Condition"}
    assert coverage_state("Condition", [non_allergy]) == "present"


# ── compute_data_gaps ─────────────────────────────────────────────────────────


def test_missing_category_shows_as_gap() -> None:
    """Required: source covers allergies but returned nothing → shows as a gap."""
    coverage = {"allergies": {"requested": True, "returned": False}}
    gaps = compute_data_gaps([], coverage)
    assert len(gaps) == 1
    assert "Allergies" in gaps[0]


def test_nka_is_not_a_gap() -> None:
    """Required: source covers allergies and returned NKA → NOT a gap."""
    coverage = {"allergies": {"requested": True, "returned": True}}
    gaps = compute_data_gaps([_NKA], coverage)
    assert gaps == []


def test_uncovered_category_is_not_a_gap() -> None:
    """Source doesn't cover procedures → not a gap (out of scope)."""
    coverage = {"procedures": {"requested": False, "returned": False}}
    gaps = compute_data_gaps([], coverage)
    assert gaps == []


def test_present_category_no_gap() -> None:
    coverage = {"medications": {"requested": True, "returned": True}}
    gaps = compute_data_gaps([_MED], coverage)
    assert gaps == []


def test_multiple_gaps_all_reported() -> None:
    coverage = {
        "medications": {"requested": True, "returned": False},
        "conditions": {"requested": True, "returned": False},
        "allergies": {"requested": False, "returned": False},  # not covered → no gap
    }
    gaps = compute_data_gaps([], coverage)
    assert len(gaps) == 2


def test_unknown_coverage_key_ignored() -> None:
    coverage = {"custom_source_category": {"requested": True, "returned": False}}
    gaps = compute_data_gaps([], coverage)
    assert gaps == []


def test_gaps_output_is_sorted() -> None:
    """Determinism: same input always produces same ordering."""
    coverage = {
        "procedures": {"requested": True, "returned": False},
        "allergies": {"requested": True, "returned": False},
    }
    gaps1 = compute_data_gaps([], coverage)
    gaps2 = compute_data_gaps([], coverage)
    assert gaps1 == gaps2 == sorted(gaps1)


def test_gap_string_describes_category() -> None:
    coverage = {"observations": {"requested": True, "returned": False}}
    gaps = compute_data_gaps([], coverage)
    assert len(gaps) == 1
    assert "Observations" in gaps[0]


# ── downgrade_for_gaps ────────────────────────────────────────────────────────


def test_confidence_drops_on_missing_allergy_field() -> None:
    """Required: high confidence drops to medium when allergies are a safety gap."""
    hyp = _make_hyp(confidence="high", cite_med=True)
    result = downgrade_for_gaps(hyp, gap_fhir_types={"AllergyIntolerance"})
    assert result.confidence == "medium"


def test_confidence_drops_medium_to_low_on_gap() -> None:
    hyp = _make_hyp(confidence="medium", cite_med=True)
    result = downgrade_for_gaps(hyp, gap_fhir_types={"AllergyIntolerance"})
    assert result.confidence == "low"


def test_confidence_low_unchanged_at_floor() -> None:
    hyp = _make_hyp(confidence="low", cite_med=True)
    result = downgrade_for_gaps(hyp, gap_fhir_types={"AllergyIntolerance"})
    assert result.confidence == "low"


def test_missing_lab_also_triggers_downgrade() -> None:
    """Missing Observation (labs) is safety-critical for drug hypotheses."""
    hyp = _make_hyp(confidence="high", cite_med=True)
    result = downgrade_for_gaps(hyp, gap_fhir_types={"Observation"})
    assert result.confidence == "medium"


def test_non_safety_critical_gap_does_not_downgrade() -> None:
    """Missing procedures or conditions: not safety-critical → no downgrade."""
    hyp = _make_hyp(confidence="high", cite_med=True)
    result = downgrade_for_gaps(hyp, gap_fhir_types={"Procedure", "Condition"})
    assert result.confidence == "high"


def test_non_medication_hypothesis_not_downgraded() -> None:
    """Only medication-citing hypotheses are downgraded."""
    hyp = _make_hyp(confidence="high", cite_med=False)
    result = downgrade_for_gaps(hyp, gap_fhir_types={"AllergyIntolerance"})
    assert result.confidence == "high"


def test_no_gaps_returns_hypothesis_identity() -> None:
    """Empty gap set → same object returned (no downgrade, no copy)."""
    hyp = _make_hyp(confidence="high", cite_med=True)
    result = downgrade_for_gaps(hyp, gap_fhir_types=set())
    assert result is hyp


def test_unknown_confidence_value_unchanged() -> None:
    """Confidence value outside the ladder → leave untouched (fail-safe)."""
    hyp = Hypothesis(
        id="h2",
        title="t",
        why="w",
        severity="moderate",
        confidence="speculative",
        citations=[Citation(kind="resource", ref="MedicationStatement/m1")],
    )
    result = downgrade_for_gaps(hyp, gap_fhir_types={"AllergyIntolerance"})
    assert result.confidence == "speculative"


def test_downgrade_preserves_other_fields() -> None:
    hyp = _make_hyp(confidence="high", cite_med=True)
    result = downgrade_for_gaps(hyp, gap_fhir_types={"AllergyIntolerance"})
    assert result.id == hyp.id
    assert result.title == hyp.title
    assert result.why == hyp.why
    assert result.severity == hyp.severity
    assert result.citations == hyp.citations


# ── apply_gap_downgrades ──────────────────────────────────────────────────────


def test_apply_gap_downgrades_applies_to_all_hypotheses() -> None:
    hyps = [_make_hyp("high", hyp_id="h1"), _make_hyp("medium", hyp_id="h2")]
    results = apply_gap_downgrades(hyps, {"AllergyIntolerance"})
    assert results[0].confidence == "medium"
    assert results[1].confidence == "low"


def test_apply_gap_downgrades_empty_list() -> None:
    assert apply_gap_downgrades([], {"AllergyIntolerance"}) == []


def test_apply_gap_downgrades_no_gaps_leaves_all_unchanged() -> None:
    hyps = [_make_hyp("high"), _make_hyp("high")]
    results = apply_gap_downgrades(hyps, set())
    assert all(r.confidence == "high" for r in results)


# ── covers vs returned empty (three-state contract) ──────────────────────────


def test_covers_returned_empty_is_a_gap() -> None:
    """Source covers allergies, returned no records → gap (not documented)."""
    coverage = {"allergies": {"requested": True, "returned": False}}
    gaps = compute_data_gaps([], coverage)
    assert len(gaps) == 1


def test_covers_returned_nka_is_not_a_gap() -> None:
    """Source covers allergies, returned NKA → NOT a gap (stated as none)."""
    coverage = {"allergies": {"requested": True, "returned": True}}
    gaps = compute_data_gaps([_NKA], coverage)
    assert gaps == []


def test_not_covered_produces_no_gap() -> None:
    """Source does not cover allergies → neither gap nor stated-none."""
    coverage = {"allergies": {"requested": False, "returned": False}}
    gaps = compute_data_gaps([], coverage)
    assert gaps == []


def test_present_data_produces_no_gap() -> None:
    """Source covers medications and returned records → no gap."""
    coverage = {"medications": {"requested": True, "returned": True}}
    gaps = compute_data_gaps([_MED], coverage)
    assert gaps == []


# ── COVERAGE_TO_FHIR mapping sanity ─────────────────────────────────────────


def test_coverage_to_fhir_mapping_is_complete() -> None:
    """Mapping contains the six primary clinical categories."""
    assert "medications" in COVERAGE_TO_FHIR
    assert "conditions" in COVERAGE_TO_FHIR
    assert "allergies" in COVERAGE_TO_FHIR
    assert "observations" in COVERAGE_TO_FHIR
    assert "procedures" in COVERAGE_TO_FHIR


# ── gap_fhir_types (production routing helper, #87) ───────────────────────────


def test_gap_fhir_types_returns_not_documented_safety_types() -> None:
    """Requested-but-absent categories map to their FHIR type via COVERAGE_TO_FHIR."""
    coverage = {
        "medications": {"requested": True, "returned": True},
        "allergies": {"requested": True, "returned": False},
        "observations": {"requested": True, "returned": False},
    }
    # Only a medication is present; allergies + labs are absent → both are gaps.
    result = gap_fhir_types([_MED], coverage)
    assert result == {"AllergyIntolerance", "Observation"}


def test_gap_fhir_types_excludes_present_categories() -> None:
    """A category with returned data is not a gap."""
    coverage = {"medications": {"requested": True, "returned": True}}
    assert gap_fhir_types([_MED], coverage) == set()


def test_gap_fhir_types_skips_unrequested_category() -> None:
    """A category the source doesn't cover is never a gap (out of scope)."""
    coverage = {"allergies": {"requested": False, "returned": False}}
    assert gap_fhir_types([], coverage) == set()


def test_gap_fhir_types_skips_unknown_category() -> None:
    """A coverage key with no COVERAGE_TO_FHIR mapping is ignored, not crashed on."""
    coverage = {"mystery_category": {"requested": True, "returned": False}}
    assert gap_fhir_types([], coverage) == set()


def test_gap_fhir_types_nka_allergy_is_not_a_gap() -> None:
    """An NKA allergy entry is 'stated_none', not 'not_documented' → not a gap."""
    coverage = {"allergies": {"requested": True, "returned": True}}
    assert gap_fhir_types([_NKA], coverage) == set()
