from pydantic import BaseModel


class RequestClassification(BaseModel):
    request_type: str  # onboarding, leave_request, policy_question, or other
    summary: str


class HandbookAnswer(BaseModel):
    answer: str
    cited_quote: str | None = None  # verbatim (claimed) quote from the handbook backing the answer
