# Corporate — architecture rules (canonical)

This is the single source of truth for how this codebase is built. `CLAUDE.md` and `.cursor/rules/00-architecture.mdc` both derive from this file — if you change a rule, change it here first, then propagate. See `/docs/adr/` for the reasoning behind each rule; this file states the rule, ADRs state the why.

## Project shape

Corporate is a hosted, cloud-native multi-agent web app: a 2D office-floor UI where department agent teams (Finance & Audit, Engineering/SRE, Legal & Risk, and a growing roster) work under a CEO orchestrator, visible through a "Command Center" dashboard. See ADR-0001.

```
/frontend    React + Vite + TS, Pixi.js office floor, xterm.js trace widget
/backend     Python 3.12, FastAPI, Google ADK
/departments Declarative per-department YAML config
/shared      Cross-language schema definitions
/infra       gcloud/firebase deployment scripts
/docs        ADRs, this file, architecture diagram
```

## Backend: Python only, ADK only

- One language for the whole backend: Python. No department introduces a second language or a second agent framework. (ADR-0002)
- Pin `google-adk==2.7.1`. Requires Python 3.11+. Do not mix ADK 1.x and 2.x session/storage data — the schema changed at 2.0.
- The only LLM in the shipped product is Gemini, via Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=1`), not a raw API key and not any other provider. This is a hackathon eligibility requirement, not a preference.
- Agents are `LlmAgent` instances (or `SequentialAgent`/`ParallelAgent`/`LoopAgent` compositions) built by `app/adk_agents/factory.py`. Use `sub_agents=`/workflow-agent composition only *within* a single department's own pipeline — never for CEO-to-department delegation, which goes over Pub/Sub (see below).
- One Runner session = one agent's turn = one inbound Pub/Sub message. Sessions are Firestore-backed (`FirestoreSessionService`) — never `InMemorySessionService` in a Cloud Run deployment, since instances are ephemeral and a push-per-message architecture can land on a different instance each turn.

## State and messaging

- **Firestore** holds all durable state: `orgs/{orgId}/{agents,tasks,messages,activity_log,board,triggers,workers,agent_sessions,audit_log,integrations,departments,settings}`. Always namespaced under `orgs/{orgId}` — this project is multi-tenant even when only `orgs/demo` is seeded. (ADR-0003)
- **Cloud Storage** holds the one kind of durable state Firestore can't (binary vision attachments) — `app/services/storage_client.py` is the only module allowed to import `google.cloud.storage` directly, mirroring `firestore_client.py`'s rule for Firestore. Task/Message docs only ever hold the resulting `gs://` URI, never raw bytes. (ADR-0013)
- **Pub/Sub** carries live inter-agent messages on a single `agent-bus` topic, one push subscription per agent. Message schema:
  ```jsonc
  { "id", "conversation", "in_reply_to", "from", "to", "act": "request|inform|propose|query|agree|refuse|done",
    "subject", "body", "hops", "requires_reply", "needs_human", "created_at" }
  ```
- `publish_message()` in `app/services/pubsub_client.py` is the *only* place that increments `hops` or resolves `requires_reply` from `act`. Never let an agent's own judgment decide whether a reply is owed, and never bypass this function to publish directly.
- Loop prevention: `hops > 12` blocks the publish, logs `loop-terminated`, and flags the originating task for human review.
- Departments and agents never touch Firestore, Pub/Sub, or the integration broker directly — always through the platform client (`app/services/*`, or `platformClient.ts` on the frontend).
- **Idempotency & failure handling** (ADR-0011): `handle_agent_turn` (`app/services/dispatch.py`) dedupes on `(agent_id, message.id)` via `store.mark_message_processed()` before dispatching anything — a redelivered Pub/Sub message is a logged no-op, never a re-run. `audited_task` (`backend/departments/base.py`) catches any exception a department's `on_task_received` raises, marks the task `BLOCKED` with a real `HumanQA` entry, and replies `Act.REFUSE` to the requester — a department is never allowed to leave a task stuck at `DOING` or crash the dispatch handler. New departments get this for free through `@audited_task`; nothing extra to implement.

