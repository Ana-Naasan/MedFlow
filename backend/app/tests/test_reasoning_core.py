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
    _has_forbidden_language,
    _strip_brackets,
    derive_confidence_tier,
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

    def test_ignores_tag_embedded_in_free_text(self) -> None:
        """Forged-citation defence: a [Type/id] substring inside a rendered
        value (mid-line, source-controlled) must NOT count as a patient tag —
        only the line-leading tag the flattener actually emits."""
        text = "[Observation/obs-1] note saying see [Condition/forged-injected] here"
        tags = _extract_patient_tags(text)
        assert tags == {"Observation/obs-1"}
        assert "Condition/forged-injected" not in tags


# ── _has_forbidden_language (output-language guard) ─────────────────────────


class TestForbiddenLanguage:
    @pytest.mark.parametrize(
        "title,why",
        [
            # Existing canonical violations (causal + direct directive):
            ("", "The bleeding was caused by warfarin."),
            ("", "Discontinue the aspirin."),
            ("", "Consider whether to stop taking metformin."),
            ("Patient must stop lisinopril", ""),
            ("", "Warfarin causes bleeding."),
            ("", "The bleeding was due to warfarin."),
            ("The patient must start warfarin", ""),
            # #75 broadening — recommendation-form directives:
            ("", "We recommend stopping the warfarin."),
            ("", "Clinician recommends discontinuing the aspirin."),
            ("", "Recommended starting a statin."),
            ("", "Recommending switching to a safer alternative."),
            # #75 broadening — should + verbed-directive:
            ("", "Patient should stop the warfarin."),
            ("", "Should discontinue the offending agent."),
            ("Should start anticoagulation", ""),
            ("", "Patient should switch to a safer agent."),
            # #75 broadening — should-not directives:
            ("", "Patient should not take aspirin."),
            ("", "Patient should not use NSAIDs concurrently."),
            ("", "Patient should not continue warfarin without monitoring."),
            ("", "Patient should not start a new SSRI here."),
            # #75 broadening — advise directives:
            ("", "We advise against the combination."),
            ("", "Strongly advise stopping the medication."),
            ("", "Advise starting an alternative."),
            # #75 broadening — dose directives:
            ("", "Increase the dose to compensate."),
            ("", "Decrease the dose by half."),
            ("", "Reduce the frequency to once daily."),
        ],
    )
    def test_flags_causal_and_directive_language(self, title: str, why: str) -> None:
        h = Hypothesis(id="h", title=title, why=why, severity="moderate", confidence="low")
        assert _has_forbidden_language(h) is True

    @pytest.mark.parametrize(
        "why",
        [
            # Canonical associational forms must keep passing:
            "Warfarin and aspirin together may be associated with an increased bleeding risk.",
            "This combination is associated with a higher fall risk — consider reviewing.",
            "No specific concern; documentation is incomplete.",
            # #75 broadening — must NOT regress on these:
            # bare "increase"/"decrease"/"reduce" without "the dose":
            "The combination may lead to an increased risk of bleeding.",
            "An increase in INR was noted in the chart.",
            "Decreased renal function may amplify the effect.",
            "There is a reduced clearance of the drug in this patient.",
            # bare "stop"/"start" outside the verbed directives:
            "Symptoms reportedly stop within an hour of dosing.",
            "The start of symptoms preceded the prescription by one week.",
            # bare "cause" (the noun) — only "caused by"/"causes" (the verb
            # form ending in -s) are flagged:
            "The cause is unclear from the documented history.",
            # NOTE: "Multiple contributing causes may be at play." would false-
            # positive against \bcauses\b (noun plural). The conservative #79
            # set accepted that tradeoff — distinguishing verb-causes from
            # noun-causes deterministically needs the per-clause grounding
            # work (#75 follow-up).
            # "consider" without a directive verb is fine:
            "Consider reviewing the patient's allergy history.",
            "Worth considering whether the lab gap is material here.",
        ],
    )
    def test_allows_associational_language(self, why: str) -> None:
        """Must NOT false-positive on valid associational / observational text.

        This is the #75 curation invariant: the conservative phrase set may grow
        but must never start flagging legit clinical-reasoning prose.
        """
        h = Hypothesis(
            id="h", title="Bleeding risk", why=why, severity="moderate", confidence="low"
        )
        assert _has_forbidden_language(h) is False


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

    def test_one_malformed_hypothesis_drops_only_itself(self) -> None:
        """LLM drift: a single hypothesis with a non-string field (severity=null)
        must drop only ITSELF, not the whole batch — the valid, citable ones
        still survive parsing. Fails closed without nuking the decision packet."""
        response = json.dumps(
            {
                "hypotheses": [
                    {"title": "Good A", "why": "x", "severity": "moderate", "confidence": "low"},
                    {"title": "Bad", "why": "x", "severity": None, "confidence": "low"},
                    {"title": "Good B", "why": "y", "severity": "serious", "confidence": "high"},
                ]
            }
        )
        hypotheses = parse_gemini_response(response)
        assert [h.title for h in hypotheses] == ["Good A", "Good B"]

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

    def test_unknown_citation_kind_taints_whole_hypothesis(
        self, sample_flattened_text: str
    ) -> None:
        """Per-clause grounding (#75): an unknown-kind citation alongside valid
        citations now drops the whole hypothesis, instead of being silently
        stripped while the prose survives. Rationale: an unknown/fabricated
        citation is a tell that the free-text ``why``/``title`` may rely on the
        fabricated source — keep none rather than surface a half-grounded entry.
        """
        h = Hypothesis(
            id="hyp-1",
            title="Test",
            why="reason",
            severity="moderate",
            confidence="low",
            citations=[
                Citation(kind="made_up_kind", ref="anything", label="Hallucinated"),
                Citation(kind="resource", ref="Condition/c1", label="Valid"),
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert result == []

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

    # ── #75 per-clause grounding: unknown-kind taints whole hypothesis ──────

    def test_per_clause_grounding_drops_mixed_known_and_unknown_kinds(
        self, sample_flattened_text: str
    ) -> None:
        """Even one unknown-kind citation taints the hypothesis. Two resolvable
        resource refs are NOT enough to keep it — the unknown one might back a
        fabricated claim in the prose."""
        h = Hypothesis(
            id="hyp-1",
            title="Mixed",
            why="...",
            severity="moderate",
            confidence="low",
            citations=[
                Citation(kind="resource", ref="Condition/c1", label="Valid 1"),
                Citation(kind="resource", ref="MedicationStatement/ms-001", label="Valid 2"),
                Citation(kind="hallucinated_guideline", ref="X", label="Fabricated"),
            ],
        )
        result = verify_citations([h], sample_flattened_text, set())
        assert result == []

    def test_per_clause_grounding_preserves_clean_hypotheses_in_same_batch(
        self, sample_flattened_text: str
    ) -> None:
        """A batch with one tainted + one clean hypothesis returns only the
        clean one — the strict gate doesn't poison sibling hypotheses."""
        tainted = Hypothesis(
            id="bad",
            title="bad",
            why="bad",
            severity="moderate",
            confidence="low",
            citations=[
                Citation(kind="resource", ref="Condition/c1", label="Valid"),
                Citation(kind="made_up", ref="x", label="Hallucinated"),
            ],
        )
        clean = Hypothesis(
            id="good",
            title="good",
            why="good",
            severity="moderate",
            confidence="low",
            citations=[Citation(kind="resource", ref="Condition/c1", label="Valid")],
        )
        result = verify_citations([tainted, clean], sample_flattened_text, set())
        assert [h.id for h in result] == ["good"]


# ── derive_confidence_tier (REASON-03) ─────────────────────────────────────


class TestDeriveConfidenceTier:
    def test_evidence_citation_is_high(self) -> None:
        """≥1 evidence citation → Tier 1 high (direct external-evidence link)."""
        h = Hypothesis(
            id="h",
            title="t",
            why="w",
            severity="moderate",
            confidence="low",  # model self-report — must be overridden
            citations=[
                Citation(kind="resource", ref="MedicationStatement/ms-001", label="x"),
                Citation(kind="evidence", ref="openfda:1:total", label="y"),
            ],
        )
        assert derive_confidence_tier(h) == "high"

    def test_resource_only_is_medium(self) -> None:
        """Only resource citations → Tier 2 medium (no external corroboration)."""
        h = Hypothesis(
            id="h",
            title="t",
            why="w",
            severity="moderate",
            confidence="high",  # model self-report — must be overridden
            citations=[
                Citation(kind="resource", ref="MedicationStatement/ms-001", label="x"),
            ],
        )
        assert derive_confidence_tier(h) == "medium"

    def test_no_citations_is_low(self) -> None:
        """No surviving citations → Tier 3 low (speculative)."""
        h = Hypothesis(
            id="h",
            title="t",
            why="w",
            severity="moderate",
            confidence="high",  # model self-report — must be overridden
            citations=[],
        )
        assert derive_confidence_tier(h) == "low"


class TestGetClient:
    def test_client_created_with_api_key(self) -> None:
        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": "test-key-123"}):
            client = _get_client()
            assert client._api_client.api_key == "test-key-123"

    def test_missing_key_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(KeyError, match="GOOGLE_GENAI_API_KEY"):
                _get_client()

    def test_blank_key_raises_keyerror_not_valueerror(self) -> None:
        # A present-but-empty key must be treated as "unset" — a uniform KeyError
        # abstention signal — rather than reaching Client(api_key="") which raises
        # ValueError (which the orchestrator would not catch → HTTP 500).
        with patch.dict("os.environ", {"GOOGLE_GENAI_API_KEY": ""}, clear=True):
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
        # REASON-03: model self-reported "medium", but it cites evidence → overridden to high.
        assert h.confidence == "high"

    @pytest.mark.asyncio
    async def test_drops_hypothesis_with_forbidden_language(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """A hypothesis with fully-resolvable citations is STILL dropped if its
        prose asserts causation/directives — the deterministic output-language
        gate runs after verification (AI-SPEC dim 3)."""
        response_text = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Hypotension",
                        "why": "The dizziness was caused by lisinopril.",
                        "severity": "moderate",
                        "confidence": "medium",
                        "citations": [
                            {"kind": "resource", "ref": "MedicationStatement/ms-001", "label": "x"}
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

        assert hypotheses == []  # citation resolved, but "caused by" prose is dropped

    @pytest.mark.asyncio
    async def test_medium_tier_override_resource_only(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """REASON-03 medium path end-to-end: Gemini self-reports some confidence,
        but the surviving citations are resource-only (no external evidence) →
        the final confidence is overridden to "medium" (Tier 2)."""
        response_text = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Lisinopril and dizziness",
                        "why": "Patient on lisinopril is associated with reported dizziness.",
                        "severity": "moderate",
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
        assert len(h.citations) == 1
        assert h.citations[0].kind == "resource"
        # Model self-reported "high", but only a resource citation resolved → medium.
        assert h.confidence == "medium"

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
    async def test_abstention_on_gemini_server_error(
        self,
        sample_flattened_text: str,
        sample_evidence_snippets: list[EvidenceSnippet],
    ) -> None:
        """REASON-08: a Gemini 5xx (ServerError, e.g. 503 'model overloaded' — a
        SIBLING of ClientError under APIError) must abstain, not crash. Regression
        for the except clause catching only ClientError (4xx)."""
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
                hypotheses = await run_reasoning(sample_flattened_text, sample_evidence_snippets)

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
