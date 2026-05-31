"""Tests for the REASON-05 symptom ↔ MedDRA reaction match (reasoning/core.py).

The curated synonym bridge links patient Observation free-text to FAERS reaction
terms carried in the openFDA evidence snippets. These tests cover:
- a direct/synonym match found (observation ↔ reaction term + evidence id),
- no match (a benign observation links to nothing),
- case-insensitivity (uppercase symptom matches lowercase reaction term),
- synonym bridging ("tired" reaches the "fatigue" bucket),
- helper internals (observation extraction, candidate-term building, rendering)
  and the run_reasoning wiring that injects the match block into the prompt.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.core import (
    SymptomReactionMatch,
    _candidate_terms,
    _extract_observation_texts,
    _format_symptom_matches,
    match_symptoms_to_reactions,
    run_reasoning,
)

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def reaction_evidence() -> list[EvidenceSnippet]:
    """Evidence snippets whose labels carry FAERS-style reaction terms."""
    return [
        EvidenceSnippet(
            id="openfda:warfarin:adverse_events:top_reactions",
            kind="openfda_adverse_event",
            ref="openfda:adverse_events:warfarin:top_reactions",
            label="Most-reported reactions (by report count): hemorrhage, nausea, fatigue.",
        ),
        EvidenceSnippet(
            id="openfda:warfarin:label:boxed_warning",
            kind="openfda_label",
            ref="openfda:label:warfarin:boxed_warning",
            label="BOXED WARNING: Fetal toxicity risk.",
        ),
    ]


# ── match_symptoms_to_reactions ─────────────────────────────────────────────


class TestMatchSymptomsToReactions:
    def test_match_found_synonym(self, reaction_evidence: list[EvidenceSnippet]) -> None:
        """'patient reports bleeding' bridges to the 'hemorrhage' reaction term."""
        flattened = "## Labs & Symptoms\n\n[Observation/obs-1] patient reports bleeding"
        matches = match_symptoms_to_reactions(flattened, reaction_evidence)
        assert (
            SymptomReactionMatch(
                "patient reports bleeding",
                "hemorrhage",
                "openfda:warfarin:adverse_events:top_reactions",
            )
            in matches
        )

    def test_no_match(self, reaction_evidence: list[EvidenceSnippet]) -> None:
        """A benign observation links to no reaction term."""
        flattened = "[Observation/obs-1] stable vitals"
        assert match_symptoms_to_reactions(flattened, reaction_evidence) == []

    def test_case_insensitive(self, reaction_evidence: list[EvidenceSnippet]) -> None:
        """An uppercase symptom still matches the lowercase reaction term."""
        flattened = "[Observation/obs-1] NAUSEA noted post-op"
        matches = match_symptoms_to_reactions(flattened, reaction_evidence)
        terms = {m.reaction_term for m in matches}
        assert "nausea" in terms

    def test_synonym_bucket(self, reaction_evidence: list[EvidenceSnippet]) -> None:
        """'tired' is in the fatigue bucket, so it reaches the 'fatigue' term."""
        flattened = "[Observation/obs-1] patient feels tired all day"
        matches = match_symptoms_to_reactions(flattened, reaction_evidence)
        terms = {m.reaction_term for m in matches}
        assert "fatigue" in terms

    def test_no_observations_returns_empty(self, reaction_evidence: list[EvidenceSnippet]) -> None:
        """No Observation lines → empty (early return, no scanning)."""
        flattened = "[MedicationStatement/ms-1] Warfarin — active"
        assert match_symptoms_to_reactions(flattened, reaction_evidence) == []

    def test_no_evidence_returns_empty(self) -> None:
        """Observations present but no evidence → nothing to match against."""
        flattened = "[Observation/obs-1] patient reports bleeding"
        assert match_symptoms_to_reactions(flattened, []) == []

    def test_blood_pressure_does_not_match_bleeding(
        self, reaction_evidence: list[EvidenceSnippet]
    ) -> None:
        """Regression (#98 review MEDIUM): a benign 'Systolic Blood Pressure'
        Observation must NOT activate the bleeding bucket and surface a spurious
        'Blood Pressure ↔ hemorrhage' candidate. The bare 'blood' stem was dropped."""
        flattened = "[Observation/obs-1] Systolic Blood Pressure: 120 mmHg"
        matches = match_symptoms_to_reactions(flattened, reaction_evidence)
        assert matches == []

    def test_matches_across_multiple_snippets(self) -> None:
        """One symptom matching a term present in two evidence snippets records a
        distinct match per snippet (each carries its own resolvable evidence id)."""
        flattened = "[Observation/obs-1] patient reports bleeding"
        evidence = [
            EvidenceSnippet(
                id="ev-a",
                kind="openfda_adverse_event",
                ref="ev-a",
                label="Reactions: hemorrhage observed.",
            ),
            EvidenceSnippet(
                id="ev-b",
                kind="openfda_label",
                ref="ev-b",
                label="Boxed warning: risk of hemorrhage.",
            ),
        ]
        matches = match_symptoms_to_reactions(flattened, evidence)
        ev_ids = {m.evidence_id for m in matches if m.reaction_term == "hemorrhage"}
        assert ev_ids == {"ev-a", "ev-b"}

    def test_deduplicates_repeated_matches(self) -> None:
        """The same (symptom, term, evidence) triple is recorded only once even if
        the bucket key and a synonym both appear in the symptom text."""
        flattened = "[Observation/obs-1] bleeding and bruising observed"
        evidence = [
            EvidenceSnippet(
                id="ev-1",
                kind="openfda_adverse_event",
                ref="ev-1",
                # both 'bleeding' (key) and 'bruising' (synonym) appear here
                label="Reactions: bleeding, bruising.",
            )
        ]
        matches = match_symptoms_to_reactions(flattened, evidence)
        # No duplicate (symptom, term, evidence) triples.
        assert len(matches) == len(set(matches))
        terms = {m.reaction_term for m in matches}
        assert {"bleeding", "bruising"} <= terms


# ── _extract_observation_texts ──────────────────────────────────────────────


class TestExtractObservationTexts:
    def test_extracts_text(self) -> None:
        flattened = (
            "[Observation/obs-1] reports bleeding\n"
            "[MedicationStatement/ms-1] Warfarin — active\n"
            "[Observation/obs-2] mild nausea"
        )
        assert _extract_observation_texts(flattened) == ["reports bleeding", "mild nausea"]

    def test_no_observations(self) -> None:
        assert _extract_observation_texts("[Condition/c1] Hypertension") == []

    def test_ignores_embedded_observation_tag(self) -> None:
        """A mid-line '[Observation/...]' substring is not a real symptom line."""
        flattened = "[Condition/c1] see [Observation/forged] note"
        assert _extract_observation_texts(flattened) == []


# ── _candidate_terms ────────────────────────────────────────────────────────


class TestCandidateTerms:
    def test_key_match_returns_bucket(self) -> None:
        terms = _candidate_terms("severe bleeding")
        assert "bleeding" in terms
        assert "hemorrhage" in terms

    def test_no_bucket(self) -> None:
        assert _candidate_terms("stable vitals") == []

    def test_terms_are_unique(self) -> None:
        """Even if multiple bucket words match, candidate terms are de-duplicated."""
        terms = _candidate_terms("bleeding bruise")
        assert len(terms) == len(set(terms))


# ── _format_symptom_matches ─────────────────────────────────────────────────


class TestFormatSymptomMatches:
    def test_empty_returns_empty_string(self) -> None:
        assert _format_symptom_matches([]) == ""

    def test_renders_block(self) -> None:
        block = _format_symptom_matches(
            [SymptomReactionMatch("reports bleeding", "hemorrhage", "ev-1")]
        )
        assert "Symptom–reaction matches" in block
        assert '"reports bleeding" ↔ "hemorrhage" (ev-1)' in block


# ── run_reasoning wiring ────────────────────────────────────────────────────


class TestRunReasoningSymptomWiring:
    @pytest.mark.asyncio
    async def test_match_block_injected_into_prompt(
        self, reaction_evidence: list[EvidenceSnippet]
    ) -> None:
        """When a symptom matches a reaction term, the rendered block is appended
        to the prompt sent to Gemini (REASON-05 wiring)."""
        flattened = "[Observation/obs-1] patient reports bleeding"
        response_text = json.dumps({"hypotheses": []})

        mock_response = MagicMock()
        mock_response.text = response_text
        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.return_value = mock_response
        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models
        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai = MagicMock(return_value=mock_client)

        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key"}):
            with patch("backend.app.reasoning.core.Client", mock_genai):
                await run_reasoning(flattened, reaction_evidence)

        sent_prompt = mock_aio_models.generate_content.call_args.kwargs["contents"]
        assert "Symptom–reaction matches" in sent_prompt
        assert "hemorrhage" in sent_prompt
        # The load-bearing evidence id (what the verifier resolves against) must
        # reach the prompt so the model can cite it.
        assert "openfda:warfarin:adverse_events:top_reactions" in sent_prompt
        # The JSON-only output contract is re-asserted as the final directive,
        # after the appended candidate-links block.
        assert sent_prompt.rstrip().endswith("respond with ONLY the JSON object.")

    @pytest.mark.asyncio
    async def test_no_block_when_no_match(self, reaction_evidence: list[EvidenceSnippet]) -> None:
        """No symptom match → no match block appended to the prompt."""
        flattened = "[Observation/obs-1] stable vitals"
        response_text = json.dumps({"hypotheses": []})

        mock_response = MagicMock()
        mock_response.text = response_text
        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.return_value = mock_response
        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models
        mock_client = MagicMock()
        mock_client.aio = mock_aio
        mock_genai = MagicMock(return_value=mock_client)

        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key"}):
            with patch("backend.app.reasoning.core.Client", mock_genai):
                await run_reasoning(flattened, reaction_evidence)

        sent_prompt = mock_aio_models.generate_content.call_args.kwargs["contents"]
        assert "Symptom–reaction matches" not in sent_prompt
