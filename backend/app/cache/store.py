from __future__ import annotations

from copy import deepcopy

from backend.app.dtos import CategoryCompleteness, Citation, DecisionPacket, Hypothesis
from backend.app.fhir.data_gaps import apply_gap_downgrades

# ── Static patient data ───────────────────────────────────────────────────────
#
# Resources that carry a "span" key originate from a PDF connector.
# span = {page: int, start: int, end: int, snippet: str}
# The /resource endpoint returns this key verbatim so the frontend can render
# the PDF highlight view.

STATIC_PATIENTS: dict[str, dict[str, object]] = {
    "pat-001": {
        "resources": {
            ("Patient", "pat-001"): {
                "resourceType": "Patient",
                "id": "pat-001",
                "identifier": [{"system": "urn:mrn", "value": "MRN-001"}],
                "gender": "female",
                "birthDate": "1944-02-18",
            },
            ("MedicationStatement", "med-001"): {
                "resourceType": "MedicationStatement",
                "id": "med-001",
                "status": "active",
                "medicationCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": "1191",
                            "display": "Aspirin 81 MG Oral Tablet",
                        }
                    ]
                },
                "subject": {"reference": "Patient/pat-001"},
            },
        },
        "evidence": {
            "openfda-label-amitriptyline": {
                "id": "openfda-label-amitriptyline",
                "source": "openFDA",
                "snippet": (
                    "Amitriptyline may cause drowsiness and anticholinergic adverse effects."
                ),
                "ref_url": "https://api.fda.gov/drug/label.json?search=openfda.rxcui:703",
            },
            "ddinter-aspirin-warfarin": {
                "id": "ddinter-aspirin-warfarin",
                "source": "DDInter",
                "snippet": "Aspirin and warfarin may increase bleeding risk.",
                "ref_url": "https://ddinter.scbdd.com/",
            },
        },
    },
    "DEMO-001": {
        "resources": {
            ("Patient", "DEMO-001"): {
                "resourceType": "Patient",
                "id": "DEMO-001",
                "identifier": [{"system": "urn:mrn", "value": "MRN-DEMO-001"}],
                "gender": "female",
                "birthDate": "1942-03-15",
            },
            # PDF-sourced medications — span mirrors the planted PDF fixture offsets.
            ("MedicationStatement", "med-warfarin"): {
                "resourceType": "MedicationStatement",
                "id": "med-warfarin",
                "status": "active",
                "medicationCodeableConcept": {"text": "Warfarin"},
                "subject": {"reference": "Patient/DEMO-001"},
                "dosage": [{"text": "5 mg oral daily"}],
                "span": {
                    "page": 2,
                    "start": 143,
                    "end": 183,
                    "snippet": "Warfarin 5 mg oral Anticoagulant Daily",
                },
            },
            ("MedicationStatement", "med-aspirin"): {
                "resourceType": "MedicationStatement",
                "id": "med-aspirin",
                "status": "active",
                "medicationCodeableConcept": {"text": "Aspirin"},
                "subject": {"reference": "Patient/DEMO-001"},
                "dosage": [{"text": "81 mg oral daily"}],
                "span": {
                    "page": 2,
                    "start": 184,
                    "end": 220,
                    "snippet": "Aspirin 81 mg oral Antiplatelet Daily",
                },
            },
            ("MedicationStatement", "med-amitriptyline"): {
                "resourceType": "MedicationStatement",
                "id": "med-amitriptyline",
                "status": "active",
                "medicationCodeableConcept": {"text": "Amitriptyline"},
                "subject": {"reference": "Patient/DEMO-001"},
                "dosage": [{"text": "25 mg oral nightly"}],
                "span": {
                    "page": 2,
                    "start": 221,
                    "end": 263,
                    "snippet": "Amitriptyline 25 mg oral Depression Nightly",
                },
            },
            # PDF-sourced condition
            ("Condition", "condition-i48-0"): {
                "resourceType": "Condition",
                "id": "condition-i48-0",
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I48.0"}],
                    "text": "Atrial fibrillation",
                },
                "span": {
                    "page": 1,
                    "start": 245,
                    "end": 283,
                    "snippet": "1. Atrial fibrillation (I48.0)",
                },
            },
        },
        "evidence": {
            "ddinter-warfarin-aspirin": {
                "id": "ddinter-warfarin-aspirin",
                "source": "DDInter",
                "snippet": (
                    "Warfarin and aspirin combination significantly increases the risk of major "
                    "bleeding. Concurrent use should be avoided or closely monitored with INR "
                    "checks and dose adjustment."
                ),
                "ref_url": "https://ddinter.scbdd.com/",
            },
            "beers-amitriptyline-anticholinergic": {
                "id": "beers-amitriptyline-anticholinergic",
                "source": "AGS Beers Criteria 2023",
                "snippet": (
                    "Amitriptyline is highly anticholinergic and should be avoided in older "
                    "adults (Beers Criteria 2023). High ACB score of 3 is associated with "
                    "cognitive impairment, falls, and delirium in patients over 65."
                ),
                "ref_url": "https://agsjournals.onlinelibrary.wiley.com/doi/10.1111/jgs.18372",
            },
            "openfda-warfarin-interactions": {
                "id": "openfda-warfarin-interactions",
                "source": "openFDA",
                "snippet": (
                    "Warfarin has a narrow therapeutic index. Aspirin and other NSAIDs may "
                    "displace warfarin from plasma protein binding sites, increasing free "
                    "warfarin levels and bleeding risk. INR must be monitored closely."
                ),
                "ref_url": "https://api.fda.gov/drug/label.json?search=openfda.rxcui:11289",
            },
        },
    },
}

