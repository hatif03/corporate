"""Brand-voice aspect checkers, deterministic (no LLM) — same vote_aspects
contract Finance & Audit uses for its numerical/schema checks. Claim shape:
{"copy": "<drafted copy text>"}."""

from __future__ import annotations

from shared.verification import AspectVote

# Overclaim language legal/brand guidelines don't want in outbound copy —
# ponytail: a small static list, not a real style-guide linter. Extend this
# list (or replace with a real brand-guidelines service) as real copy review
# surfaces more categories worth catching.
BANNED_PHRASES = ("guaranteed", "best in the world", "#1", "risk-free", "no questions asked")

CTA_MARKERS = ("sign up", "get started", "learn more", "try it", "book a", "contact us", "request a demo")


async def no_banned_phrases(claim: dict) -> AspectVote:
    copy_lower = claim["copy"].lower()
    hits = [phrase for phrase in BANNED_PHRASES if phrase in copy_lower]
    return AspectVote(
        "no_banned_phrases",
        passed=not hits,
        reason="clean" if not hits else f"contains banned phrase(s): {hits}",
    )


async def has_call_to_action(claim: dict) -> AspectVote:
    copy_lower = claim["copy"].lower()
    found = any(marker in copy_lower for marker in CTA_MARKERS)
    return AspectVote("has_call_to_action", passed=found, reason="CTA present" if found else "no clear CTA found")


ASPECTS = {
    "no_banned_phrases": no_banned_phrases,
    "has_call_to_action": has_call_to_action,
}
