# Project history — decisions, explorations, and what we let go

This is the narrative companion to `/docs/adr/` — the ADRs are the
authoritative, per-decision record (context/decision/alternatives/
consequences); this document is the connective story across all of them,
plus the things that never became a numbered ADR (UI passes, research
spikes that led nowhere, deployment debugging) but were real work with real
reasoning behind it. Read this for "how did we get here and why"; read the
ADRs for "what exactly did we decide and what's the precise tradeoff."

Corporate is a hosted multi-agent web app built for the **All Things
Agentic** hackathon (track: The Fortified Enterprise Fleet, deadline
2026-08-31): departments of autonomous AI employees working on a 2D office
floor, coordinated by a CEO agent, visible through a "Command Center"
dashboard. Everything below happened inside that constraint set: hosted
(not desktop), Gemini-via-Vertex-AI only, Google ADK only, a hard deadline.

## Phase 0 — foundations

The very first decisions were about *shape*, before any department existed:

- **Hosted, not desktop** (ADR-0001). An early direction modeled Corporate
  as a local app spawning agent processes on the user's own machine, with a
  thin cloud-sync layer bolted on just to technically touch Google Cloud.
  Rejected — the hackathon needs a real hosted URL and *load-bearing* Google
  Cloud usage, not peripheral. A "desktop for dev, cloud for submission"
  hybrid was also considered and rejected as duplicated effort with no
  concrete feature to justify it.
- **Python/ADK only, no polyglot departments** (ADR-0002). Each department
  could in principle pick its own best-fit language. Rejected in favor of
  one language, one framework, one Firestore/Pub-Sub client — a coherent
  stack scores better against "Architectural Discipline" than a patchwork,
  and Python has ADK's most mature SDK anyway.
- **Firestore for state, Pub/Sub for messaging** (ADR-0003). A Firestore-only
  design (agents polling an inbox collection) was considered and rejected —
  polling doesn't fit Cloud Run's request-driven scaling, and either wastes
  cost idling or adds latency. Pub/Sub push, one topic + per-agent filtered
  subscriptions, won. A mechanical hop-cap (`hops > 12`) and mechanical
  `requires_reply` derivation were chosen over trusting an LLM's own
  judgment about whether a reply is owed — cheap insurance against an agent
  plausibly deciding to ping-pong forever.
- **A2A at the external boundary only, never internally** (ADR-0004). ADK
  has first-class A2A support, and it would be possible to route all
  internal CEO→department messaging over it. Rejected — no external,
  cross-vendor, opaque-agent problem exists internally, and A2A's
  request/response shape fits Cloud Run worse than Pub/Sub's push/fan-out
  for that traffic. Skipping A2A entirely was also considered, but the
  narrow use — exposing Sales/Support as real A2A servers for genuinely
  external callers — was kept because it gives a real "Fortified Enterprise
  Fleet" trust-boundary story instead of ignoring a protocol ADK explicitly
  built for exactly this seam.
- **One `DepartmentSpec` contract for every department** (ADR-0005). The
  alternative — each department wiring its own Firestore/Pub-Sub access as
  needed — was rejected outright as the exact "everyone reinvents their own
  plumbing" risk a fixed contract exists to prevent. `on_task_received` is
  the *only* entrypoint the platform ever calls, wrapped in `@audited_task`
  for audit logging and failure containment.
- **Ponytail enforcement phasing** (ADR-0008). `lite` while the three core
  department designs were being established (getting a working end-to-end
  loop mattered more than minimality yet), moving to `full` once building
  the from-scratch wider roster (five to six new departments is exactly
  where over-engineering risk compounds). `ultra` was never on the table,
  given the deadline.

## Phase 1–3 — core departments, then the full roster

Built in order: **Finance & Audit** and a minimal frontend first (proving
the CEO↔department loop over real Pub/Sub), then **Engineering & SRE** and
**Legal & Risk**, then **Office of the CEO** (digest agent) and **Sales &
CRM** (the one department exposed over live A2A), then **Triggers &
Workers** (schedule/webhook triggers, ephemeral one-off workers), then **HR
& People Ops** and **Customer Support**, then **Marketing & Comms** and
**Product & Data Analytics** — completing all 9 originally planned
departments.

