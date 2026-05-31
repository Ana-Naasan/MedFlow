"""Tests for reasoning/prompts.py — prompt assembly for the Gemini call."""

from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.prompts import (
    SYSTEM_INSTRUCTION,
    _format_evidence,
    build_reasoning_prompt,
)


# ── _format_evidence tests ─────────────────────────────────────────────────


class TestFormatEvidence:
    def test_empty_evidence(self) -> None:
        result = _format_evidence([])
        assert result == "_(no evidence cards available)_"

    def test_single_snippet(self) -> None:
        snippets = [
            EvidenceSnippet(
                id="openfda:197885:adverse_events:total_count",
                kind="openfda_adverse_event",
                ref="openfda:adverse_events:197885:total_count",
                label="10,064 adverse events reported for lisinopril.",
            ),
        ]
        result = _format_evidence(snippets)
        assert "openfda:197885:adverse_events:total_count" in result
        assert "openfda_adverse_event" in result
        assert "10,064" in result
        assert result.startswith("1. [")

    def test_multiple_snippets(self) -> None:
        snippets = [
            EvidenceSnippet(
                id="openfda:197885:adverse_events:total_count",
                kind="openfda_adverse_event",
                ref="",
                label="First snippet.",
            ),
            EvidenceSnippet(
                id="openfda:197885:label:boxed_warning",
                kind="openfda_label",
                ref="",
                label="Second snippet.",
            ),
        ]
        result = _format_evidence(snippets)
        assert result.startswith("1. [openfda:197885:adverse_events:total_count]")
        assert "2. [openfda:197885:label:boxed_warning]" in result

    def test_label_truncated_at_200_chars(self) -> None:
        long_label = "x" * 500
        snippets = [
            EvidenceSnippet(
                id="test:1",
                kind="test",
                ref="",
                label=long_label,
            ),
        ]
        result = _format_evidence(snippets)
        # 200-char slice, no trailing "..."
        assert result.count("x") == 200


# ── build_reasoning_prompt tests ───────────────────────────────────────────


class TestBuildPrompt:
    def test_includes_system_instruction(self) -> None:
        prompt = build_reasoning_prompt("## Medications\n\n_(not documented)_", [])
        assert SYSTEM_INSTRUCTION in prompt

    def test_includes_patient_section(self) -> None:
        patient_text = "## Medications\n\n[MedicationStatement/ms-001] Lisinopril — active"
        prompt = build_reasoning_prompt(patient_text, [])
        assert "## Patient Clinical Data" in prompt
        assert "[MedicationStatement/ms-001]" in prompt

    def test_includes_evidence_section(self) -> None:
        snippets = [
            EvidenceSnippet(
                id="openfda:197885:adverse_events:total_count",
                kind="openfda_adverse_event",
                ref="",
                label="10,064 events.",
            ),
        ]
        prompt = build_reasoning_prompt("_(not documented)_", snippets)
        assert "## Evidence Cards" in prompt
        assert "openfda:197885:adverse_events:total_count" in prompt

    def test_no_evidence_shows_fallback(self) -> None:
        prompt = build_reasoning_prompt("_(not documented)_", [])
        assert "no evidence cards available" in prompt

    def test_output_format_instructions_present(self) -> None:
        prompt = build_reasoning_prompt("_(not documented)_", [])
        assert '"hypotheses"' in prompt
        assert "patient_fact" in prompt
        assert "evidence_card" in prompt
        assert "severity" in prompt
        assert "confidence" in prompt
        assert "critical|serious|moderate|minor" in prompt
        assert "high|medium|low" in prompt

    def test_only_reference_present_facts_rule(self) -> None:
        prompt = build_reasoning_prompt("_(not documented)_", [])
        assert "ONLY reference facts" in prompt
        assert "Do NOT invent" in prompt

    def test_patient_text_with_no_evidence(self) -> None:
        """Evidence section shows fallback when no snippets provided."""
        prompt = build_reasoning_prompt(
            "## Conditions\n\n[Condition/c1] Hypertension — active, confirmed",
            [],
        )
        assert "no evidence cards available" in prompt

    def test_multiline_patient_text(self) -> None:
        patient_text = (
            "## Medications\n\n"
            "[MedicationStatement/ms-001] Lisinopril 10 MG — active\n"
            "[MedicationStatement/ms-002] Metformin 500 MG — active\n\n"
            "## Conditions\n\n"
            "[Condition/c1] Hypertension — active, confirmed\n"
        )
        prompt = build_reasoning_prompt(patient_text, [])
        assert "[MedicationStatement/ms-001]" in prompt
        assert "[MedicationStatement/ms-002]" in prompt
        assert "[Condition/c1]" in prompt

    def test_output_format_instructions_include_all_fields(self) -> None:
        """Verify every Hypothesis field appears in the prompt instructions."""
        prompt = build_reasoning_prompt("_(not documented)_", [])
        for field in ("title", "why", "severity", "confidence", "citations"):
            assert field in prompt, f"Field '{field}' missing from prompt instructions"

    def test_evidence_snippet_ids_preserved(self) -> None:
        """Snippet IDs appear exactly once and match the input."""
        snippets = [
            EvidenceSnippet(
                id="openfda:197885:adverse_events:death_count",
                kind="openfda_adverse_event",
                ref="",
                label="42 events involved death.",
            ),
        ]
        prompt = build_reasoning_prompt("_(not documented)_", snippets)
        assert "openfda:197885:adverse_events:death_count" in prompt
        assert "42 events involved death." in prompt
