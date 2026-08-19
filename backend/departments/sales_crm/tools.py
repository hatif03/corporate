"""Sales & CRM-specific tools. pricing_guardrail is the deterministic hard
cap referenced in docs/system_prompt.md's department roster — no LLM,
anywhere in the call chain, can raise the approved discount above this."""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

MAX_DISCOUNT_PERCENT = 20


async def pricing_guardrail(proposed_percent: float, tool_context: ToolContext) -> dict:
    """Validate a proposed discount percentage against the company's hard cap.

    Args:
        proposed_percent: the discount percentage the deal strategist wants to offer.
    """
    approved = min(proposed_percent, MAX_DISCOUNT_PERCENT)
    return {
        "proposed_percent": proposed_percent,
        "approved_percent": approved,
        "capped": approved < proposed_percent,
        "cap": MAX_DISCOUNT_PERCENT,
    }
