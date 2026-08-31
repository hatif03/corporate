"""Runtime cross-model-style hallucination check: an independent second
model call judges the same claim the primary generation already produced,
as one more AspectChecker in the existing vote_aspects fan-out (shared/
verification.py, ADR-0007) — a genuinely separate call (fresh context, no
shared state with the primary generation), not just re-asking the same
model the same question in the same turn. See
docs/adr/0019-gemma-veo-lyria-vertex-ai-expansion.md for the full history:
this was originally spec'd as Gemma, live-tested against this project's
real Vertex AI, and swapped for a distinct Gemini tier
(corporate_verifier_model) after confirming Gemma requires a paid
self-hosted GPU endpoint in this project — not the free serverless call
originally assumed. Still a real second opinion, just not a different
vendor.

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


async def _ask_verifier(description: str) -> bool:
    # Deliberately NOT settings.vertex_location ("us-central1", what every
    # other raw genai.Client() in this app — Veo, Lyria, embeddings, voice —
    # correctly uses). corporate_verifier_model is a Gemini 3.5-tier model
    # (ADR-0020), and those only resolve at Vertex's "global" location in
    # this project — confirmed live, the exact 404 ADR-0020 already
    # documents for ADK's own default client, which this checker doesn't
    # go through since it's a raw genai.Client(), not an ADK LlmAgent.
    client = genai.Client(vertexai=True, project=settings.google_cloud_project, location="global")
    response = await client.aio.models.generate_content(
        model=settings.corporate_verifier_model, contents=_PROMPT.format(claim=description)
    )
    return (response.text or "").strip().lower().startswith("yes")


def make_verifier_checker(aspect_name: str, describe: Callable[[dict], str]) -> AspectChecker:
    """Returns an AspectChecker for vote_aspects. `describe(claim)` renders
    the department's existing claim dict as a short plain-English
    description for the independent reviewer — built from fields the claim
    already has, no new fields needed on any department's claim-construction
    code."""

    async def checker(claim: dict) -> AspectVote:
        description = describe(claim)
        try:
            passed = await _ask_verifier(description)
        except Exception as exc:  # noqa: BLE001 - see module docstring: failure counts as "no", not a crash
            return AspectVote(aspect_name, passed=False, reason=f"independent review call failed: {exc}")
        reason = "independent model review: plausible" if passed else "independent model review: flagged as inconsistent"
        return AspectVote(aspect_name, passed=passed, reason=reason)

    return checker
