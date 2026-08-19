# ADR-0006: Fraud-detection stays Gemini-only, independence comes from structure not model diversity

Status: Accepted

## Context

A fraud/anomaly-detection stage benefits from having its reasoning arrive independently of an earlier classification stage's conclusions — otherwise the same model, having already committed to a read of a document, may simply rationalize its own prior framing rather than catching what that framing missed. One way to get independence is to run the second stage on a genuinely different model provider. This project's hard constraint (see `/docs/system_prompt.md`) is that all product-facing reasoning runs on Gemini via Google ADK — no second LLM provider in the shipped product.

## Decision

The Finance & Audit fraud-detection stage is two-stage and Gemini-only:
1. **Stage 1** computes deterministic signals with zero LLM calls (statistical anomaly checks, duplicate/near-duplicate detection, round-number heuristics).
2. **Stage 2** is a fresh, low-temperature Gemini call that sees *only* the Stage 1 signals JSON — not the upstream classification agent's prior reasoning or conclusions.

Independence comes from what each stage is allowed to see, not from which model vendor answers.

## Alternatives considered

- **A second LLM provider dedicated to fraud detection**, evaluated and rejected to keep the product's LLM surface single-vendor per the Gemini-only constraint, and to avoid the added integration/cost/latency of a second provider for one narrow stage.
- **Self-consistency sampling** (multiple Gemini calls at the same stage, voting) as a partial substitute for cross-model diversity — noted as an available future enhancement, not required for the MVP.

## Consequences

The fraud agent's prompt boundary is a hard rule, not a style preference: Stage 2 must never receive the accountant/classification agent's chain-of-thought or verdict, only the Stage 1 signal payload. Any refactor that collapses the two stages into one call reintroduces the exact bias this ADR exists to prevent.
