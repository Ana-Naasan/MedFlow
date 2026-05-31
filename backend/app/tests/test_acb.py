"""Tests for backend.app.knowledge.acb.

Coverage:
  - Known drug lookup + score
  - Total score computation
  - Unknown drug tracked in unresolved
  - Mixed known + unknown
  - Case-insensitive matching
  - Empty drug list
  - Age enrichment: score-3 label gets ≥65 rider when age_years ≥ 65
  - No enrichment for age_years < 65 or age_years None
  - Snippet id / kind / ref fields
  - Total-score snippet present when score > 0
  - Smoke: 82-year-old with amitriptyline + hydroxyzine → total 6
"""

import pytest

import backend.app.knowledge.acb as _acb_mod
from backend.app.knowledge.acb import AcbMatch, AcbResult, lookup_acb


@pytest.fixture(autouse=True)
def _reset_index() -> None:
    """Clear cached index between tests."""
    _acb_mod._INDEX = None


# ── Lookup behaviour ───────────────────────────────────────────────────────


class TestAcbLookup:
    def test_score_3_drug_matched(self) -> None:
        result = lookup_acb(["amitriptyline"])
        assert any(m.drug_name == "amitriptyline" and m.acb_score == 3 for m in result.matches)

    def test_score_1_drug_matched(self) -> None:
        result = lookup_acb(["alprazolam"])
        assert any(m.acb_score == 1 for m in result.matches)

    def test_score_2_drug_matched(self) -> None:
        result = lookup_acb(["atenolol"])
        assert any(m.acb_score == 2 for m in result.matches)

    def test_total_score_single_drug(self) -> None:
        result = lookup_acb(["amitriptyline"])
        assert result.total_score == 3

    def test_total_score_multiple_drugs(self) -> None:
        # amitriptyline (3) + hydroxyzine (3) = 6
        result = lookup_acb(["amitriptyline", "hydroxyzine"])
        assert result.total_score == 6

    def test_empty_list_returns_zero(self) -> None:
        result = lookup_acb([])
        assert result.total_score == 0
        assert result.matches == []
        assert result.unresolved == []

    def test_match_is_acb_match_type(self) -> None:
        result = lookup_acb(["amitriptyline"])
        for m in result.matches:
            assert isinstance(m, AcbMatch)

    def test_case_insensitive_match(self) -> None:
        result = lookup_acb(["Amitriptyline"])
        assert any(m.drug_name == "amitriptyline" for m in result.matches)


# ── Unresolved ─────────────────────────────────────────────────────────────


class TestAcbUnresolved:
    def test_unknown_drug_in_unresolved(self) -> None:
        result = lookup_acb(["zyzzyva_unknown_drug"])
        assert "zyzzyva_unknown_drug" in result.unresolved
        assert result.matches == []
        assert result.total_score == 0

    def test_mixed_known_and_unknown(self) -> None:
        result = lookup_acb(["amitriptyline", "zyzzyva_unknown_drug"])
        assert any(m.drug_name == "amitriptyline" for m in result.matches)
        assert "zyzzyva_unknown_drug" in result.unresolved


# ── Age enrichment ─────────────────────────────────────────────────────────


class TestAcbAgeEnrichment:
    def test_no_age_no_enrichment(self) -> None:
        result = lookup_acb(["amitriptyline"], age_years=None)
        label = result.matches[0].snippet.label
        assert "≥65" not in label

    def test_age_65_enriches_score3_label(self) -> None:
        result = lookup_acb(["amitriptyline"], age_years=65)
        label = result.matches[0].snippet.label
        assert "≥65" in label

    def test_age_under_65_no_enrichment(self) -> None:
        result = lookup_acb(["amitriptyline"], age_years=50)
        label = result.matches[0].snippet.label
        assert "≥65" not in label

    def test_score_1_no_enrichment_even_at_65(self) -> None:
        # Only score-3 gets the ≥65 rider.
        result = lookup_acb(["alprazolam"], age_years=82)
        label = result.matches[0].snippet.label
        assert "≥65" not in label


# ── Snippet shape ──────────────────────────────────────────────────────────


class TestAcbSnippets:
    def test_per_drug_snippet_id_format(self) -> None:
        result = lookup_acb(["amitriptyline"])
        ids = {s.id for s in result.snippets if s.kind == "acb_score"}
        assert "acb:amitriptyline:score_3" in ids

    def test_per_drug_snippet_kind(self) -> None:
        result = lookup_acb(["amitriptyline"])
        for m in result.matches:
            assert m.snippet.kind == "acb_score"

    def test_per_drug_snippet_ref_is_citation(self) -> None:
        result = lookup_acb(["amitriptyline"])
        for m in result.matches:
            assert m.snippet.ref  # non-empty citation string

    def test_total_snippet_present_when_score_positive(self) -> None:
        result = lookup_acb(["amitriptyline"])
        total_snippets = [s for s in result.snippets if s.kind == "acb_total"]
        assert len(total_snippets) == 1

    def test_total_snippet_absent_when_no_matches(self) -> None:
        result = lookup_acb(["zyzzyva_unknown_drug"])
        total_snippets = [s for s in result.snippets if s.kind == "acb_total"]
        assert total_snippets == []

    def test_total_snippet_id_contains_sorted_names(self) -> None:
        result = lookup_acb(["amitriptyline", "hydroxyzine"])
        total = next(s for s in result.snippets if s.kind == "acb_total")
        # sorted: amitriptyline < hydroxyzine
        assert "amitriptyline,hydroxyzine" in total.id


# ── Smoke test ─────────────────────────────────────────────────────────────


class TestAcbSmoke:
    def test_82yo_amitriptyline_hydroxyzine_total_6(self) -> None:
        result = lookup_acb(["amitriptyline", "hydroxyzine"], age_years=82)
        assert result.total_score == 6

    def test_82yo_result_is_acb_result(self) -> None:
        result = lookup_acb(["amitriptyline"], age_years=82)
        assert isinstance(result, AcbResult)

    def test_82yo_score3_label_has_enrichment(self) -> None:
        result = lookup_acb(["amitriptyline"], age_years=82)
        ami = next(m for m in result.matches if m.drug_name == "amitriptyline")
        assert "≥65" in ami.snippet.label
