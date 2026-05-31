"""Tests for backend.app.knowledge.beers.

Coverage:
  - Age gate (< 65 → empty, exactly 65 → matches, > 65 → matches)
  - Known-drug lookup + snippet shape
  - Unknown drug tracked in unresolved
  - Mixed known + unknown
  - Case-insensitive matching
  - Drug appearing in multiple rules (diphenhydramine → anticholinergic + sleep)
  - Snippet id / kind / ref fields
  - Age gate does NOT populate unresolved
  - Smoke: 82-year-old with amitriptyline → "Avoid"
"""

import pytest

import backend.app.knowledge.beers as _beers_mod
from backend.app.knowledge.beers import BeersMatch, BeersResult, lookup_beers


@pytest.fixture(autouse=True)
def _reset_index() -> None:
    """Clear cached index between tests so mutations don't bleed."""
    _beers_mod._INDEX = None


# ── Age gating ─────────────────────────────────────────────────────────────


class TestBeersAgeGate:
    def test_age_under_65_returns_empty(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=64)
        assert result.matches == []
        assert result.snippets == []

    def test_age_under_65_unresolved_is_empty(self) -> None:
        # Age gate fires before resolution; unresolved must NOT be populated.
        result = lookup_beers(["amitriptyline"], age_years=50)
        assert result.unresolved == []

    def test_age_exactly_65_returns_match(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=65)
        assert len(result.matches) >= 1

    def test_age_above_65_returns_match(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=82)
        assert len(result.matches) >= 1


# ── Lookup behaviour ───────────────────────────────────────────────────────


class TestBeersLookup:
    def test_known_drug_produces_match(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        assert any(m.drug_name == "amitriptyline" for m in result.matches)

    def test_match_is_beers_match_type(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        for m in result.matches:
            assert isinstance(m, BeersMatch)

    def test_unknown_drug_in_unresolved(self) -> None:
        result = lookup_beers(["zyzzyva_unknown_drug"], age_years=70)
        assert "zyzzyva_unknown_drug" in result.unresolved
        assert result.matches == []

    def test_mixed_known_and_unknown(self) -> None:
        result = lookup_beers(["amitriptyline", "zyzzyva_unknown_drug"], age_years=70)
        assert any(m.drug_name == "amitriptyline" for m in result.matches)
        assert "zyzzyva_unknown_drug" in result.unresolved

    def test_case_insensitive_match(self) -> None:
        result = lookup_beers(["Amitriptyline"], age_years=70)
        assert any(m.drug_name == "amitriptyline" for m in result.matches)

    def test_empty_drug_list_returns_empty(self) -> None:
        result = lookup_beers([], age_years=70)
        assert result.matches == []
        assert result.unresolved == []

    def test_drug_in_multiple_rules(self) -> None:
        # "diphenhydramine (oral)" appears in anticholinergic-01 AND sleep-01.
        result = lookup_beers(["diphenhydramine"], age_years=70)
        matched_rule_ids = {m.rule_id for m in result.matches}
        assert "beers-2023-anticholinergic-01" in matched_rule_ids
        assert "beers-2023-sleep-01" in matched_rule_ids

    def test_parenthetical_stripped_for_match(self) -> None:
        # Seed has "diphenhydramine (oral)"; patient sends "diphenhydramine".
        result = lookup_beers(["diphenhydramine"], age_years=70)
        assert any(m.drug_name == "diphenhydramine" for m in result.matches)

    def test_match_has_recommendation(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        for m in result.matches:
            assert m.recommendation in {"Avoid", "Use with caution"}

    def test_match_has_rationale(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        for m in result.matches:
            assert m.rationale


# ── Snippet shape ──────────────────────────────────────────────────────────


class TestBeersSnippets:
    def test_snippet_id_format(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        for m in result.matches:
            assert m.snippet.id.startswith("beers:beers-2023-")
            assert ":amitriptyline" in m.snippet.id

    def test_snippet_kind(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        for m in result.matches:
            assert m.snippet.kind == "beers_criteria"

    def test_snippet_ref_is_citation_string(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        for m in result.matches:
            assert "Beers" in m.snippet.ref or "Geriatrics" in m.snippet.ref

    def test_snippets_list_matches_match_snippets(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=70)
        snippet_ids = {s.id for s in result.snippets}
        for m in result.matches:
            assert m.snippet.id in snippet_ids


# ── Smoke test ─────────────────────────────────────────────────────────────


class TestBeers82YoSmoke:
    def test_82yo_amitriptyline_produces_avoid(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=82)
        recs = {m.recommendation for m in result.matches}
        assert "Avoid" in recs, f"Expected 'Avoid' in recommendations, got {recs}"

    def test_82yo_result_is_beers_result(self) -> None:
        result = lookup_beers(["amitriptyline"], age_years=82)
        assert isinstance(result, BeersResult)
