"""Tests for reasoning/core.py — Gemini call, response parsing, citation verification.

Edge cases and input-validation patterns:
- Empty / malformed / non-dict / non-list responses → ``ValueError``
- Non-dict entries in hypotheses list → silently skipped
- Unknown citation kinds left as-is
- Every patient-fact ref must exist in the flattened text
- Every evidence-card ref must match a known snippet ID
- ``run_reasoning`` golden path with a mocked Gemini response
"""

import json
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from backend.app.dtos import Citation, Hypothesis
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.core import (
    _extract_patient_tags,
    _get_client,
    parse_gemini_response,
    run_reasoning,
    verify_citations,
)

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_flattened_text() -> str:
    return (
        "## Medications\n\n"
        "[MedicationStatement/ms-001] Lisinopril 10 MG — active\n"
        "[MedicationStatement/ms-002] Metformin 500 MG — active\n\n"
        "## Conditions\n\n"
        "[Condition/c1] Hypertension — active, confirmed\n\n"
        "## Allergies\n\n"
        "_(not documented)_"
    )


@pytest.fixture
def sample_evidence_snippets() -> list[EvidenceSnippet]:
    return [
        EvidenceSnippet(
            id="openfda:197885:adverse_events:total_count",
            kind="openfda_adverse_event",
            ref="openfda:adverse_events:197885:total_count",
            label="10,064 adverse events reported for lisinopril.",
        ),
        EvidenceSnippet(
            id="openfda:197885:label:boxed_warning",
            kind="openfda_label",
            ref="openfda:label:197885:boxed_warning",
            label="BOXED WARNING: Fetal toxicity...",
        ),
    ]


@pytest.fixture
def sample_valid_hypotheses() -> list[Hypothesis]:
    return [
        Hypothesis(
            id="hyp-1",
            title="Lisinopril may contribute to hypotension",
            why="The patient has hypertension but is on lisinopril which can cause hypotension in salt-depleted patients.",
            severity="moderate",
            confidence="medium",
            citations=[
                Citation(
                    kind="patient_fact",
                    ref="[MedicationStatement/ms-001]",
                    label="Lisinopril prescription",
                ),
                Citation(
                    kind="patient_fact",
                    ref="[Condition/c1]",
                    label="Hypertension diagnosis",
                ),
                Citation(
                    kind="evidence_card",
                    ref="openfda:197885:adverse_events:total_count",
                    label="10,064 adverse events reported",
                ),
            ],
        ),
    ]


# ── _extract_patient_tags ──────────────────────────────────────────────────


class TestExtractPatientTags:
    def test_extracts_all_tags(self, sample_flattened_text: str) -> None:
        tags = _extract_patient_tags(sample_flattened_text)
        assert "[MedicationStatement/ms-001]" in tags
        assert "[MedicationStatement/ms-002]" in tags
        assert "[Condition/c1]" in tags

    def test_no_tags(self) -> None:
        assert _extract_patient_tags("_(not documented)_") == set()

    def test_empty_string(self) -> None:
        assert _extract_patient_tags("") == set()

    def test_deduplicates_duplicate_tags(self) -> None:
        text = "[Patient/p1] foo\n[Patient/p1] bar"
        assert _extract_patient_tags(text) == {"[Patient/p1]"}

    def test_tag_with_special_chars(self) -> None:
        """Tags can contain dots, hyphens, underscores, colons."""
        text = "[Observation/obs-001.a] test [Procedure/proc_002:b]"
        tags = _extract_patient_tags(text)
        assert "[Observation/obs-001.a]" in tags
        assert "[Procedure/proc_002:b]" in tags


# ── parse_gemini_response ──────────────────────────────────────────────────


