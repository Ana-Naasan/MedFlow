from __future__ import annotations

from copy import deepcopy

from backend.app.dtos import Citation, DecisionPacket, Hypothesis

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
    }
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
    patient = STATIC_PATIENTS.get("pat-001")
    if patient is None:
        return None
    evidence = patient["evidence"].get(evidence_id)
    return deepcopy(evidence) if evidence is not None else None


def refresh_patient(patient_id: str) -> dict[str, object]:
    if patient_id not in STATIC_PATIENTS:
        return {"patient_id": patient_id, "status": "missing"}
    return {"patient_id": patient_id, "status": "refreshed"}