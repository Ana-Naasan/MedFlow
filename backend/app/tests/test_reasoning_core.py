"""Tests for reasoning/core.py — Gemini call, response parsing, citation verification.

Edge cases and input-validation patterns:
- Empty / malformed / non-dict / non-list responses → ``ValueError``
- Non-dict entries in hypotheses list → silently skipped
- Unknown citation kinds → silently dropped (anti-hallucination)
- Known citation kinds ``"resource"`` / ``"evidence"`` checked against context
- Bare refs (``MedicationStatement/ms-001`` without brackets) resolved
- ``run_reasoning`` wraps API failures as abstention (REASON-08)
- Golden path with a mocked Gemini response
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from google.genai import errors as genai_errors

from backend.app.dtos import Citation, Hypothesis
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.core import (
    _extract_patient_tags,
    _get_client,
    _strip_brackets,
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
def sample_hypothesis() -> Hypothesis:
    """A hypothesis with ``kind='resource'`` and ``kind='evidence'`` citations."""
    return Hypothesis(
        id="hyp-1",
        title="Lisinopril may contribute to hypotension",
        why="Patient on lisinopril with hypertension; lisinopril can cause hypotension.",
        severity="moderate",
        confidence="medium",
        citations=[
            Citation(
                kind="resource",
                ref="MedicationStatement/ms-001",
                label="Lisinopril prescription",
            ),
            Citation(
                kind="resource",
                ref="Condition/c1",
                label="Hypertension diagnosis",
            ),
            Citation(
                kind="evidence",
                ref="openfda:197885:adverse_events:total_count",
                label="10,064 adverse events reported",
            ),
        ],
    )


# ── _strip_brackets ────────────────────────────────────────────────────────


class TestStripBrackets:
    def test_strips_brackets(self) -> None:
        assert _strip_brackets("[Condition/c1]") == "Condition/c1"

    def test_no_brackets(self) -> None:
        assert _strip_brackets("Condition/c1") == "Condition/c1"

    def test_empty_string(self) -> None:
        assert _strip_brackets("") == ""


# ── _extract_patient_tags ──────────────────────────────────────────────────


class TestExtractPatientTags:
    def test_extracts_all_tags(self, sample_flattened_text: str) -> None:
        tags = _extract_patient_tags(sample_flattened_text)
        assert "MedicationStatement/ms-001" in tags
        assert "MedicationStatement/ms-002" in tags
        assert "Condition/c1" in tags

    def test_no_tags(self) -> None:
        assert _extract_patient_tags("_(not documented)_") == set()

    def test_empty_string(self) -> None:
        assert _extract_patient_tags("") == set()

    def test_deduplicates_duplicate_tags(self) -> None:
        text = "[Patient/p1] foo\n[Patient/p1] bar"
        assert _extract_patient_tags(text) == {"Patient/p1"}

    def test_tag_with_special_chars(self) -> None:
        text = "[Observation/obs-001.a] test\n[Procedure/proc_002:b]"
        tags = _extract_patient_tags(text)
        assert "Observation/obs-001.a" in tags
        assert "Procedure/proc_002:b" in tags


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
                                "kind": "resource",
                                "ref": "MedicationStatement/ms-001",
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
        assert h.citations[0].ref == "MedicationStatement/ms-001"

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
                    {
                        "title": "Valid one",
                        "why": "reason",
                        "severity": "minor",
                        "confidence": "low",
                    },
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
                        "citations": [
                            "not-a-dict",
                            {"kind": "resource", "ref": "Test/t1"},
                        ],
                    }
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert len(hypotheses) == 1
        assert len(hypotheses[0].citations) == 1
        assert hypotheses[0].citations[0].ref == "Test/t1"

    def test_citations_null_does_not_crash(self) -> None:
        """citations=null in JSON coalesces to [] (bug #1 fix)."""
        response = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Null citations",
                        "why": "reason",
                        "severity": "moderate",
                        "confidence": "low",
                        "citations": None,
                    }
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert len(hypotheses) == 1
        assert hypotheses[0].citations == []

    def test_citations_string_does_not_crash(self) -> None:
        """citations being a string instead of a list yields empty citations."""
        response = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "String citations",
                        "why": "reason",
                        "severity": "minor",
                        "confidence": "low",
                        "citations": "malicious_string",
                    }
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert len(hypotheses) == 1
        assert hypotheses[0].citations == []

    def test_default_severity_and_confidence(self) -> None:
        response = json.dumps({"hypotheses": [{"title": "Defaults", "why": "test"}]})
        hypotheses = parse_gemini_response(response)
        assert hypotheses[0].severity == "moderate"
        assert hypotheses[0].confidence == "low"


# ── verify_citations ───────────────────────────────────────────────────────


