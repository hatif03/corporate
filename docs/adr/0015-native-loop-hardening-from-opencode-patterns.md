# ADR-0015: Agent loop hardening, patterns reimplemented natively from opencode research

Status: Accepted

## Context

Following ADR-0014's rejection of Google Antigravity, a request to study a real, mature open-source coding agent (`anomalyco/opencode`, MIT, ~200k stars) and four "loop engineering" sources (Addy Osmani x2, the Claude Agent SDK docs, LangChain) in depth, and bring the best concrete patterns into this backend's own agent loop — without adopting a new framework or dependency, the same constraint that shaped ADR-0002 and ADR-0014.

Real, verbatim research (opencode's actual source read via `gh api`, all four articles read via WebFetch) surfaced a small number of concrete, portable patterns worth reimplementing, and confirmed several existing boundaries in this codebase were already correctly drawn.

## Decision

Reimplement, natively in Python against this project's own ADK/Firestore stack, the following patterns adapted from opencode (MIT-licensed, attributed in `/THIRD_PARTY_SKILLS.md`):

1. **Doom-loop guard + per-turn tool-call cap** (`app/adk_agents/runtime.py`) — the same tool called with byte-identical arguments 3 times in a row, or more than 25 tool calls in one turn, raises `RuntimeError`. Reuses `@audited_task`'s existing failure-containment path (ADR-0011) rather than a new mechanism — a stuck agent turn becomes a BLOCKED task with a real HumanQA entry, the async equivalent of opencode's synchronous "ask a human before the 4th repeat."
2. **Session compaction** (`app/services/compaction.py`, wired into `FirestoreSessionService._persist`) — resolves the 1 MiB Firestore-document-size risk that `session_service.py` already flagged as a known, deferred gap. Adapted from opencode's tail-budget-verbatim / truncate-tool-output / summarize-older / chain-prior-summaries design, reworked around Firestore's actual byte-size constraint rather than a token-window estimate (the wrong metric for this project — Gemini's context window is not what's actually at risk here).
3. **Gated memory auto-surfacing** (`app/adk_agents/runtime.py`) — a cheap existence check (`store.list_memory`, no embedding call) gates a real semantic-search call, so an agent with no memory yet costs nothing extra on the hottest code path in the app. Complements (doesn't replace) the newly-added `search_memory_tool`, which lets an agent explicitly search on demand.
4. **Extended maker/checker verification** — `engineering_sre` (new `aspects.py`, internal triage/cascade consistency checks) and `hr_people_ops` (handbook answers now carry a `cited_quote`, grounded via the existing `ground_quote()`) join `finance_audit`/`legal_risk`/`marketing_comms`/`customer_support` in using `shared/verification.py` (ADR-0007). `sales_crm`, `product_analytics`, and `executive` were audited and explicitly left unchanged — none of them produce an external claim that verification would meaningfully check.
5. **`create_jira_ticket`** (`departments/engineering_sre/tools.py`) — the one real, concrete gap the tool audit found: `integration_broker.py`'s `jira` template existed but was never called anywhere. Mirrors `notify_slack_channel`'s exact shape (deterministic call site, fail-soft when unconfigured).

## Alternatives considered

- **Adopting opencode's in-process sub-agent/child-session pattern for CEO→department delegation** — rejected. That pattern (fresh session, narrowed permissions, no shared history, result reinjected as a synthetic message) is architecturally the *opposite* of this project's Pub/Sub-based delegation (ADR-0004), which exists specifically because departments are separate services on Cloud Run, not in-process child sessions in a single local process the way opencode's `task` tool assumes. Adopting it would be a strict downgrade for no benefit, not a genuine improvement.
- **Narrowing `spawn_worker`'s tool permissions**, mirroring opencode's sub-agent permission-narrowing — considered and dropped. No concrete evidence of a real problem (workers are already fully session-isolated); adding a permission layer with nothing real behind it would repeat the "unrequested abstraction" mistake this project's own conventions already warn against.
- **Forcing `vote_aspects` onto every department** — rejected for `sales_crm` (its one risky claim, discount %, is already deterministically guarded by `pricing_guardrail` — ADR-0007's pattern, just not routed through the shared module), `product_analytics` and `executive` (both narrate numbers computed deterministically before the LLM ever sees them, with no external claim to mis-ground). Forcing it there would repeat the "don't force fits" mistake already corrected once this session during third-party skill curation.
- **Auto-injecting memory into every turn unconditionally** — rejected in favor of the gated version above; an unconditional embedding call on the single most shared code path in the app, for departments that may have no memory worth surfacing yet, is real avoidable cost for no benefit in the common case.

## Consequences

- ADR-0002 (Python/ADK-only backend) and ADR-0004 (Pub/Sub CEO→department boundary) are unchanged, not amended — nothing here introduces a new framework or replaces the delegation mechanism.
- `session_service.py`'s own `ponytail:` comment is resolved by this ADR's compaction mechanism, not left open — the documented subcollection-migration path remains noted as the next upgrade if compaction alone isn't enough at real scale.
- `THIRD_PARTY_SKILLS.md` gets a new entry attributing the doom-loop guard and compaction design to `anomalyco/opencode` (MIT).
- A security note, for the record: one of the four loop-engineering articles' fetched content contained an "instruction-shaped pattern" that Claude Code's own harness detected and neutralized automatically during research for this ADR, before it could reach the research agent as an instruction. Nothing was acted on; flagged to the user at the time.
