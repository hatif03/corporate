# ADR-0012: A minimal Gemini call budget, no more and no less

Status: Accepted

## Context

The hop-cap of 12 (ADR-0003) bounds message ping-pong between agents, not raw Gemini call volume or spend — a genuine runaway loop (a department stuck re-triggering itself, a bug in a pipeline that keeps re-invoking a stage) could still burn real money indefinitely, and until now nothing stopped that. This was flagged and deliberately deferred once already while the project was still running entirely on mocks; with real billing now active on the deployment account, deferring it again isn't defensible — this is the one item, of several raised as "deliberately not built," whose status genuinely changed.

## Decision

One atomic counter, one choke point, no new service:

- `store.increment_and_check_gemini_budget(org_id, daily_limit)` atomically increments a per-day counter at `orgs/{orgId}/usage/{YYYY-MM-DD}` via Firestore's native `Increment` transform, and reports whether the org is still under `settings.corporate_daily_gemini_call_limit` (default 500, overridable via env var — a config value, not a hardcoded constant, since the right threshold depends on expected demo traffic, not on anything the code itself should decide).
- Checked once, in `app/adk_agents/runtime.py`'s `run_agent_turn` — the single function every agent turn in the app already goes through (CEO and every department pipeline stage alike), so this is one call site, not one per department.
- Over budget raises `RuntimeError("daily Gemini call budget exceeded")`. For a department turn, `@audited_task`'s existing failure path (ADR-0011) catches it, marks the task `BLOCKED` with a real `human_qa` entry, and replies `refuse` — the same visibility path any other department failure already uses. For the CEO-turn branch, `dispatch.py`'s existing top-level safety net (ADR-0011, fix #4) catches and logs it the same way. No new failure-handling code was needed — this rides entirely on the reliability work already in place.

## Alternatives considered

- **A Firestore transaction** for a race-free exact count. Rejected for now — the increment itself is atomic (can't lose a concurrent write), but the follow-up read isn't part of the same transaction, so under concurrent calls the reported count can be off by a small, bounded amount. Acceptable for a circuit breaker meant to catch gross runaway behavior (hundreds of calls), not for exact billing enforcement; the tradeoff and upgrade path are noted inline as a `ponytail:` comment rather than built preemptively.
- **Per-department or per-agent budgets** instead of one per-org counter. Rejected — the actual risk is total spend on the account, not any one department in particular; a single org-scoped counter is the smallest thing that addresses the real concern.
- **A hard-coded limit** instead of a config value. Rejected — the right threshold is an operational judgment call (how much demo traffic is expected), not something the code should bake in.

## Consequences

Every department gets budget protection automatically through `run_agent_turn` and `@audited_task` — no department-level code changes were needed, and none will be needed for future departments either. The known imprecision (a small race window on the read) means this is a circuit breaker, not a precise billing cap; if that distinction ever matters, the transaction-based upgrade path is already documented at the point it would be added.