Two structural decisions came out of building the first three:

- **Fraud detection stays Gemini-only; independence comes from structure,
  not model diversity** (ADR-0006). A second LLM provider dedicated to
  fraud detection was evaluated and rejected — the project's hard
  Gemini-only constraint stands, and the added integration/cost/latency of
  a second provider for one narrow stage wasn't worth it. Instead, Stage 2
  (fraud judgment) is a *fresh* Gemini call that only ever sees Stage 1's
  deterministic signal JSON — never the classification agent's own
  reasoning — so it can't just rationalize a prior framing. Self-consistency
  sampling was noted as an available future enhancement, not required.
- **High-stakes claims are deterministically grounded, never trusted from
  raw LLM output** (ADR-0007). Trusting an LLM's self-reported confidence
  score was rejected — confidence scores aren't reliably calibrated to
  actual groundedness. A second LLM call double-checking the first was also
  rejected as the *sole* mechanism, since it's still LLM-mediated and can
  share the same failure mode. What shipped: `ground_quote()` (deterministic
  string matching, no LLM — an unlocatable quote means the claim is
  *dropped*, not "corrected") and `vote_aspects()` (N independent pluggable
  checkers, two-thirds agreement, one retry). An LLM may judge or propose;
  only deterministic code verifies.

Sales & CRM needed one genuine directly-invokable ADK agent object (for
`to_a2a()` to expose), unlike the other departments' plain-Python
orchestration. That meant `SequentialAgent` — already deprecated in ADK
2.7.1 in favor of a new graph-based `Workflow` API, but the only option that
still worked without spending scarce time learning and correctly
implementing an unfamiliar graph API under deadline pressure. Documented as
known, tracked debt (ADR-0009), not an oversight — worth revisiting for the
whole department layer if `Workflow` becomes the standard, but not before
the deadline.

## Hardening pass — auth, idempotency, cost

Once the department roster was real, three reliability/security gaps got
closed:

- **Auth, two independent layers** (ADR-0010). Firestore Security Rules
  alone was rejected — it doesn't protect the backend's own write path,
  since the backend writes with an elevated service account, not a
  per-user token. A backend-only check with permissive Firestore rules was
  also rejected — the frontend reads most state directly via `onSnapshot`,
  so a leaked client reference would read any org's data with no rule to
  stop it. Both layers ship, neither alone considered sufficient.
  Router-level `require_org_member` wiring (not per-endpoint) was chosen
  specifically so a new endpoint can't accidentally ship unauthenticated.
- **Dispatch idempotency and failure handling** (ADR-0011). A reliability
  review of the actual dispatch path (not assumed, read directly) found:
  no dedup on Pub/Sub redelivery, no error handling anywhere in the
  path (an exception left a task stuck at `DOING` forever *and* told
  Pub/Sub to retry indefinitely), and the Ask-me flow was non-functional
  end-to-end (`has_pending_human_qa` was set but the actual `HumanQA` entry
  the answer endpoint indexes into was never appended). A Pub/Sub
  dead-letter policy was considered instead of catching failures ourselves
  — rejected, since once every anticipated failure is caught and acked,
  there's no failure mode left for a DLQ to catch. Retry-with-backoff for
  transient Gemini errors was scoped out as a separate, later concern.
  Fixed: atomic check-and-set idempotency via Firestore's native `create()`
  Conflict semantics, and a shared `_ask_human` failure-containment path
  that both a department's real exception *and* a deliberate
  `needs_human=True` now route through identically.
- **A minimal Gemini call budget** (ADR-0012). Previously deferred while
  running entirely on mocks; not defensible once real billing went live.
  A Firestore transaction for an exact race-free count was considered and
  rejected — the atomic `Increment` plus a non-transactional follow-up read
  is close enough for a circuit breaker meant to catch gross runaway
  behavior, not exact billing enforcement (documented inline as the
  precise, intentional imprecision). Per-department budgets were rejected
  too — the real risk is total account spend, not any one department.

## Capability pass — search, tiering, vision, per-org budget

Live testing surfaced a real gap: an open-ended research goal got routed to
`product_analytics` (correctly scoped only to internal task/SLA metrics),
which declined it — correctly, but the decline reason was itself invisible
until fixed separately. At the same time the fixed 500/day Gemini budget
was found to risk blocking a live demo outright with no way to raise it
short of a redeploy. Four things shipped together (ADR-0013), all
constrained by the same fact: department `LlmAgent`s are module-level
singletons built once at import time, not per-request.