## The department contract

Every department is a Python package under `backend/departments/<dept_id>/` exporting a `DepartmentSpec` (id, display name, accepted task types, memory namespace, an `on_task_received` function, contributed verifier "aspect" checkers, optional human-review predicate, optional root ADK agent for A2A exposure). The **only** entrypoint the platform calls is that department's `on_task_received`, with signature `async def on_task_received(org_id: str, task: Task) -> TaskResult` — a plain function, not a class method (departments are stateless modules; their LlmAgents and session service are module-level singletons). Wrap it with `@audited_task(department_id)` from `backend/departments/base.py`, which handles hash-chained audit logging, failure containment, and the task-status/reply writeback (ADR-0011). See ADR-0005. Use the `new-department` Claude Code skill to scaffold a new one — don't hand-roll the package structure.

### Department roster

| id | display name | accepted task types | status |
|---|---|---|---|
| `finance_audit` | Finance & Audit | `review_invoice` | implemented (Phase 1) |
| `engineering_sre` | Engineering & SRE | `handle_incident` | implemented (Phase 2) |
| `legal_risk` | Legal & Risk | `check_decision_conflict` | implemented (Phase 2) |
| `executive` | Office of the CEO | `company_digest` | implemented (Phase 3) |
| `sales_crm` | Sales & CRM | `qualify_lead` | implemented (Phase 3), **A2A-exposed** (`app/a2a_server.py`, ADR-0004) |
| `hr_people_ops` | HR & People Ops | `hr_request` | implemented (Phase 5) |
| `customer_support` | Customer Support | `support_ticket` | implemented (Phase 5) |
| `marketing_comms` | Marketing & Comms | `marketing_request` | implemented (Phase 5) |
| `product_analytics` | Product & Data Analytics | `analytics_query` | implemented (Phase 5) |

All 9 departments from the original roster are now implemented.

(The `new-department` skill appends a row here when it scaffolds a new department.)

## Shared utilities — use them, don't reimplement

- `backend/shared/audit_chain.py` — tamper-evident hash-chained log. Applied automatically via `@audited_task`; you should not need to call it directly.
- `backend/shared/verification.py` — `ground_quote()` (deterministic, no LLM) and `vote_aspects()` (pluggable checker fan-out with retry). Any department producing a claim-with-evidence routes it through this before surfacing it. See ADR-0007.
- `backend/shared/privacy_pipeline.py` — redact-before-LLM PII handling. Any department ingesting user-generated or externally-sourced text/images uses this before it reaches Gemini.

Before writing a new cross-cutting utility, check whether one of these three already covers it.

## Integrations — the broker is the only place a secret materializes

`backend/app/services/integration_broker.py` holds `INTEGRATION_TEMPLATES` (a declarative catalog: slack, jira, github, stripe, notion, hubspot — kind, default base URL, auth type, secret label, docs URL) and `call_integration(org_id, integration_id, method, path, ...)`, the only function anywhere allowed to dereference a Secret Manager `secret_ref` to a real credential. Departments call third-party APIs through `call_integration`, never by holding a raw token themselves. Setting up an integration is write-only for the secret: `POST /api/org/{org_id}/integrations` takes a raw `secret_value` exactly once, writes it straight to Secret Manager via `store_secret()`, and returns only the public config — the value is never stored in Firestore, logged, or echoed back.

First real consumer: `departments/engineering_sre/tools.py`'s `notify_slack_channel`, called directly from `on_task_received` (not exposed as an LLM-invokable tool) when an incident is high-severity — "notify Slack on P1/P2" is mechanism, the same reasoning already applied to `publish_message`'s hop-cap and `requires_reply` derivation.

## A2A — narrow, boundary-only

A2A (`to_a2a()` / `RemoteA2aAgent`, both built into ADK) is used only to expose specific external-facing department agents (Sales and/or Support) as A2A servers for genuinely external callers. It is never used for internal CEO-to-department messaging — that stays on Pub/Sub. See ADR-0004. Don't add A2A anywhere else without a new ADR justifying it.

