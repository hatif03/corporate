# ADR-0003: Firestore for state, Pub/Sub for inter-agent messaging

Status: Accepted

## Context

Following ADR-0001's cloud-native pivot, agent state (rosters, tasks, memory, activity) and inter-agent messages need a persistence and delivery mechanism that survives Cloud Run's stateless, horizontally-scaled, scale-to-zero execution model — no single instance can be assumed to hold state in memory or on a local disk between requests.

## Decision

- **Firestore** holds all durable state: the agent roster, the task kanban, per-agent memory, the activity log, ADK session data, and a mirrored copy of every inter-agent message (for UI/audit querying).
- **Pub/Sub** carries live inter-agent message delivery: a single `agent-bus` topic, with one push subscription per agent filtered by a `to` attribute, delivering to a Cloud Run push endpoint per agent.
- Messages follow a fixed schema: `{id, conversation, in_reply_to, from, to, act, subject, body, hops, requires_reply, needs_human, created_at}`, where `act` is one of `request|inform|propose|query|agree|refuse|done`.
- A single chokepoint function (`publish_message()`) owns hop-counting and loop prevention: it increments `hops` per conversation and blocks any publish once `hops > 12`, flagging the originating task for human review instead of looping forever. `requires_reply` is derived mechanically from `act`, never left to agent judgment.

## Alternatives considered

- **A single Firestore-only design** (agents poll a Firestore `inbox` collection instead of using Pub/Sub). Rejected: polling doesn't fit Cloud Run's request-driven scaling model as cleanly as a push subscription does, and would either waste cost on idle polling or add latency.
- **No hop cap / reply-obligation left to LLM judgment.** Rejected: an LLM agent can plausibly decide two messages "need" a reply back and forth indefinitely; a mechanical cap is cheap insurance and doesn't rely on the model behaving.

## Consequences

Every department implementation talks to state exclusively through a platform client (never raw Firestore/Pub-Sub calls) — this is enforced as a project rule (see `/docs/system_prompt.md` and `.cursor/rules/firestore-access.mdc`). The CEO agent has no special-cased routing logic; it is "just another agent" with elevated tool grants, and all orchestration mechanics live in `publish_message()`, not in any agent's prompt.
