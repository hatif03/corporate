"""Stage 1 of fraud detection: deterministic signals, zero LLM calls.
See docs/adr/0006-gemini-only-fraud-agent-structural-independence.md."""

from __future__ import annotations

from collections import Counter

from app.services import store
from departments.finance_audit.schemas import FraudSignals, InvoiceFields

ROUND_NUMBER_SUFFIXES = ("000", "00")


def _round_number_check(amount: float) -> tuple[bool, str]:
    cents = round(amount * 100)
    as_str = str(int(cents // 100))
    if any(as_str.endswith(suffix) for suffix in ROUND_NUMBER_SUFFIXES) and amount >= 100:
        return True, f"amount {amount} is a suspiciously round number"
    return False, "amount is not a round number"


def _duplicate_check(org_id: str, invoice: InvoiceFields) -> tuple[bool, str]:
    """Naive duplicate check: same vendor + invoice number in recent task
    results. ponytail: this scans list_tasks() results in Python rather than
    an indexed Firestore query — fine at hackathon-demo task volume, but
    should become a `where` query on a denormalized (vendor, invoiceNumber)
    field if the task history grows large."""
    for task in store.list_tasks(org_id):
        result = task.result or {}
        prior_vendor = result.get("vendor")
        prior_invoice_number = result.get("invoice_number")
        if prior_vendor == invoice.vendor and prior_invoice_number == invoice.invoice_number:
            return True, f"invoice {invoice.invoice_number} from {invoice.vendor} was already processed"
    return False, "no prior invoice with the same vendor + invoice number found"


def _benford_deviation_check(line_item_amounts: list[float]) -> tuple[bool, str]:
    """ponytail: real Benford's Law analysis needs a large population of
    naturally-occurring numbers (typically hundreds+) to be statistically
    meaningful — a single invoice's line items are far too few for a genuine
    chi-squared test against Benford's expected leading-digit distribution.
    This is a simplified single-document adaptation (flags an invoice whose
    line items are ALL the same leading digit, a weak but cheap proxy) —
    upgrade path: run real Benford's analysis in the accountant stage across
    the full historical AP ledger, not per-invoice, once that ledger exists.
    """
    leading_digits = [int(str(abs(a))[0]) for a in line_item_amounts if a > 0]
    if len(leading_digits) < 3:
        return False, "too few line items for a leading-digit check"
    most_common_digit, count = Counter(leading_digits).most_common(1)[0]
    if count == len(leading_digits) and most_common_digit in (1, 9):
        return True, f"all {len(leading_digits)} line items start with digit {most_common_digit}"
    return False, "leading-digit distribution looks unremarkable"


def compute_signals(org_id: str, invoice: InvoiceFields) -> FraudSignals:
    round_flag, round_detail = _round_number_check(invoice.amount)
    dup_flag, dup_detail = _duplicate_check(org_id, invoice)
    benford_flag, benford_detail = _benford_deviation_check(invoice.line_item_amounts)
    return FraudSignals(
        round_number_flag=round_flag,
        round_number_detail=round_detail,
        duplicate_flag=dup_flag,
        duplicate_detail=dup_detail,
        benford_deviation_flag=benford_flag,
        benford_deviation_detail=benford_detail,
    )
