from pydantic import BaseModel


class TriageResult(BaseModel):
    severity: str  # P1, P2, P3, or P4
    affected_systems: list[str]
    summary: str


class CascadePrediction(BaseModel):
    cascade_risk: str  # low, medium, high
    reasoning: str
