from pydantic import BaseModel


class RequestClassification(BaseModel):
    request_type: str  # onboarding, leave_request, policy_question, or other
    summary: str
