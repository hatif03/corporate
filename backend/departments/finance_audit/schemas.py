from pydantic import BaseModel


class InvoiceFields(BaseModel):
    """What doc_intel extracts from a raw invoice description."""

    vendor: str
    invoice_number: str
    amount: float
    currency: str = "USD"
    line_item_amounts: list[float] = []


class FraudSignals(BaseModel):
    """Stage-1 deterministic output (see docs/adr/0006). The fraud LlmAgent
    (Stage 2) sees only this — never the accountant agent's prior reasoning."""

    round_number_flag: bool
    round_number_detail: str
    duplicate_flag: bool
    duplicate_detail: str
    benford_deviation_flag: bool
    benford_deviation_detail: str