- **Universal Google Search** on every agent, via ADK's documented
  `GoogleSearchAgentTool` workaround for combining the built-in
  `google_search` grounding tool with custom function tools.
- **Per-task model tiering**, CEO-decided at `create_task` time
  (`model_tier: "flash"|"pro"`). Mutating a shared singleton's `.model`
  per-turn was rejected outright as a real race condition the moment two
  orgs' turns overlap on Cloud Run — instead, two full singletons per
  pipeline stage. A deterministic priority→tier rule was considered and
  rejected too — priority already means urgency, not complexity, and would
  need a second field regardless.
- **Vision attachments via Cloud Storage**, not base64-in-Firestore — the
  original draft used base64, rejected once the ~700KB effective ceiling
  (after base64 inflation, under Firestore's 1MiB/doc limit) was flagged as
  too low for real screenshots/photos. `Part.from_uri()` reading the GCS
  object directly turned out to be the more natural Vertex AI integration
  anyway. `include_attachment` defaults to `True` (not opt-in) — an LLM
  asked to remember an optional flag on every `create_task` call is exactly
  the kind of thing that silently gets dropped.
- **Per-org configurable Gemini budget**, raised fallback from 500 to 5000
  so the global default stops being a demo-blocking trap while still
  catching a genuine runaway loop, with a real Settings tab to change it
  without a redeploy.

## UI evolution — from boxes to a real office, with real attribution

Separately from the backend work, the frontend went through several real
passes rather than one shot:

- Kenney's CC0 RPG Urban Pack tiles were adopted for the office floor
  (`ef9263e`, `fda92a5`) — walking character sprites with idle/walk-frame
  animation, replacing placeholder boxes. Tile indices were repeatedly
  **verified by rendering and individually inspecting the actual tile
  PNGs**, not guessed from the packed tilemap thumbnail (too small to read
  reliably) — a discipline that recurs throughout this project wherever a
  visual asset choice mattered.
- A "harness-grade UI" pass (`ae13bab`, `bd5f2e1`) adapted the color
  palette, type scale, spacing scale, shadow/border system, and CSS
  animation mechanics from an MIT-licensed reference design system
  (`chaitanyagiri/munder-difflin` — see `THIRD_PARTY_SKILLS.md` for full
  attribution). Fonts, color tokens, and interaction timings are a close
  adaptation; the office-floor scene, agent/department content, and all
  product copy are original — no branded characters or copy from the
  reference are reproduced. This same pass added the animated office scene
  layer: a continuous "breathing" bob so no sprite ever looks frozen, a
  slow ambient wander for idle agents, a pulsing glow under active agents,
  and a swaying office plant.
- This session's own layout/office-scene overhaul (see below) went further
  after the user reviewed real screenshots of that same reference app's
  running UI and found the earlier pass's *layout* (not just its tokens)
  still didn't match — a second, deeper adaptation pass, not a one-shot
  copy.

## Deployment infrastructure

`docs/ARCHITECTURE.md`, a `Dockerfile`, and `/infra/deploy/setup.sh` +
`deploy.sh` were written to take the project from local-only to a real
Cloud Run + Firebase Hosting deployment (`99eb88f`). Getting there in
practice surfaced and fixed several real, live issues rather than
theoretical ones: Cloud Build's default service account needed explicit
Storage/Artifact Registry IAM grants on a tightened-default project
(`935a6d6`); `/internal/*` routes needed real Pub/Sub OIDC token
verification once the backend had to be deployed `--allow-unauthenticated`
(`0a31814` — Cloud Run's own IAM gate can't coexist with a publicly
browser-reachable `/api/org/*` on the same service); the A2A card wasn't
reachable and the Firestore client wasn't reading correctly on first deploy
(`fd3892a`); and `deploy.sh`'s Firestore-seed step needed to explicitly use
the venv's own Python (`ca877a1`). Billing availability gated how much of
this could be exercised end-to-end against a live project at any given
point in the timeline — see the individual commits for what was verified
live versus what was written and reviewed but not yet run against a live
project as of that point.

## Research digression 1 — Google Antigravity: evaluated, rejected

A request to make department agents feel like a real persistent, stateful
multi-agent harness rather than one-shot chatbot replies led to evaluating
Google Antigravity (`google-antigravity` SDK + the separate `agy` CLI) —
the Google-only stack this project is locked to anyway. This was a real
empirical spike, not a docs read: the actual package was installed,
inspected with `inspect` against real installed source, and run against
live Vertex AI turns (ADR-0014). Three independent blockers surfaced:

1. A resolvable `protobuf` version conflict with the A2A SDK.
2. **No pluggable persistence that survives a fresh process** — the real
   installed API had none of what the docs described (no `BaseDb`, no
   `SqliteDb`/`PostgresDb`); the only continuation mechanism was tied to
   local disk, which an ephemeral, scale-to-zero, multi-instance Cloud Run
   deployment can't tolerate. The only way to inject history manually was
   reaching into a private, unsupported internal attribute on an early
   Alpha package — rejected as too fragile days before a deadline.
3. The CLI's real headless auth path was a raw Gemini API key, not Vertex
   AI — directly conflicting with this project's own stated hackathon
   eligibility requirement.

**Let go entirely**: no Antigravity dependency, SDK or CLI. What shipped
instead needed no new framework at all: curated, attributed excerpts from
real MIT-licensed skills appended directly into the relevant department
prompt files (see `THIRD_PARTY_SKILLS.md`), plus the discovery — once
actually checked — that department sessions already persist across turns
via the existing `FirestoreSessionService`, so the "no memory between
turns" gap the investigation started from didn't actually exist. Curating
those skills also caught two that didn't genuinely fit their assigned
department (`security-guidance`, an editor hook, not domain knowledge;
`saas-metrics-coach`, irrelevant ARR/MRR coaching for per-invoice review)
and one misassignment (`revops` fits lead qualification better than deal
strategy) — corrected before landing rather than forced to fit.

## Research digression 2 — opencode: patterns adopted, framework rejected

A request to study a real, mature open-source coding agent
(`anomalyco/opencode`, MIT, real source read via `gh api`) plus four
outside "loop engineering" sources led to reimplementing several concrete
patterns *natively* against this project's own ADK/Firestore stack, with no
new framework or dependency (ADR-0015):

- A doom-loop guard + per-turn tool-call cap (same tool, byte-identical
  args, 3 times in a row → `RuntimeError`, routed through the existing
  `@audited_task` failure path).
- Session compaction, resolving a previously-flagged, previously-deferred
  1 MiB Firestore-document-size risk — reworked around Firestore's actual
  byte-size constraint rather than a token-window estimate (the wrong
  metric here, since Gemini's context window isn't what's actually at
  risk).
- Gated memory auto-surfacing — a cheap existence check gates a real
  semantic-search call, so an agent with no memory yet costs nothing extra
  on the hottest code path in the app.
- Extended maker/checker verification into `engineering_sre` and
  `hr_people_ops`, and added the one real gap a tool audit found:
  `create_jira_ticket` (the `jira` integration template existed but was
  never called anywhere).

**Let go**: opencode's in-process sub-agent/child-session pattern for
CEO→department delegation — rejected as architecturally the *opposite* of
this project's Pub/Sub-based delegation, which exists specifically because
departments are separate Cloud Run services, not in-process child sessions
in a single local process. Narrowing `spawn_worker`'s tool permissions
(mirroring opencode's sub-agent permission-narrowing) was considered and
dropped — no concrete evidence of a real problem to justify it. Forcing
`vote_aspects` onto every department was rejected for `sales_crm` (already
deterministically guarded elsewhere), `product_analytics`, and `executive`
(both narrate deterministically-computed numbers with no external claim to
mis-ground) — the same "don't force fits" principle applied again.

## This session — layout/office-scene overhaul + agent capability expansion

Triggered by the user reviewing real screenshots of the reference app's
running UI and concluding the earlier design-token adaptation wasn't
enough — the *layout* itself (roster position, dashboard position, office
scene scale/detail, icons, collapsible sections, agent personas) still
didn't match — plus a batch of genuine platform questions the project
hadn't answered yet: how does an org customize an agent, connect its own
data, control which department can use which integration (and let an agent
request access it doesn't have), and can agents spawn sub-agents or combine
several of their own tool calls into one round trip.

**Research, both explored and rejected**: Anthropic's real Programmatic
Tool Calling (a Claude-API-specific beta — Anthropic-hosted stateful code
containers, `allowed_callers`/`caller` attribution) was fetched and read
directly, then confirmed **not usable** — this backend is Gemini-via-
Vertex-AI-only, a hard eligibility requirement, not a preference. The
linked "speculative PTC" research (a token-stream-level inference-server
optimization requiring raw partial-generation access) was likewise
confirmed not implementable against ADK's `Runner.run_async`. What was
genuinely portable — letting an agent orchestrate several of its own tool
calls in one snippet instead of many round trips — was reimplemented
natively as the sandboxed `execute_python` tool (below), the only actual
takeaway from that research thread.

**A first plan was presented and rejected** by the user, with three
specific, concrete corrections, all honored in the revision: (1) the
header's plain `org: demo` text and generic profile icon needed fixing, and
the sign-in page needed real design treatment, not a placeholder screen;
(2) no emoji anywhere in the UI, including the pre-existing 👑 CEO badge —
use a real icon library, not just avoid adding new emoji; (3) the frontend
needed a real, visible way to see every connected integration, not just an
admin-config toggle buried in a form.

**Frontend, shipped:**

- Sidebar given a real height constraint (was silently causing page-level
  scroll instead of scrolling internally).
- `App.tsx` restructured from a swap-on-select single-column layout into
  Sidebar / office scene (always mounted — no more destroying and
  rebuilding the whole Pixi application, and its animation state, on every
  agent click) / a right-hand dashboard-or-agent-detail column.
- The office floor rebuilt as a genuine 3×3 room-and-corridor grid
  (replacing 9 small, differently-shaped zones including one oddball wide
  strip) inside a responsive Pixi `world` container that rescales to fit
  whatever screen space is actually available, with real tiled walls,
  doors, corridor floors, and a bookshelf — tile indices for all of it
  re-verified the same render-and-inspect way as every earlier tile choice
  in this project, not guessed. A bordered-room tile family and several
  alternate door/corridor tiles were found and explicitly **not used** —
  the simpler, already-confirmed set was chosen to keep the rewrite
  tractable, and no water-cooler-shaped tile exists anywhere in the pack
  (confirmed by full visual review) so that prop was skipped rather than
  forced.
- Every emoji glyph replaced with `lucide-react` icons (a new,
  MIT-licensed, tree-shakeable dependency — each intended icon name was
  confirmed to actually exist in the installed package before use, not
  assumed), including the CEO crown badge.
- Real per-agent personas (original names/bios, no resemblance to any
  media property) replacing generic department-name placeholders, which
  also fixed a real bug: two agents sharing one zone (CEO + Office of the
  CEO, both in the executive room) previously rendered as visually
  identical sprites because sprite-variant selection hashed the
  *department*, not the agent.
- A real header (Google-account avatar via Firebase Auth's already-present
  `photoURL`, a styled org badge instead of plain text) and a redesigned
  sign-in landing page.
- Collapsible sections for Triggers (Schedules/Webhooks) and Commands —
  deliberately **not** added to Settings, which is one flat panel with
  nothing to usefully collapse.

**Backend, shipped** (see ADR-0016 for the full decision record):

- **Per-department integration access control**, reusing
  `Integration.connected_departments` — a field that already existed on
  the model and was already written by the create-integration form, but
  had never once been read. Empty means unrestricted (every existing
  integration's actual behavior, unchanged); non-empty is a strict
  allowlist enforced in `call_integration`, the one function every
  integration call already goes through. A denial files a standing
  `access_requests` doc for an owner to resolve, rather than blocking the
  task itself — a permission decision is a governance-timescale call, not
  a per-task one (rejected: routing it through the existing
  `_ask_human`/`TaskStatus.BLOCKED` path, since the existing integration
  call sites are deliberately fail-soft already). The frontend gained a
  real "Connected apps" panel and a pending-requests panel, directly
  answering the user's third correction above.
- **An org-uploadable knowledge base** per department, falling back to each
  department's existing static corpus when nothing's been uploaded — a
  fresh org behaves identically to before. Explicitly **not** embedded or
  searched (rejected) — the static corpora it replaces were never searched
  either, only inlined whole into the prompt, so there's nothing yet for a
  vector index to improve on.
- **Sub-agent spawning**, reusing the existing ephemeral `spawn_worker`
  mechanism rather than reopening the Pub/Sub-only CEO↔department boundary
  (ADR-0004) — a synchronous `spawn_worker_and_await` sibling with a 120s
  timeout returns a delegated sub-task's real result inline. The depth cap
  is **structural, not counted**: the new tool is wired only to the CEO and
  two departments, and deliberately kept out of the tool list the
  ephemeral worker agents themselves get — a spawned worker cannot spawn
  another one because it was never given the tool to do so, not because a
  counter stopped it. A per-turn depth counter was considered and rejected
  for exactly that reason — a counted limit can be gamed or miscounted;
  structural absence cannot.
- **A sandboxed `execute_python` tool**, the one concrete, portable idea
  salvaged from the PTC research above. A bare in-process `exec()` with a
  builtins allowlist was rejected outright — the classic
  `().__class__.__bases__` gadget defeats it, and a CPU-bound `while True`
  can't be force-killed in-process either way. RestrictedPython alone
  (in-process) was also rejected as insufficient on its own — it closes the
  gadget but still can't bound wall-clock time. What shipped: a real OS
  subprocess as the actual isolation boundary (only a real process can be
  `kill()`ed regardless of what's running inside it), with
  RestrictedPython's `compile_restricted` running inside that subprocess as
  defense-in-depth on top. This was verified live, not assumed: a
  malicious `import os` snippet was rejected by the real subprocess; a
  `while True: pass` snippet actually ran for the full timeout and was
  actually killed by the parent process; and a multi-lookup task completed
  in one real round trip instead of N. The child process never imports
  `app.services.store` or holds any credential — a whitelisted, read-only
  `call_tool(name, **kwargs)` (`list_tasks_tool`, `list_agents_tool`,
  `search_memory_tool`, `read_memory`) is serviced entirely by the parent
  over line-delimited JSON on stdio. Write tools were deliberately **left
  out of the allowlist** — they stay individually visible in the outer
  turn's own trace/audit log rather than proxied opaquely through a
  snippet, pending a real sandboxed-write audit design that doesn't exist
  yet.

## Voice, OAuth connect, and the Gemma-to-Gemini-tier correction

Three more real features landed after the layout/capability overhaul above, each with its own ADR:

- **Realtime voice** (ADR-0017): studying the reference app's own voice feature (a second LLM provider's Realtime API) led to real research into whether Vertex AI has an equivalent — confirmed yes, `client.aio.live.connect()`, GA, ADC-authenticated, no new provider needed. The hard constraint that shaped the whole design: Vertex's Live API has no ephemeral-token path, so a browser can never hold the credential directly — the backend has to be a real WebSocket relay, holding ADC credentials and piping raw PCM audio both ways, never handing anything else to the browser. v1 scope is deliberately a voice *conversation* with the CEO's persona, not yet wired to its actual tools (`create_task` etc.) — that needs `Runner.run_live`/`LiveRequestQueue`, seen in ADK's own source but not independently verified this pass, so it was left as a real follow-up rather than shipped unverified.
- **OAuth "Connect with X"** (ADR-0018) for Slack, GitHub, and Notion — replacing "paste a raw token" with a real consent-screen flow. Real per-provider research surfaced genuine transport differences (form-POST vs. JSON-body client-secret submission) that made one shared OAuth helper actively wrong, so each provider got its own small adapter instead. Surfaced and fixed a real pre-existing bug along the way: `call_integration()` only ever attached an `Authorization` header for `BEARER`-type credentials — `OAUTH2` silently fell through with no header at all, meaning every OAuth-connected integration would have been silently broken had this not been caught.
- **Gemma, Veo, Lyria via Vertex AI** (ADR-0019) — the hackathon's bonus-model scoring calls out Gemma/Veo/Lyria by name, and a cross-model "second opinion" checker was independently wanted for hallucination mitigation on top of the existing citation-grounding check. Live-testing (not trusting Model Garden's docs) found Gemma unreachable in this project at any tier — every variant's card showed only a paid, self-hosted "Deploy model" button, never the zero-deployment MaaS path the ADR assumed, and the same was true of every other open-model alternative tried (Llama, Mistral, Codestral, Jamba). Self-hosting a GPU endpoint for one aspect checker was explicitly rejected given the deadline. The independent-review checker shipped anyway, just on a distinct Gemini tier instead of Gemma — still a genuinely separate model call with fresh context, just not a different vendor, and the ADR says so plainly rather than quietly dropping the "cross-model" framing. Veo and Lyria, by contrast, were confirmed fully live-working — including catching a wrong field name in Lyria's response parsing that a search-engine-summarized "verified" example had gotten wrong.

## Hackathon submission push — eligibility, full observability, and going live

With the 2026-08-31 deadline three days out, a submission-readiness pass turned up one hard, previously-unnoticed problem and a real, previously-undiscovered production bug, alongside the frontend/documentation polish that had been explicitly requested:

- **Gemini 3.5 eligibility** (ADR-0020): re-reading the hackathon's own rules directly (not from memory) surfaced a hard requirement — "Gemini 3.5 or newer" — that this project's 2.5-tier default models didn't meet. Same live-testing discipline as the Gemma correction above: `client.models.list()` against this project's real Vertex AI access found `gemini-3.5-flash`/`gemini-3.5-flash-lite`/`gemini-3.1-pro-preview` all reachable (3.5 Pro has no public model id anywhere yet), but only at Vertex's `global` location — the 2.5-tier models this project already used are pinned to `us-central1`. Reading ADK's own installed source (`google.adk.models.google_llm.Gemini.api_client`) showed it never passes an explicit location at all, and `google.genai`'s own client already silently defaults to `global` whenever `GOOGLE_CLOUD_LOCATION` is unset — which it always has been here — so the region mismatch that looked like it might need new plumbing turned out to need zero code change beyond the model id strings themselves, confirmed with a real end-to-end ADK turn before committing any of it.
- **A real, previously-undiscovered production bug**: auditing whether ephemeral workers' execution was visible anywhere in the frontend led to reading `update_agent_status`'s Firestore call closely enough to notice it does an `.update()` — which throws `NotFound` on a document that was never created. Every worker's session id doubles as its "agent id" for the shared ADK callback mechanism, but a worker never gets a real `agents/{id}` document the way a registered department agent does. `before_agent_callback` fires this call on literally the first thing that happens in any agent turn — meaning every single `spawn_worker`/`spawn_worker_and_await` call had been failing in production, silently, since the feature shipped. Confirmed live against real Firestore both ways (the bug reproduced with the old code, the fix resolved it) before committing. The fix is a one-line `except NotFound: pass` in the one function every agent-status update already goes through — not a new agents-collection doc for every ephemeral worker, which would have polluted the persistent-agent roster the office floor renders.
- **Full observability build-out**: per-aspect verification votes (which checker passed/failed and why — previously computed by `vote_aspects()` and then thrown away by every caller) now persist onto `task.result`; ephemeral workers' execution trace turned out to already exist for free (the same NotFound-doc discovery above meant the trace subcollection write — a Firestore subcollection `.add()`, which doesn't require its parent document to exist — was reachable all along; it just needed a frontend panel); a live audit hash-chain integrity badge; a new Board tab for the CEO's shared blackboard collection, which had zero frontend surface before this; and previously-invisible fields (task model tier/attachment/timestamps, agent session turn count) surfaced across the existing views.
- **The live check the plan explicitly couldn't do from code alone**: after redeploying, reading the CEO self-check trigger's actual production behavior (it fires correctly every 30 minutes, confirmed via its Firestore history) found a real, if lower-severity, problem — `list_tasks_tool()` genuinely and correctly returns an empty list (the demo org has zero tasks right now, nobody's dispatched real work through the live UI yet), but the CEO was misreading that healthy empty result as a broken tool, and re-posting an increasingly dramatically worded "crisis"/"catastrophic failure" note to the company's own shared board on every single firing for hours, rather than recognizing an unchanged, already-reported, non-issue. Exactly the kind of thing a judge opening the new Board tab would have seen. Fixed in the trigger's own prompt — an empty list is stated as healthy, not a failure, and a stable unresolved finding doesn't need re-alarming every 30 minutes — and the stale alarmist board note was cleared.
- **A public landing page**, service-health indicators (a connection-lost banner when any Firestore listener drops, a polling status dot against the now-real `/api/healthz`), and a backend-wide error-handling audit (a global exception handler, timeouts and clean failure modes added to every external call this project makes) — the frontend/production-readiness asks that kicked off this whole push, addressed alongside the eligibility and bug fixes above once those took priority.

## What we chose to let go — the full list in one place

Everything below was seriously considered at some point and deliberately
not built, with the reason on record (mostly in the ADR named):

- A local desktop app with a bolted-on cloud-sync layer (ADR-0001).
- A polyglot backend, one language per department (ADR-0002).
- Firestore-only messaging via inbox polling, instead of Pub/Sub push
  (ADR-0003).
- A2A for internal CEO↔department messaging (ADR-0004).
- Ad hoc per-department Firestore/Pub-Sub wiring instead of one shared
  contract (ADR-0005).
- A second, non-Gemini LLM provider dedicated to fraud detection
  (ADR-0006).
- Trusting an LLM's self-reported confidence score, or a second LLM call
  as the *sole* check, for grounded claims (ADR-0007).
- Ponytail at `full`/`ultra` during initial core-department buildout, or
  at `lite` throughout the wider-roster buildout (ADR-0008).
- Learning and adopting ADK's new `Workflow` graph API under deadline
  pressure, or avoiding a real ADK agent for Sales entirely (ADR-0009) —
  the latter still an open item, not yet revisited.
- Firestore-rules-only or backend-check-only auth, and per-endpoint (versus
  router-level) auth wiring (ADR-0010).
- A Pub/Sub dead-letter policy instead of catching failures ourselves, and
  retry-with-backoff for transient Gemini errors (deferred, ADR-0011).
- A Firestore-transaction-exact Gemini budget counter, and per-department
  (versus per-org) budgets (ADR-0012).
- Base64-in-Firestore for vision attachments, a deterministic
  priority→model-tier rule, `include_attachment` defaulting to opt-in, and
  mutating a shared agent singleton's `.model` per-turn (ADR-0013).
- Google Antigravity, SDK or CLI, in any form — including a DIY
  private-attribute persistence hack and a single-always-on-machine CLI
  deployment (ADR-0014).
- opencode's in-process sub-agent/child-session delegation pattern, worker
  permission-narrowing with no concrete problem behind it, and forcing
  `vote_aspects` onto departments with no external claim to verify
  (ADR-0015).
- Anthropic's Programmatic Tool Calling and "speculative PTC" outright (not
  usable on this stack, not a design choice); routing integration-access
  denial through the task-blocking path instead of a standing queue;
  embedding/searching the knowledge base instead of inlining it; and a
  counted (versus structural) sub-agent depth cap (ADR-0016, this session).

## Current state

All 9 originally planned departments are implemented: Finance & Audit,
Engineering & SRE, Legal & Risk, Office of the CEO, Sales & CRM (also
A2A-exposed), HR & People Ops, Customer Support, Marketing & Comms, and
Product & Data Analytics. The full Command Center tab set is implemented
(Monitor, Tasks, Ask-me, Activity, Triggers, Workers, Memory, Knowledge,
Board, Graph, Settings, Commands), plus a real 3×3 office floor with
personas, per-department integration access control, an org-uploadable
knowledge base, sub-agent spawning, a sandboxed multi-tool orchestration
path, realtime voice, OAuth "Connect apps," Veo/Lyria generation, and a
public landing page. **Live**, deployed against a real GCP project — see
`README.md`'s Status section for the current URLs. 228+ backend tests and
a clean frontend build/lint pass as of this writing.

Known open items, not hidden: the `SequentialAgent`→`Workflow` migration
(ADR-0009), retry-with-backoff for transient Gemini errors (ADR-0011),
self-service org invites (still manual via `scripts/seed.py
--owner-uid`), real Cloud Run Job execution for ephemeral workers (they
currently run as in-process `asyncio` tasks — a documented, deliberate MVP
shape, not an oversight), and extending the sandbox's tool allowlist to
writes once a real sandboxed-write audit design exists.
