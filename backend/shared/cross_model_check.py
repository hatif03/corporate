"""Runtime cross-model hallucination check: an independent second model
(Gemma, via Vertex AI's fully-managed MaaS API — same project/location/ADC
as every other Vertex call in this app, no self-hosted GPU endpoint needed)
judges the same claim Gemini already produced, as one more AspectChecker in
the existing vote_aspects fan-out (shared/verification.py, ADR-0007) —
genuine cross-model consensus, not just more Gemini checking Gemini. See
docs/adr/0019-gemma-veo-lyria-vertex-ai-expansion.md.

Deliberately NOT an "auto-fix on disagreement" loop: a failed vote flows
into the exact same @audited_task BLOCKED/HumanQA path every other
verification failure already takes (ADR-0011) — "an LLM may judge or
propose, but only deterministic code verifies" (ADR-0007) applies here
exactly as it does to every other aspect checker. A model-call failure
(quota, network, malformed response) counts as a "no" rather than raising —
the whole point of this checker is an extra layer of caution, so a checker
that can silently vanish on error would defeat that.
"""

from __future__ import annotations

from typing import Callable

from google import genai

from app.config import settings
from shared.verification import AspectChecker, AspectVote

_PROMPT = (
    "You are an independent reviewer double-checking another AI system's work — you did not "
    "produce this claim yourself. Claim to review:\n\n{claim}\n\n"
    "Does this claim look internally consistent and plausible, with no obvious fabrication or "
    "contradiction? Answer with exactly one word: yes or no."
)


async def _ask_gemma(description: str) -> bool:
    client = genai.Client(vertexai=True, project=settings.google_cloud_project, location=settings.vertex_location)
    response = await client.aio.models.generate_content(
        model=settings.corporate_gemma_model, contents=_PROMPT.format(claim=description)
    )
    return (response.text or "").strip().lower().startswith("yes")


def make_gemma_checker(aspect_name: str, describe: Callable[[dict], str]) -> AspectChecker:
    """Returns an AspectChecker for vote_aspects. `describe(claim)` renders
    the department's existing claim dict as a short plain-English
    description for Gemma to review — built from fields the claim already
    has, no new fields needed on any department's claim-construction code."""

    async def checker(claim: dict) -> AspectVote:
        description = describe(claim)
        try:
            passed = await _ask_gemma(description)
        except Exception as exc:  # noqa: BLE001 - see module docstring: failure counts as "no", not a crash
            return AspectVote(aspect_name, passed=False, reason=f"gemma check failed: {exc}")
        reason = "independent model review: plausible" if passed else "independent model review: flagged as inconsistent"
        return AspectVote(aspect_name, passed=passed, reason=reason)

    return checker
