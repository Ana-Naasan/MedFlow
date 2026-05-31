from fastapi import APIRouter

from backend.app.dtos import Citation, DecisionPacket, Hypothesis

router = APIRouter(prefix="/packet", tags=["packet"])


@router.get("/{patient_id}", response_model=DecisionPacket)
async def get_packet(patient_id: str) -> DecisionPacket:
    return DecisionPacket(
        patient_id=patient_id,
        summary_markdown="**Stub packet** — real reasoning not yet wired.",
        hypotheses=[
            Hypothesis(
                id="h-001",
                title="Polypharmacy interaction risk",
                why="Patient is on 5+ medications with overlapping metabolic pathways.",
                severity="moderate",
                confidence="low",
                citations=[
                    Citation(
                        kind="evidence_card",
                        ref="rxnorm://12345",
                        label="Drug interaction: warfarin × aspirin",
                    )
                ],
            )
        ],
        data_gaps=["Renal function labs missing"],
        cache_status="stub",
    )