## Antigravity — evaluated and rejected, don't re-add without re-checking ADR-0014

`google-antigravity` (SDK) and `agy` (CLI) are not dependencies of this project. Both were evaluated empirically (installed, inspected with `inspect` against real installed source, run against live Vertex AI turns — not assumed from docs) and rejected: the SDK has no pluggable persistence that survives a fresh process (incompatible with ephemeral, scale-to-zero, multi-instance Cloud Run), and the CLI's practical headless auth path is a raw Gemini API key, conflicting with this project's Vertex-AI-only eligibility requirement below. See ADR-0014 for the full findings. Department "harness feel" instead comes from curated skill excerpts in prompt files (see `/THIRD_PARTY_SKILLS.md`) and the already-existing `FirestoreSessionService` cross-turn persistence — no new framework.

## Auth & multi-tenancy — defense in depth, two independent layers

Every `orgs/{orgId}/...` collection is namespaced from day one, even with only `orgs/demo` seeded. Two layers enforce it independently (a Security Rule alone isn't sufficient once the backend writes with its own elevated service account):
1. **Firestore Security Rules** (`firestore.rules`, repo root) — a client can only *read* an org's documents if `request.auth.uid` has a doc at `orgs/{orgId}/members/{uid}`; all client writes are rejected outright (writes only ever happen through the backend's service account).
2. **Backend membership check** (`backend/app/services/auth.py`) — `require_org_member` verifies the caller's Firebase ID token *and* their `orgs/{orgId}/members/{uid}` role, wired as a router-level dependency on every `/api/org/{org_id}/*` router in `app/main.py` (not per-endpoint, so a new endpoint can't accidentally ship without it). `require_role("owner")` is available for owner-gated actions. `/internal/*` routes are deliberately excluded — those are Pub/Sub-push/Cloud-Scheduler targets authenticated via IAM/OIDC, not end-user tokens.

Granting org membership is currently manual (`scripts/seed.py --owner-uid <uid>`) — there's no self-service invite flow yet.

## Secrets

- All third-party credentials (Slack, Jira, Stripe, etc.) live in **Secret Manager**, referenced from Firestore `integrations/{id}.secretRef` — never the raw value in Firestore, code, or `.env` committed to git.
- `.env.example` documents every required environment variable with placeholder values; real `.env` files are gitignored.
- The integration broker (`app/services/integration_broker.py`) is the only module where a secret is ever dereferenced to its real value.

## Testing

- Every department ships `tests/test_<dept_id>_smoke.py` — at minimum, one call through `on_task_received` with a representative task and an assertion on the writeback.
- Shared utilities (`audit_chain.verify_chain()`, `verification.ground_quote`/`vote_aspects`) have their own unit tests, including at least one deliberate-tamper / deliberate-ungroundable-claim test proving the failure path actually fires.

## Ponytail

Enforcement level is phase-dependent: `lite` while building the three core departments, `full` once building the wider department roster from scratch. Never `ultra` given the deadline. See ADR-0008. Update this section and `.cursor/rules/ponytail-hackathon.mdc` together if the phase changes.

## Version control & documentation discipline

- One commit per meaningful architectural change, conventional-commit style (`feat(finance): ...`, `chore(infra): ...`), referencing the relevant ADR in the body (`Refs: ADR-0003`) when applicable.
- README.md is a living document — update it in the same commit as any change to setup/deploy steps, dependencies, or the department roster.
- Any new non-obvious architectural decision gets an ADR in `/docs/adr/` (template: `TEMPLATE.md`) — don't defer writing it.

## Definition of done (per PR/change)

- [ ] Code follows the conventions above (Python/ADK-only, platform-client-only Firestore/Pub-Sub access, secrets via Secret Manager)
- [ ] Tests added/updated and passing
- [ ] README updated if setup/deploy/dependencies changed
- [ ] New ADR added if a non-obvious architectural decision was made
- [ ] `.cursor/rules/00-architecture.mdc` still matches this file (no drift)
