# ADR-0004: A2A protocol used only at the external boundary, never internally

Status: Accepted

## Context

Google's Agent2Agent (A2A) protocol standardizes discovery and delegation between independently-deployed, opaque agents across organizational/framework boundaries (Agent Card discovery, a task lifecycle built for long-running/human-in-the-loop work, OAuth2/mTLS/signed-card auth). Google ADK has first-class A2A support (`to_a2a()` to expose an agent, `RemoteA2aAgent` to call one). It would be possible to route all internal CEO-to-department messaging over A2A instead of Pub/Sub.

## Decision

Internal CEO-to-department messaging stays on Pub/Sub (ADR-0003) — we own every agent, every schema, and every trust boundary already, and A2A's request/response semantics and cross-organization auth model solve problems this deployment doesn't have.

A2A is used narrowly, at exactly one seam: exposing specific customer/partner-facing department agents (Sales and/or Support) as A2A servers via `to_a2a()`, so a genuinely external, independently-owned agent (a customer's or partner's own agent, on any framework, or Google's Gemini Enterprise Agent Registry) can discover and delegate work to that department without knowing anything about the internal Firestore/Pub-Sub schema.

## Alternatives considered

- **A2A for all internal messaging.** Rejected — no external, cross-vendor, opaque-agent problem exists internally; this would add a heavier auth/discovery layer with zero new capability over Pub/Sub, and Pub/Sub's push/fan-out model fits Cloud Run better than A2A's request/response shape for that traffic.
- **Skip A2A entirely.** Considered, but rejected in favor of the narrow external-boundary use: it gives a genuine, defensible "Fortified Enterprise Fleet" story (a real difference in trust model — OAuth2/signed cards at the external edge, IAM-scoped Pub/Sub internally) rather than either overusing or ignoring a protocol Google explicitly built into ADK for exactly this seam.

## Consequences

Exactly one (or two) department root agents get a second "front door": an A2A server alongside their normal Pub/Sub subscription, translating an inbound A2A task into an internal message and returning the result as a completed A2A artifact. No other department, and no internal orchestration path, touches A2A.