class TestParseGeminiResponse:
    def test_happy_path(self) -> None:
        response = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Test link",
                        "why": "Because X and Y",
                        "severity": "serious",
                        "confidence": "high",
                        "citations": [
                            {
                                "kind": "patient_fact",
                                "ref": "[MedicationStatement/ms-001]",
                                "label": "Lisinopril",
                            }
                        ],
                    }
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert len(hypotheses) == 1
        h = hypotheses[0]
        assert h.id == "hyp-1"
        assert h.title == "Test link"
        assert h.why == "Because X and Y"
        assert h.severity == "serious"
        assert h.confidence == "high"
        assert len(h.citations) == 1
        assert h.citations[0].ref == "[MedicationStatement/ms-001]"

    def test_empty_hypotheses(self) -> None:
        hypotheses = parse_gemini_response('{"hypotheses": []}')
        assert hypotheses == []

    def test_empty_response_raises(self) -> None:
        with pytest.raises(ValueError, match="empty response"):
            parse_gemini_response("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty response"):
            parse_gemini_response("   \n\n  ")

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(ValueError, match="malformed JSON"):
            parse_gemini_response("{broken json}")

    def test_non_dict_top_level_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected JSON object"):
            parse_gemini_response('"just a string"')

    def test_hypotheses_not_a_list_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected 'hypotheses' to be a list"):
            parse_gemini_response('{"hypotheses": "not-a-list"}')

    def test_non_dict_hypothesis_skipped(self) -> None:
        response = json.dumps(
            {
                "hypotheses": [
                    "just a string",
                    {"title": "Valid one", "why": "reason", "severity": "minor", "confidence": "low"},
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert len(hypotheses) == 1
        assert hypotheses[0].title == "Valid one"

    def test_missing_citations_field(self) -> None:
        response = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "No citations",
                        "why": "reason",
                        "severity": "moderate",
                        "confidence": "low",
                    }
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert len(hypotheses) == 1
        assert hypotheses[0].citations == []

    def test_non_dict_citation_skipped(self) -> None:
        response = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Test",
                        "why": "reason",
                        "severity": "minor",
                        "confidence": "low",
                        "citations": ["not-a-dict", {"kind": "patient_fact", "ref": "[Test/t1]"}],
                    }
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert len(hypotheses) == 1
        assert len(hypotheses[0].citations) == 1
        assert hypotheses[0].citations[0].ref == "[Test/t1]"

    def test_default_severity_and_confidence(self) -> None:
        response = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Defaults",
                        "why": "test",
                    }
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert hypotheses[0].severity == "moderate"
        assert hypotheses[0].confidence == "low"


# ── verify_citations ───────────────────────────────────────────────────────


