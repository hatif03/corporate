# ADR-0011: Dispatch-path idempotency and failure handling

Status: Accepted

## Context

A reliability review of the dispatch path (`app/services/dispatch.py`, `departments/base.py`, `app/api/internal.py`) surfaced three concrete gaps, all confirmed by reading the actual code rather than assumed:

1. **No idempotency on redelivery.** Pub/Sub push is at-least-once delivery. Nothing deduped on the message's own id before running a department pipeline or a CEO turn. A redelivered message re-ran the full Gemini pipeline, appended a second audit-chain entry, published a second reply, and — for Engineering & SRE — could re-fire the Slack notification.
2. **No error handling anywhere in the dispatch path.** `audited_task`'s wrapper had no try/except around calling the department's `on_task_received`; neither did `handle_agent_turn`'s CEO-turn branch, nor `internal.py`'s route handler. Any exception (a Gemini timeout/quota error, malformed LLM JSON, a Pydantic validation error) propagated to a bare 500. That left the task stuck at `DOING` forever (no audit entry, no reply, nothing visible to a human) *and* the 500 told Pub/Sub to retry — which, combined with gap #1, meant a permanently-malformed message would retry indefinitely with no dead-letter policy to ever stop it. The same problem existed for the explicit `400` responses `internal.py` returned on a malformed envelope: Pub/Sub retries on *any* non-2xx status, not just 5xx.
3. **The Ask-me flow was non-functional end-to-end.** `audited_task`'s `needs_human` branch set `has_pending_human_qa=True` but never appended an actual `HumanQA` entry to `task.human_qa` (which defaults to `[]`). `POST /tasks/{id}/answer` indexes into that list expecting an entry to exist — so the first real attempt to answer any blocked task failed with "no such question." Every department that sets `needs_human=True` was affected.

## Decision

- **Idempotency**: `store.mark_message_processed(org_id, agent_id, message_id)` uses Firestore's native `DocumentReference.create()` (raises `Conflict` if the doc already exists) as an atomic check-and-set on `orgs/{orgId}/processed_messages/{agentId}:{messageId}`. Called once at the top of `handle_agent_turn` — the single handler both the real push endpoint and the `LOCAL_DEV` pull loop share — so both get the guard for free. A duplicate is a logged no-op, not a re-run.
- **Failure containment, department path**: `audited_task` now wraps the call to the department's `on_task_received` in try/except. On exception it appends an audit-chain entry recording the failure itself, marks the task `BLOCKED`, appends a real `HumanQA` entry describing the failure, and publishes an `Act.REFUSE` reply to the requester — the same visibility path a deliberate `needs_human=True` result already used, factored into one shared `_ask_human` helper (which is also what fixes gap #3: both the deliberate and the failure path now actually populate `task.human_qa`, not just the boolean flag).
- **Failure containment, general safety net**: `handle_agent_turn` wraps everything after the idempotency check in try/except — covers the CEO-turn branch (which doesn't go through `audited_task` at all) and anything unexpected in `get_department`/`store.get_task`. `internal.py`'s envelope parsing is wrapped the same way, and every response is now 200 (including a rejected/malformed envelope) — Pub/Sub only retries on non-2xx, and retrying can't fix a payload that will always fail to parse.

## Alternatives considered

- **A Pub/Sub dead-letter topic/policy** instead of catching failures ourselves. Rejected: once every failure is caught and acked, there's no failure mode left for a DLQ to catch — Pub/Sub only retries on a non-2xx response, and we no longer produce one for anything we can anticipate. Revisit only if a genuinely unexpected crash (e.g. OOM) that bypasses our own try/except is observed in practice.
- **Retry-with-backoff for transient Gemini errors** (timeouts, rate limits) at the dispatch level. Rejected for this pass — a real, separate robustness feature, but distinct from "don't leave the app broken or silently stuck," which is what this ADR addresses. Left as a follow-up.
- **Porting the reference implementation's actual dedup code** (a per-agent scalar `cursor.json` over a flat-file inbox). Not applicable — that mechanism assumes a single-process, file-based inbox with monotonically-sortable ids; it doesn't map onto Pub/Sub's push-delivery model. What's adapted here is the *principle* (dedupe before processing; never drop a failure silently, always surface it to a human), implemented natively against Firestore/Pub-Sub.

## Consequences

Every department's failure path is now exercised the same way its success path is — through `_ask_human`/`human_qa`, not a special case. New departments get this for free via `@audited_task`; no department-level code needs to change. The tradeoff is that a transient failure (e.g. one Gemini timeout) now surfaces as a blocked task needing human review rather than silently retrying and possibly succeeding on a later attempt — acceptable for now per the "no retry-with-backoff yet" note above, but worth revisiting if transient failures turn out to be common enough in practice to want automatic retry before falling back to human review.
