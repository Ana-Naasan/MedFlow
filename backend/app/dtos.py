from pydantic import BaseModel, Field


class Citation(BaseModel):
    kind: str = Field(..., description="Citation type, such as resource or evidence card.")
    ref: str = Field(..., description="Resolvable citation target.")
    label: str | None = Field(default=None, description="Display label for the citation.")


class CategoryCompleteness(BaseModel):
    category: str = Field(..., description="Clinical data category, e.g. Medications.")
    documented: bool = Field(..., description="True if the category has documented data.")
    gap_note: str | None = Field(default=None, description="Clinician to-do when not documented.")


class Hypothesis(BaseModel):
    id: str
    title: str
    why: str
    severity: str
    confidence: str
    group: str | None = Field(
        default=None, description="Stable cross-reference key for dismiss-similar."
    )
    citations: list[Citation] = Field(default_factory=list)


class DecisionPacket(BaseModel):
    patient_id: str
    summary_markdown: str
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    completeness: list[CategoryCompleteness] = Field(default_factory=list)
    cache_status: str | None = None


class IntakeRequest(BaseModel):
    connector: str = Field(..., description="Registered connector ID, e.g. 'mock-fhir'.")
    source_patient_id: str = Field(..., description="Patient ID as known to the source connector.")
    patient_id: str | None = Field(
        default=None,
        description="Override the stored patient ID; auto-generated UUID if omitted.",
    )


class IntakeResponse(BaseModel):
    patient_id: str
    status: str
    resource_count: int
    hypothesis_ids: list[str] = Field(default_factory=list)


class HypothesisActionRequest(BaseModel):
    patient_id: str


class HypothesisConfirmResponse(BaseModel):
    id: str
    status: str


class HypothesisDismissResponse(BaseModel):
    id: str
    status: str
    dismissed_ids: list[str]