class TestVerifyCitations:
    def test_valid_hypothesis_survives(
        self, sample_flattened_text: str, sample_valid_hypotheses: list[Hypothesis]
    ) -> None:
        evidence_ids = {"openfda:197885:adverse_events:total_count"}
        result = verify_citations(
            sample_valid_hypotheses, sample_flattened_text, evidence_ids
        )
        assert len(result) == 1

    def test_drops_when_patient_fact_missing(
        self, sample_flattened_text: str
    ) -> None:
        h = Hypothesis(
            id="hyp-1",
            title="Test",
            why="reason",
            severity="minor",
            confidence="low",
            citations=[
                Citation(
                    kind="patient_fact",
                    ref="[NonExistent/xyz]",
                    label="Missing",
                )
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 0

    def test_drops_when_evidence_card_missing(
        self, sample_flattened_text: str, sample_valid_hypotheses: list[Hypothesis]
    ) -> None:
        result = verify_citations(
            sample_valid_hypotheses, sample_flattened_text, set()
        )
        assert len(result) == 0

    def test_unknown_citation_kind_preserved(
        self, sample_flattened_text: str
    ) -> None:
        h = Hypothesis(
            id="hyp-1",
            title="Test",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[
                Citation(
                    kind="unknown_type",
                    ref="some-ref",
                    label="Should be kept",
                )
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 1

    def test_empty_hypotheses(self, sample_flattened_text: str) -> None:
        result = verify_citations([], sample_flattened_text, set())
        assert result == []

    def test_drops_when_any_citation_fails(
        self, sample_flattened_text: str
    ) -> None:
        """If one citation is invalid, the whole hypothesis is dropped."""
        h = Hypothesis(
            id="hyp-1",
            title="Mixed valid and invalid",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[
                Citation(
                    kind="patient_fact",
                    ref="[MedicationStatement/ms-001]",
                    label="Exists",
                ),
                Citation(
                    kind="patient_fact",
                    ref="[FakeResource/xyz]",
                    label="Does not exist",
                ),
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 0


# ── _get_client ────────────────────────────────────────────────────────────


class TestGetClient:
    def test_client_created_with_api_key(self) -> None:
        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key-123"}):
            client = _get_client()
            assert client._api_client.api_key == "test-key-123"

    def test_missing_key_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(KeyError, match="GOOGLE_GENAI_API_KEY"):
                _get_client()


# ── run_reasoning (golden path with mocked Gemini) ─────────────────────────


class TestRunReasoning:
    @pytest.mark.asyncio
    async def test_golden_path(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """Happy path: mocked Gemini returns a valid response, verifier passes."""
        response_text = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Lisinopril hypotension risk",
                        "why": "Patient on lisinopril with hypertension.",
                        "severity": "moderate",
                        "confidence": "medium",
                        "citations": [
                            {
                                "kind": "patient_fact",
                                "ref": "[MedicationStatement/ms-001]",
                                "label": "Lisinopril",
                            },
                            {
                                "kind": "evidence_card",
                                "ref": "openfda:197885:adverse_events:total_count",
                                "label": "10,064 events",
                            },
                        ],
                    }
                ]
            }
        )

        # Create mock async client
        mock_response = MagicMock()
        mock_response.text = response_text

        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.return_value = mock_response

        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models

        mock_client = MagicMock()
        mock_client.aio = mock_aio

        mock_genai = MagicMock()
        mock_genai.return_value = mock_client

        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key"}):
            with patch("backend.app.reasoning.core.Client", mock_genai):
                hypotheses = await run_reasoning(
                    sample_flattened_text, sample_evidence_snippets
                )

        assert len(hypotheses) == 1
        h = hypotheses[0]
        assert h.title == "Lisinopril hypotension risk"
        assert h.severity == "moderate"
        assert h.confidence == "medium"
        assert len(h.citations) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_hypotheses_survive_verification(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """Gemini returns citations to non-existent resources → verifier drops all."""
        response_text = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Fake link",
                        "why": "reason",
                        "severity": "moderate",
                        "confidence": "low",
                        "citations": [
                            {
                                "kind": "patient_fact",
                                "ref": "[NonExistent/xyz]",
                                "label": "Fake",
                            }
                        ],
                    }
                ]
            }
        )

        mock_response = MagicMock()
        mock_response.text = response_text

        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.return_value = mock_response

        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models

        mock_client = MagicMock()
        mock_client.aio = mock_aio

        mock_genai = MagicMock()
        mock_genai.return_value = mock_client

        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key"}):
            with patch("backend.app.reasoning.core.Client", mock_genai):
                hypotheses = await run_reasoning(
                    sample_flattened_text, sample_evidence_snippets
                )

        assert hypotheses == []

    @pytest.mark.asyncio
    async def test_malformed_gemini_response_raises(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """Malformed JSON from Gemini should propagate as ValueError."""
        mock_response = MagicMock()
        mock_response.text = "{invalid json}"

        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.return_value = mock_response

        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models

        mock_client = MagicMock()
        mock_client.aio = mock_aio

        mock_genai = MagicMock()
        mock_genai.return_value = mock_client

        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key"}):
            with patch("backend.app.reasoning.core.Client", mock_genai):
                with pytest.raises(ValueError, match="malformed JSON"):
                    await run_reasoning(
                        sample_flattened_text, sample_evidence_snippets
                    )
