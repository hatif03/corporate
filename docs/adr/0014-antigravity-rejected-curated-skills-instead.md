# ADR-0014: Google Antigravity rejected as a harness layer; curated skills added as prompt excerpts instead

Status: Accepted

## Context

A request to make department agents feel less like one-shot chatbot replies and more like a real multi-agent harness — persistent stateful sessions, native skill-loading, self-directed behavior — led to evaluating Google Antigravity (`google-antigravity` on PyPI, and the separate `agy` CLI) as a harness layer, since it's the Google-only stack this project is locked to and already listed as an optional future dependency.

Empirical spikes (installing the real package, inspecting real installed source with `inspect`, and running live turns against Vertex AI — not trusting documentation prose) found three separate, independent blockers:

1. **Dependency conflict.** `google-antigravity==0.1.14` requires `protobuf>=7.35`; `a2a-sdk==1.1.2` (pulled in by `app/a2a_server.py`'s use of `google.adk.a2a.utils.agent_to_a2a`) requires `protobuf<7`. This alone was resolvable (splitting the main backend and the standalone A2A service into separate dependency closures — they already deploy as separate Cloud Run services), but was superseded by the next two findings.
2. **No pluggable persistence.** The installed SDK has no `BaseDb`, no `AntigravityAgent`, no `SqliteDb`/`PostgresDb` — none of what the docs pages described. The real API (`Agent`, `AgentConfig`, `LocalAgentConfig`, `Conversation`) has no public parameter anywhere to inject a prior turn's history into a fresh session. The only continuation mechanism (`conversation_id` + `session_continuation_mode`) is wired through `LocalConnectionStrategy`, tied to local disk (`save_dir`/`app_data_dir`) — exactly the single-machine dependency this project's ephemeral, scale-to-zero, multi-instance Cloud Run deployment cannot tolerate. The only way to inject history manually is reaching into a private `conn._initial_history` attribute — an unsupported internal on an early 0.1.x (Alpha) package, not a stable extension point.
3. **Eligibility conflict (CLI).** As an alternative, the separate Antigravity CLI (`agy`) was evaluated — it does support real session resumption (`--conversation <id>`) unlike the SDK. But its documented headless/automatable auth path is a raw `GEMINI_API_KEY`, not Vertex AI. `/docs/system_prompt.md` states Vertex AI (not a raw API key, not any other provider) is a hackathon eligibility requirement, "not a preference." The one auth path that might route through Vertex AI (an interactively signed-in Google Cloud org account with Gemini Code Assist/Vertex AI licensing) is not headless-friendly and is contested even for legitimate users (see a real user's IAM permission failure on this exact path, google-antigravity/antigravity-cli#437).

## Decision

Stay on ADK everywhere, as before this investigation. No Antigravity dependency (SDK or CLI) is added. The "feels like a real harness, not a one-shot chatbot" goal is pursued through two changes that need no new framework:

- **Curated skill excerpts**: a short, adapted, attributed excerpt from a real open-source MIT-licensed skill appended directly to the relevant pipeline-stage prompt file, for stages where a genuine domain-technique fit exists. See `/THIRD_PARTY_SKILLS.md` for the full list and sources. No new loading mechanism — these are plain text appended to the same `.md` files `_load_prompt()` already reads.
- Department sessions already persist across turns via the existing `FirestoreSessionService` (session_id == agent_id) — the "no memory between turns" gap assumed at the start of this investigation didn't actually exist once verified against the real session service.

## Alternatives considered

- **DIY Firestore persistence via `conn._initial_history`** — rejected: relies on an undocumented private attribute of an Alpha package that could break on any point release with no warning, days before a hackathon deadline.
- **Stateless per-turn Antigravity, for `skills_paths` and hook-based tool transcripts only** — rejected: `skills_paths` native loading isn't worth taking on a new framework dependency for, once curated-excerpt prompts already deliver equivalent domain guidance with zero new risk.
- **Antigravity CLI on a single always-on machine** ("it doesn't have to scale, it just needs to be a demo") — rejected on the eligibility finding above, not on the deployment-shape concern (a single persistent VM for a demo would have been an acceptable trade).
- **Literal "drain the inbox, keep working" lifecycle hook**, ported from Antigravity's hook API — dropped as a concept, not just an Antigravity dependency: this project's Pub/Sub push architecture already dispatches every task as its own message/request the moment it's created, so there's no backlog queue for an agent to "drain" the way a long-lived local process would have one.

## Consequences

- ADR-0002's "Python-only, ADK-only" backend rule is unchanged, not amended — no new framework was introduced.
- Skill curation review (checking each shortlisted skill's *actual* content, not just its name/description) caught two skills that didn't genuinely fit their assigned department task (`security-guidance`, an editor hook not domain knowledge; `saas-metrics-coach`, ARR/MRR coaching irrelevant to per-invoice AP review) and one department reassignment (`revops` fits `lead_qualifier` far better than `deal_strategist`) — all corrected before landing, per this project's "don't force fits" convention already established for the department/skill survey.
- If Antigravity's SDK ships real `BaseDb`-equivalent pluggable persistence in a later release, or the CLI adds a documented Vertex AI / service-account headless auth path, this decision is worth revisiting — but not before the 2026-08-31 deadline.
