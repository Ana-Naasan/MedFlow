"""Integration test: golden path from demo patient → prompt → reasoning → verified hypotheses.

Uses the mock_fhir snapshot bundle and OpenFDA evidence data to
exercise the full pipeline with a mocked Gemini response.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.fhir.flatten import flatten_to_tagged_text
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.core import run_reasoning

# Path to the mock_fhir snapshot
_SNAPSHOT_PATH = Path("backend/app/seeds/mock_fhir_snapshot.json")

# Demographics for the demo patient
_DEMO_PATIENT_ID = "patient-example"


@pytest.fixture(scope="module")
def demo_flattened_text() -> str:
    """Load the mock_fhir snapshot and flatten it to tagged markdown."""
    snap = json.loads(_SNAPSHOT_PATH.read_text())
    resources = [entry["resource"] for entry in snap["entry"]]
    return flatten_to_tagged_text(resources)


@pytest.fixture(scope="module")
def demo_evidence() -> list[EvidenceSnippet]:
    """Simulated OpenFDA evidence cards for the demo patient's medication."""
    return [
        EvidenceSnippet(
            id="openfda:metformin:adverse_events:total_count",
            kind="openfda_adverse_event",
            ref="openfda:metformin:adverse_events:total_count",
            label="433,192 adverse events reported for metformin.",
        ),
        EvidenceSnippet(
            id="openfda:metformin:adverse_events:top_reactions",
            kind="openfda_adverse_event",
            ref="openfda:metformin:adverse_events:top_reactions",
            label="Most-reported reactions: NAUSEA, DIARRHOEA, VOMITING.",
        ),
        EvidenceSnippet(
            id="openfda:metformin:label:boxed_warning",
            kind="openfda_label",
            ref="openfda:metformin:label:boxed_warning",
            label="BOXED WARNING: LACTIC ACIDOSIS. See full prescribing information.",
        ),
        EvidenceSnippet(
            id="openfda:metformin:label:contraindication",
            kind="openfda_label",
            ref="openfda:metformin:label:contraindication",
            label="Contraindicated in severe renal impairment (eGFR below 30).",
        ),
    ]


# ── Golden path test ───────────────────────────────────────────────────────


class TestGoldenPath:
    """End-to-end golden test: demo patient → prompt → Gemini → verification."""

    @pytest.mark.asyncio
    async def test_demo_patient_produces_verified_hypothesis(
        self,
        demo_flattened_text: str,
        demo_evidence: list[EvidenceSnippet],
    ) -> None:
        """Given the demo patient + metformin evidence, a verified hypothesis
        with both patient-fact and evidence citations survives verification."""
        response_text = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Metformin gastrointestinal side effects",
                        "why": (
                            "The patient is prescribed Metformin (MedicationStatement/med-001) "
                            "for Type 2 diabetes mellitus (Condition/cond-001). "
                            "OpenFDA adverse-event data lists nausea, diarrhoea, and vomiting "
                            "as the most-reported reactions for metformin. "
                            "These align with known gastrointestinal side effects of metformin."
                        ),
                        "severity": "moderate",
                        "confidence": "high",
                        "citations": [
                            {
                                "kind": "resource",
                                "ref": "MedicationStatement/med-001",
                                "label": "Metformin prescription",
                            },
                            {
                                "kind": "resource",
                                "ref": "Condition/cond-001",
                                "label": "Type 2 diabetes diagnosis",
                            },
                            {
                                "kind": "evidence",
                                "ref": "openfda:metformin:adverse_events:top_reactions",
                                "label": "Metformin adverse reactions",
                            },
                            {
                                "kind": "evidence",
                                "ref": "openfda:metformin:label:boxed_warning",
                                "label": "Lactic acidosis warning",
                            },
                        ],
                    },
                    {
                        "title": "Metformin and renal function monitoring",
                        "why": (
                            "The patient is on metformin. OpenFDA label data contraindicates "
                            "metformin in severe renal impairment. No recent renal-function "
                            "lab is documented in the patient record."
                        ),
                        "severity": "serious",
                        "confidence": "medium",
                        "citations": [
                            {
                                "kind": "resource",
                                "ref": "MedicationStatement/med-001",
                                "label": "Metformin prescription",
                            },
                            {
                                "kind": "evidence",
                                "ref": "openfda:metformin:label:contraindication",
                                "label": "Renal impairment contraindication",
                            },
                        ],
                    },
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
                    demo_flattened_text, demo_evidence
                )

        # At least one hypothesis survives verification
        assert len(hypotheses) >= 1, (
            "Expected at least one verified hypothesis for the demo patient"
        )

        # Each surviving hypothesis must have both resource and evidence citations
        for hyp in hypotheses:
            kinds = {c.kind for c in hyp.citations}
            assert "resource" in kinds, (
                f"Hypothesis '{hyp.title}' missing patient-fact citation"
            )
            assert "evidence" in kinds, (
                f"Hypothesis '{hyp.title}' missing evidence citation"
            )

    @pytest.mark.asyncio
    async def test_hypotheses_have_required_fields(
        self,
        demo_flattened_text: str,
        demo_evidence: list[EvidenceSnippet],
    ) -> None:
        """Every surviving hypothesis has title, why, severity, confidence."""
        response_text = json.dumps(
            {
                "hypotheses": [
                    {
                        "title": "Test hypothesis A",
                        "why": "Because of known link between metformin and GI issues.",
                        "severity": "moderate",
                        "confidence": "high",
                        "citations": [
                            {
                                "kind": "resource",
                                "ref": "MedicationStatement/med-001",
                                "label": "Metformin",
                            },
                            {
                                "kind": "evidence",
                                "ref": "openfda:metformin:adverse_events:total_count",
                                "label": "433,192 events",
                            },
                        ],
                    },
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
                    demo_flattened_text, demo_evidence
                )

        assert len(hypotheses) == 1
        h = hypotheses[0]
        assert h.title
        assert h.why
        assert h.severity in ("critical", "serious", "moderate", "minor")
        assert h.confidence in ("high", "medium", "low")

    @pytest.mark.asyncio
    async def test_demo_patient_text_contains_expected_tags(
        self,
        demo_flattened_text: str,
    ) -> None:
        """Sanity check: the demo patient flattened text has the expected tags."""
        assert "[MedicationStatement/med-001]" in demo_flattened_text
        assert "[Condition/cond-001]" in demo_flattened_text
        assert "[Observation/obs-001]" in demo_flattened_text
        assert "[AllergyIntolerance/allergy-001]" in demo_flattened_text
        assert "[Procedure/proc-001]" in demo_flattened_text

    @pytest.mark.asyncio
    async def test_demo_evidence_has_expected_ids(
        self,
        demo_evidence: list[EvidenceSnippet],
    ) -> None:
        """Sanity check: evidence snippets have expected IDs."""
        ids = {s.id for s in demo_evidence}
        assert "openfda:metformin:adverse_events:top_reactions" in ids
        assert "openfda:metformin:label:boxed_warning" in ids
