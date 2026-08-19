from pydantic import BaseModel


class IntentClassification(BaseModel):
    intent: str  # billing, technical, account, or other
    urgency: str  # low, medium, high


class DraftResponse(BaseModel):
    reply: str
    cited_quote: str | None = None  # verbatim (claimed) quote from the KB backing the reply
