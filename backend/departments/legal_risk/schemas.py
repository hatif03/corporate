from pydantic import BaseModel


class Finding(BaseModel):
    """One judge's raw opinion — NOT yet trusted. It only becomes a reportable
    conflict after shared.verification.ground_quote confirms evidence_quote
    is actually present in the context text (see agents.py)."""

    lens: str
    conflict: bool
    claim: str | None = None
    evidence_quote: str | None = None
    confidence: int = 0


class GroundedConflict(BaseModel):
    lens: str
    claim: str
    grounded_quote: str
    confidence: int
