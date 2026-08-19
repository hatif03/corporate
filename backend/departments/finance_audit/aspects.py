"""Aspect checkers this department contributes to the shared verifier
(shared/verification.py's vote_aspects). Each receives the claim dict built
in agents.py's finalize step: {"invoice": ..., "signals": ..., "amount": ...}.
"""

from __future__ import annotations

from shared.verification import AspectVote

TOLERANCE = 0.01


async def numerical_consistency(claim: dict) -> AspectVote:
    invoice = claim["invoice"]
    line_sum = sum(invoice.get("line_item_amounts", []))
    amount = invoice.get("amount", 0.0)
    if not invoice.get("line_item_amounts"):
        return AspectVote("numerical_consistency", passed=True, reason="no line items to cross-check")
    passed = abs(line_sum - amount) <= TOLERANCE
    reason = f"line items sum to {line_sum}, invoice total is {amount}"
    return AspectVote("numerical_consistency", passed=passed, reason=reason)


async def schema_consistency(claim: dict) -> AspectVote:
    invoice = claim["invoice"]
    required = ("vendor", "invoice_number", "amount")
    missing = [f for f in required if not invoice.get(f)]
    return AspectVote(
        "schema_consistency",
        passed=not missing,
        reason="all required fields present" if not missing else f"missing fields: {missing}",
    )


ASPECTS = {
    "numerical_consistency": numerical_consistency,
    "schema_consistency": schema_consistency,
}
