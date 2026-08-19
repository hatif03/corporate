# ADR-0007: High-stakes claims are deterministically grounded and voted, never trusted from raw LLM output

Status: Accepted

## Context

Several departments (Finance & Audit's verifier stage, Legal & Risk's conflict judges) produce claims that quote or reference source material as evidence for a decision or warning. An LLM can plausibly misquote, paraphrase, or fabricate a supporting quote while sounding confident. For departments whose whole value proposition is trustworthy output (an audit finding, a compliance warning), an ungrounded claim is worse than no claim.

## Decision

A shared verification module provides two composable, deterministic-first primitives used across departments:
- `ground_quote(quote, source_text)` — no LLM involved; exact/fuzzy string matching against the actual source text. If the quote can't be located in the source, the claim is dropped, not "corrected" by another LLM call.
- `vote_aspects(claim, aspect_checkers)` — fans a claim out to N independent pluggable checkers (each department supplies its own, e.g. numerical-consistency, citation-in-corpus, evidence-in-transcript), requires at least two-thirds agreement, and allows exactly one retry before treating the claim as unverified.

The operating principle: an LLM may *judge* or *propose*, but only deterministic code *verifies*. If nothing survives grounding/voting, the entire finding is dropped rather than surfaced with a caveat.

## Alternatives considered

- **Trust the LLM's self-reported confidence score.** Rejected — confidence scores from LLMs are not reliably calibrated to actual groundedness, and this project's audit/compliance departments need a harder guarantee than "the model said it was confident."
- **A second LLM call to double-check the first.** Rejected as the sole mechanism — an LLM checking another LLM's quote is still LLM-mediated and can share the same failure mode; the grounding step must be able to fail deterministically.

## Consequences

Any department producing a claim-with-evidence must route it through this shared module rather than trusting the generating agent's own output. This is slower and more conservative (real findings can be dropped if evidence can't be verbatim-located), which is the intended tradeoff for departments whose credibility depends on not fabricating support for their conclusions.