STATIC_CONNECTORS: list[dict[str, object]] = [
    {
        "id": "mock-fhir",
        "name": "MockFHIRProvider",
        "capabilities": ["PATIENT", "MEDICATIONS", "CONDITIONS"],
        "health": "ok",
    },
    {
        "id": "postgres",
        "name": "PostgresProvider",
        "capabilities": ["PATIENT", "MEDICATIONS", "CONDITIONS", "ALLERGIES"],
        "health": "ok",
    },
]


def build_packet(patient_id: str) -> DecisionPacket:
    if patient_id == "DEMO-001":
        return _build_demo_001_packet()
    return _build_default_packet(patient_id)


def _build_demo_001_packet() -> DecisionPacket:
    # Authored at maximum suspected confidence; the data_gaps gate below
    # downgrades both medication-citing hypotheses one step because the
    # patient record has no AllergyIntolerance or Observation resources
    # (issue #30: never claim safety from absence).
    hypotheses = [
        Hypothesis(
            id="hyp-DEMO-001-bleeding",
            title="Warfarin + Aspirin co-prescription with supratherapeutic INR",
            why=(
                "Patient is on warfarin (INR 3.2 — above the 2.0–3.0 target) and aspirin "
                "81 mg concurrently. DDInter classifies this as a Major interaction. Aspirin "
                "displaces warfarin from protein binding and adds antiplatelet effect, "
                "compounding bleed risk."
            ),
            severity="high",
            confidence="high",
            group="drug:warfarin+aspirin;risk:bleeding",
            citations=[
                Citation(kind="resource", ref="Patient/DEMO-001", label="Patient/DEMO-001"),
                Citation(
                    kind="resource",
                    ref="MedicationStatement/med-warfarin",
                    label="Warfarin (PDF)",
                ),
                Citation(
                    kind="resource",
                    ref="MedicationStatement/med-aspirin",
                    label="Aspirin (PDF)",
                ),
                Citation(
                    kind="evidence",
                    ref="ddinter-warfarin-aspirin",
                    label="DDInter warfarin-aspirin (Major)",
                ),
                Citation(
                    kind="evidence",
                    ref="openfda-warfarin-interactions",
                    label="openFDA warfarin label",
                ),
            ],
        ),
        Hypothesis(
            id="hyp-DEMO-001-anticholinergic",
            title="Amitriptyline in elderly — high anticholinergic burden",
            why=(
                "Amitriptyline has an ACB score of 3 (highest tier). AGS Beers Criteria 2023 "
                "explicitly recommends avoiding tricyclic antidepressants in adults 65+ due to "
                "risk of cognitive impairment, falls, and delirium. Patient is 82 years old."
            ),
            severity="moderate",
            confidence="high",
            group="drug:amitriptyline;risk:anticholinergic",
            citations=[
                Citation(kind="resource", ref="Patient/DEMO-001", label="Patient/DEMO-001"),
                Citation(
                    kind="resource",
                    ref="MedicationStatement/med-amitriptyline",
                    label="Amitriptyline (PDF)",
                ),
                Citation(
                    kind="evidence",
                    ref="beers-amitriptyline-anticholinergic",
                    label="AGS Beers Criteria 2023 — amitriptyline",
                ),
            ],
        ),
    ]
    # Labs (Observation) and Allergies (AllergyIntolerance) are safety-critical
    # gaps for this patient — drop med-citing hypotheses one rung on the ladder.
    hypotheses = apply_gap_downgrades(
        hypotheses, gap_fhir_types={"AllergyIntolerance", "Observation"}
    )
    return DecisionPacket(
        patient_id="DEMO-001",
        summary_markdown=(
            "### Clinical Alerts — Eleanor Smith (82F)\n"
            "- **Suspected high risk:** Warfarin + Aspirin co-prescription → major bleeding risk "
            "(INR 3.2 noted in narrative, structured lab confirmation pending). Confidence "
            "downgraded one step — verify allergy history and connect lab system before acting.\n"
            "- **Moderate risk:** Amitriptyline in elderly patient → Anticholinergic Cognitive "
            "Burden score 3 (Beers Criteria 2023). Confidence downgraded pending allergy/lab "
            "verification; consider safer alternative."
        ),
        hypotheses=hypotheses,
        data_gaps=[
            "INR result noted in narrative but no structured lab source connected",
            "Allergy history not documented",
            "Surgical/procedure history not available",
        ],
        completeness=[
            CategoryCompleteness(category="Patient", documented=True),
            CategoryCompleteness(category="Medications", documented=True),
            CategoryCompleteness(category="Conditions", documented=True),
            CategoryCompleteness(
                category="Labs",
                documented=False,
                gap_note="INR result noted but no structured lab source — connect lab system",
            ),
            CategoryCompleteness(
                category="Allergies",
                documented=False,
                gap_note="No allergy documentation found — verify with patient",
            ),
            CategoryCompleteness(
                category="Procedures",
                documented=False,
                gap_note="Surgical and procedure history not documented",
            ),
        ],
        cache_status="HIT",
    )


