# ADR-0009: SequentialAgent/ParallelAgent used despite deprecation — known debt

Status: Accepted

## Context

Google ADK 2.7.1 (the pinned version, ADR-0002) marks `SequentialAgent` and `ParallelAgent` as deprecated in favor of a new graph-based `Workflow` API (`google.adk.workflow.Workflow`, built on `BaseNode`/edges/triggers — a materially different execution model). They are not yet removed and still function correctly. Sales & CRM needs one genuine, directly-invokable ADK agent object as its `root_agent` (unlike Finance/Engineering/Legal, which orchestrate their stages in plain Python and leave `root_agent=None` — see ADR-0005's note on that field), because ADK's `to_a2a()` (ADR-0004) needs a real `BaseAgent`/`Workflow` to expose externally.

## Decision

Use `SequentialAgent` for Sales & CRM's three-stage pipeline (`lead_qualifier -> deal_strategist -> outreach_drafter`) despite the deprecation warning, rather than spending time learning and correctly implementing the new `Workflow` graph API under a hackathon deadline without having verified it.

## Alternatives considered

- **Learn and use `Workflow` now.** Rejected for now — it's a genuinely different model (nodes/edges/graph orchestration) that needs real investigation to use correctly, and getting it subtly wrong under time pressure is worse than a documented deprecation warning on a class that still works.
- **Avoid a real ADK agent entirely, keep Sales as plain-Python orchestration like the other three departments.** Rejected — Sales specifically needs a real `root_agent` for A2A exposure (ADR-0004); plain-Python orchestration has no single agent object to hand `to_a2a()`.

## Consequences

Sales & CRM will emit a `DeprecationWarning` at import time. This is accepted debt, not an oversight — revisit when there's time to properly evaluate `google.adk.workflow.Workflow` (worth doing for the whole department layer, not just Sales, if it becomes the standard way to compose multi-stage agents). Track this ADR as still-open until that evaluation happens.