class TestVerifyCitations:
    def test_valid_hypothesis_survives(
        self, sample_flattened_text: str, sample_hypothesis: Hypothesis
    ) -> None:
        evidence_ids = {"openfda:197885:adverse_events:total_count"}
        result = verify_citations([sample_hypothesis], sample_flattened_text, evidence_ids)
        assert len(result) == 1

    def test_drops_when_resource_ref_missing(self, sample_flattened_text: str) -> None:
        h = Hypothesis(
            id="hyp-1",
            title="Test",
            why="reason",
            severity="minor",
            confidence="low",
            citations=[Citation(kind="resource", ref="NonExistent/xyz", label="Missing")],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 0

    def test_drops_when_evidence_ref_missing(
        self, sample_flattened_text: str, sample_hypothesis: Hypothesis
    ) -> None:
        result = verify_citations([sample_hypothesis], sample_flattened_text, set())
        assert len(result) == 0

    def test_unknown_citation_kind_dropped(self, sample_flattened_text: str) -> None:
        h = Hypothesis(
            id="hyp-1",
            title="Test",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[
                Citation(kind="made_up_kind", ref="anything", label="Should be dropped"),
                Citation(kind="resource", ref="Condition/c1", label="Valid"),
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 1
        # The unknown kind should be stripped from the output
        assert all(c.kind in ("resource", "evidence") for c in result[0].citations)

    def test_all_hypotheses_dropped_when_kind_unknown(self, sample_flattened_text: str) -> None:
        """All citations have unknown kinds → no known citations → passes but empty list."""
        h = Hypothesis(
            id="hyp-1",
            title="Test",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[Citation(kind="hallucinated_kind", ref="x", label="y")],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 0

    def test_empty_hypotheses(self, sample_flattened_text: str) -> None:
        result = verify_citations([], sample_flattened_text, set())
        assert result == []

    def test_drops_when_any_citation_fails(self, sample_flattened_text: str) -> None:
        h = Hypothesis(
            id="hyp-1",
            title="Mixed",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[
                Citation(kind="resource", ref="MedicationStatement/ms-001", label="Exists"),
                Citation(kind="resource", ref="FakeResource/xyz", label="Does not exist"),
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 0

    def test_ref_with_brackets_still_matches(self, sample_flattened_text: str) -> None:
        """Bracketed refs are stripped before matching."""
        h = Hypothesis(
            id="hyp-1",
            title="Test",
            why="reason",
            severity="minor",
            confidence="low",
            citations=[
                Citation(
                    kind="resource",
                    ref="[MedicationStatement/ms-001]",
                    label="With brackets",
                )
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 1

    def test_zero_citation_hypothesis_dropped(self, sample_flattened_text: str) -> None:
        """Hypothesis with zero known citations is dropped (bug #2 fix)."""
        h = Hypothesis(
            id="hyp-1",
            title="No citations",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 0

    def test_all_unknown_kinds_dropped(self, sample_flattened_text: str) -> None:
        """Hypothesis with only unknown citation kinds is dropped."""
        h = Hypothesis(
            id="hyp-1",
            title="Unknown kinds only",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[Citation(kind="alien", ref="x", label="y")],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert len(result) == 0


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
                                "kind": "resource",
                                "ref": "MedicationStatement/ms-001",
                                "label": "Lisinopril",
                            },
                            {
                                "kind": "evidence",
                                "ref": "openfda:197885:adverse_events:total_count",
                                "label": "10,064 events",
                            },
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
                hypotheses = await run_reasoning(sample_flattened_text, sample_evidence_snippets)

        assert len(hypotheses) == 1
        h = hypotheses[0]
        assert h.title == "Lisinopril hypotension risk"
        assert len(h.citations) == 2
        assert h.citations[0].kind == "resource"
        assert h.citations[1].kind == "evidence"

    @pytest.mark.asyncio
    async def test_abstention_on_gemini_api_error(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """API errors → REASON-08 abstention: returns empty list."""
        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.side_effect = genai_errors.ClientError(
            429, {}, MagicMock()
        )

        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models

        mock_client = MagicMock()
        mock_client.aio = mock_aio

        mock_genai = MagicMock()
        mock_genai.return_value = mock_client

        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key"}):
            with patch("backend.app.reasoning.core.Client", mock_genai):
                hypotheses = await run_reasoning(sample_flattened_text, sample_evidence_snippets)

        assert hypotheses == []

    @pytest.mark.asyncio
    async def test_abstention_on_gemini_5xx(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """Gemini 5xx (ServerError) → REASON-08 abstention."""
        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.side_effect = genai_errors.ServerError(
            503, {}, MagicMock()
        )

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
    async def test_abstention_on_httpx_error(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """Network errors → REASON-08 abstention."""
        mock_aio_models = AsyncMock()
        mock_aio_models.generate_content.side_effect = httpx.RequestError("network")

        mock_aio = MagicMock()
        mock_aio.models = mock_aio_models

        mock_client = MagicMock()
        mock_client.aio = mock_aio

        mock_genai = MagicMock()
        mock_genai.return_value = mock_client

        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key"}):
            with patch("backend.app.reasoning.core.Client", mock_genai):
                hypotheses = await run_reasoning(sample_flattened_text, sample_evidence_snippets)

        assert hypotheses == []

    @pytest.mark.asyncio
    async def test_abstention_on_malformed_json_from_gemini(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """Malformed JSON from Gemini → empty list (not a crash)."""
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
                hypotheses = await run_reasoning(sample_flattened_text, sample_evidence_snippets)

        assert hypotheses == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_hypotheses_survive_verification(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """Gemini returns citations that fail verification → empty result."""
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
                                "kind": "resource",
                                "ref": "NonExistent/xyz",
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
                hypotheses = await run_reasoning(sample_flattened_text, sample_evidence_snippets)

        assert hypotheses == []