def _build_default_packet(patient_id: str) -> DecisionPacket:
    return DecisionPacket(
        patient_id=patient_id,
        summary_markdown=(
            "### Cited suggestions\n"
            "- May be associated with a medication effect; consider reviewing aspirin use.\n"
            "- Citation-backed resolution is available for the patient record and evidence cards."
        ),
        hypotheses=[
            Hypothesis(
                id="hyp-001",
                title="Possible medication-related bleeding risk",
                why=(
                    "The patient is on aspirin and the evidence store includes a cited DDInter "
                    "interaction."
                ),
                severity="moderate",
                confidence="low",
                group="drug:aspirin;risk:bleeding",
                citations=[
                    Citation(kind="resource", ref="Patient/pat-001", label="Patient/pat-001"),
                    Citation(
                        kind="evidence",
                        ref="ddinter-aspirin-warfarin",
                        label="DDInter aspirin-warfarin",
                    ),
                ],
            )
        ],
        data_gaps=["Renal function labs missing"],
        completeness=[
            CategoryCompleteness(category="Patient", documented=True),
            CategoryCompleteness(category="Medications", documented=True),
            CategoryCompleteness(
                category="Conditions",
                documented=False,
                gap_note="No condition documentation found — request discharge summary",
            ),
            CategoryCompleteness(
                category="Labs",
                documented=False,
                gap_note="Renal function labs not available — order BMP/CMP",
            ),
            CategoryCompleteness(
                category="Allergies",
                documented=False,
                gap_note="Allergy history not provided — verify with patient",
            ),
            CategoryCompleteness(
                category="Procedures",
                documented=False,
                gap_note="Procedure history not available",
            ),
        ],
        cache_status="HIT",
    )


def list_patient_ids() -> list[str]:
    return list(STATIC_PATIENTS)


def list_connectors() -> list[dict[str, object]]:
    return deepcopy(STATIC_CONNECTORS)


def get_patient_resource(
    patient_id: str,
    resource_type: str,
    resource_id: str,
) -> dict[str, object] | None:
    patient = STATIC_PATIENTS.get(patient_id)
    if patient is None:
        return None
    resources = patient["resources"]
    resource = resources.get((resource_type, resource_id))
    return deepcopy(resource) if resource is not None else None


def get_evidence_card(evidence_id: str) -> dict[str, object] | None:
    for patient in STATIC_PATIENTS.values():
        evidence = patient.get("evidence", {})
        card = evidence.get(evidence_id)
        if card is not None:
            return deepcopy(card)
    return None


def get_patient_resources(patient_id: str) -> list[dict[str, object]]:
    """Return every FHIR resource dict for a patient (empty list if unknown).

    Feeds the reasoning pipeline's flattener; the per-citation lookups still go
    through ``get_patient_resource`` so the cache stays the authority.
    """
    patient = STATIC_PATIENTS.get(patient_id)
    if patient is None:
        return []
    resources = patient["resources"]
    return [deepcopy(r) for r in resources.values()]


def get_evidence_cards(patient_id: str) -> list[dict[str, object]]:
    """Return every evidence card dict for a patient (empty list if unknown)."""
    patient = STATIC_PATIENTS.get(patient_id)
    if patient is None:
        return []
    evidence = patient.get("evidence", {})
    return [deepcopy(c) for c in evidence.values()]
