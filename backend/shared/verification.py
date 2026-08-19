"""Grounded-claim verification: only deterministic code verifies, an LLM may
only judge/propose. See docs/adr/0007-grounded-claim-verification-pattern.md.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Awaitable, Callable

GROUND_MATCH_THRESHOLD = 0.85


def ground_quote(quote: str, source_text: str) -> str | None:
    """Locate `quote` verbatim (or near-verbatim) inside `source_text`.

    Returns the exact substring of source_text that matches, or None if the
    quote can't be grounded — callers must drop the claim in that case, never
    "correct" it with another LLM call.
    """
    quote = quote.strip()
    if not quote:
        return None
    if quote in source_text:
        return quote

    # Fuzzy fallback: slide a window of the quote's length over the source
    # and keep the best-matching window if it clears the threshold.
    window = len(quote)
    best_ratio = 0.0
    best_match: str | None = None
    for start in range(0, max(len(source_text) - window, 0) + 1):
        candidate = source_text[start : start + window]
        ratio = difflib.SequenceMatcher(None, quote, candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate
    if best_ratio >= GROUND_MATCH_THRESHOLD:
        return best_match
    return None


@dataclass
class AspectVote:
    aspect: str
    passed: bool
    reason: str = ""


@dataclass
class VerifiedResult:
    verified: bool
    votes: list[AspectVote]
    retried: bool = False


AspectChecker = Callable[[dict], Awaitable[AspectVote]]


async def vote_aspects(
    claim: dict,
    aspect_checkers: dict[str, AspectChecker],
    min_agreement_ratio: float = 2 / 3,
) -> VerifiedResult:
    """Fan a claim out to every supplied aspect checker, require at least
    `min_agreement_ratio` to pass, and allow exactly one retry before treating
    the claim as unverified."""
    if not aspect_checkers:
        raise ValueError("vote_aspects requires at least one aspect checker")

    votes = [await checker(claim) for checker in aspect_checkers.values()]
    if _agreement_ratio(votes) >= min_agreement_ratio:
        return VerifiedResult(verified=True, votes=votes)

    retry_votes = [await checker(claim) for checker in aspect_checkers.values()]
    return VerifiedResult(
        verified=_agreement_ratio(retry_votes) >= min_agreement_ratio,
        votes=retry_votes,
        retried=True,
    )


def _agreement_ratio(votes: list[AspectVote]) -> float:
    return sum(1 for v in votes if v.passed) / len(votes)
