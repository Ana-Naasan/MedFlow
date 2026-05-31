from pydantic import BaseModel, Field


class Citation(BaseModel):
    kind: str = Field(..., description="Citation type, such as resource or evidence card.")
    ref: str = Field(..., description="Resolvable citation target.")
    label: str | None = Field(default=None, description="Display label for the citation.")


class Hypothesis(BaseModel):
    id: str
    title: str
    why: str
    severity: str
    confidence: str
    citations: list[Citation] = Field(default_factory=list)


class DecisionPacket(BaseModel):
    patient_id: str
    summary_markdown: str
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    cache_status: str | None = None
