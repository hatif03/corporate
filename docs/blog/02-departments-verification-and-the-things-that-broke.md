# Building Corporate, part 2: departments, verification, and the things that broke

*Part 2 of a four-part series on building Corporate. [Part 1](01-why-a-company-of-agents.md) covered why we shaped this as a company of agents in the first place. This part covers the department pipelines themselves, how we keep an LLM's claims honest, and a hardening pass that fixed real, live bugs — not hypothetical ones.*

## Building order, and why it wasn't arbitrary

Departments went in roughly this order: Finance & Audit first (alongside a minimal frontend — the whole point was to prove the CEO-to-department loop over *real* Pub/Sub, not a stub), then Engineering & SRE and Legal & Risk, then Office of the CEO (a digest agent that reads real Firestore counts) and Sales & CRM (the one department later exposed over live A2A), then Triggers & Workers, then HR & People Ops and Customer Support, then Marketing & Comms and Product & Data Analytics — all nine of the originally planned departments.

That order matters because the first three taught us two structural lessons that shaped every department after them.

## Lesson one: independence comes from structure, not a second vendor

[ADR-0006](../adr/0006-gemini-only-fraud-agent-structural-independence.md): Finance & Audit's fraud-detection stage needed some notion of an independent check — you don't want the same model call that classified an invoice also being the one that decides whether it's fraudulent, using its own prior reasoning as evidence. The obvious move is a second LLM *provider* for that one stage. We evaluated it and rejected it: this project's hard Gemini-only-via-Vertex-AI constraint isn't a style preference, it's a hackathon eligibility requirement, and the added integration surface, cost, and latency of a second provider for one narrow pipeline stage wasn't worth it even if it were allowed.

What shipped instead: Stage 2 (the fraud-risk judgment) is a genuinely *fresh* Gemini call that only ever sees Stage 1's deterministic signal JSON — never the classification agent's own free-text reasoning. It structurally can't rationalize a framing it never saw. Self-consistency sampling (running the same judgment multiple times and checking agreement) was noted as a future enhancement, not something we needed for this to be a real, defensible independence story.

## Lesson two: an LLM may judge or propose; only deterministic code verifies

This is the one architectural principle ([ADR-0007](../adr/0007-grounded-claim-verification-pattern.md)) that shows up in more departments than any other, so it's worth explaining properly. Say a department produces a claim with evidence attached — "this invoice cites vendor terms saying X," "this support answer quotes the knowledge base saying Y." How do you know the quote is real and not a plausible-sounding fabrication?

Two tempting shortcuts, both rejected:

- **Trust the LLM's own confidence score.** Rejected — confidence scores from an LLM aren't reliably calibrated to actual groundedness. A model can be extremely confident and simply wrong.
- **Have a second LLM call double-check the first.** Rejected as the *sole* mechanism — it's still LLM-mediated, and can share the exact same failure mode as the first call (both models trained on similar data, both susceptible to the same kind of plausible fabrication).

What actually shipped is [`shared/verification.py`](../../backend/shared/verification.py), and it has two genuinely different tools for two genuinely different jobs:

- **`ground_quote()`** — deterministic string matching (with a fuzzy fallback for near-verbatim quotes), no LLM involved at all. If a cited quote can't be located in the source text, the claim is *dropped*, never "corrected" by asking a model to fix it up. This is used by Legal & Risk (five parallel judge lenses, then deterministic quote-grounding drops anything that doesn't check out) and Customer Support (classify → knowledge-base-grounded reply → the same grounding check, third reuse of the pattern).
- **`vote_aspects()`** — for claims that aren't a single quotable string but a broader judgment (is this marketing copy on-brand? does this fraud signal actually look internally consistent?), N independent pluggable checkers vote, two-thirds agreement required, with one retry allowed before the claim is treated as unverified. Finance & Audit, Engineering & SRE, and Marketing & Comms all use this. Critically, the *checkers* can be LLM-backed — an LLM may propose a judgment — but the harness code, not any model, decides the final verdict from the vote tally. That line never moves.

## The one place we knowingly took on debt: `SequentialAgent`

Sales & CRM needed one genuine, directly-invokable ADK agent object, because `to_a2a()` (the mechanism that exposes an agent externally over the [A2A protocol](https://github.com/a2aproject/A2A)) needs a real agent, not the plain-Python orchestration every other department uses internally. The tool for that job in [ADK](https://github.com/google/adk-python) 2.7.1 is `SequentialAgent` — except it's already deprecated in that same version, in favor of a new [graph-based `Workflow` API](https://adk.dev/graphs/).

We used `SequentialAgent` anyway, and wrote down exactly why: learning and correctly implementing an unfamiliar graph API under real deadline pressure, for the one department that structurally needs a composed agent object, was a worse trade than shipping working code with known, tracked debt. This is in [ADR-0009](../adr/0009-sequentialagent-deprecation-known-debt.md) as exactly that — a deliberate choice, revisitable later if `Workflow` becomes the standard across the whole department layer, not something we're pretending isn't there.

## Hardening pass: the bugs we found by actually reading the dispatch path

Once the department roster was real, we did something that sounds obvious but is easy to skip under time pressure: we read the actual dispatch path end to end, instead of assuming it worked because the happy-path demo worked. That read turned up three real gaps, not hypothetical ones ([ADR-0011](../adr/0011-dispatch-idempotency-and-failure-handling.md)):

**No dedup on Pub/Sub redelivery.** Pub/Sub is at-least-once delivery by design — a redelivered message is a normal, expected event, not an edge case. Nothing in the dispatch path checked for it, meaning a redelivered message would re-run a department's `on_task_received` from scratch. Fixed with an atomic check-and-set using Firestore's native `create()` call, which raises a `Conflict` if the (agent, message) pair was already processed — the redelivery becomes a logged no-op.

**No error handling anywhere in the path.** An exception inside a department's task processing left the task stuck at `DOING` forever, and — because nothing acked or nacked the Pub/Sub message — told Pub/Sub to keep retrying indefinitely. We considered a Pub/Sub dead-letter policy as the fix and rejected it: once every failure mode we could actually anticipate is caught and acknowledged, there's no failure left for a DLQ to catch that we'd want silently parked instead of surfaced. What shipped is [`@audited_task`](../../backend/departments/base.py)'s shared failure-containment path — any exception a department raises gets caught, the task is marked `BLOCKED` with a real human-question entry, and the requester gets a proper `refuse` reply. A department can no longer leave a task stuck or crash the whole dispatch handler.

**The Ask-me flow was broken end to end.** `has_pending_human_qa` was being set correctly on a task, but the actual `HumanQA` entry the answer endpoint needed to index into was never being appended anywhere. The flag said "a human needs to look at this" and there was nothing to look at. Fixed alongside the failure-containment path above, since both a genuine exception and a deliberate `needs_human=True` now route through the identical mechanism.

We found a very similar bug again in the final 72 hours before the deadline — a different feature, a different root cause, the same lesson (read the actual code path, don't assume the demo working means the whole path works). That story is in [part 4](04-the-final-72-hours.md).

## Two auth layers, because one alone has a hole

[ADR-0010](../adr/0010-defense-in-depth-auth.md): [Firestore Security Rules](https://firebase.google.com/docs/firestore/security/get-started) alone was rejected as insufficient: the backend writes to Firestore using its own elevated service account, not a per-user token, so a rule gating client reads/writes does nothing to protect the backend's own write path from a compromised or over-permissioned backend bug. A backend-only check with permissive Firestore rules was rejected too, for the mirror-image reason: the frontend reads most state directly via `onSnapshot`, so a leaked client reference (or a misconfigured rule) would expose any org's data with nothing stopping it. Both layers ship. `require_org_member` is wired at the router level, not per-endpoint, specifically so a newly added endpoint can't accidentally ship without it — a mistake that's easy to make once and easy to never notice, if the check lived at the leaf instead of the root.

## A Gemini budget, because "it's all mocked" stops being an excuse once it isn't

[ADR-0012](../adr/0012-gemini-cost-guard.md): the daily Gemini call budget was genuinely deferred early on — while everything ran against mocks, a runaway-cost circuit breaker wasn't defensible engineering time. It became necessary the moment real billing went live. We considered making the counter Firestore-transaction-exact and rejected it: an atomic `Increment` plus a non-transactional follow-up read is close enough for a circuit breaker meant to catch *gross* runaway behavior, not to serve as precise billing enforcement — and we said so directly in the code rather than let it look like an oversight. Per-department budgets were considered and rejected too: the real risk this guards against is total account spend, not any one department spending more than its neighbors.

## Real testing found a real gap, twice

[ADR-0013](../adr/0013-search-model-tiering-vision-per-org-budget.md): two capability gaps got found by actually using the live system, not by static review: an open-ended research goal got correctly declined by Product & Analytics (rightly scoped to internal task/SLA metrics only) — but the decline reason was invisible until we fixed that separately by giving every agent Google Search as a tool with real guidance on when to reach for it. And a fixed 500-call/day Gemini budget was found to risk blocking a live demo outright with no way to raise it short of a redeploy — fixed with a per-org configurable budget in the Settings tab, raised to a much higher fallback default.

Alongside those: per-task model tiering (the CEO picks "flash" or "pro" per task, not a static per-department setting), where we specifically rejected mutating a shared agent singleton's `.model` field per-turn — department `LlmAgent`s are built once at import time and shared across every org's turns, so a per-turn mutation is a real race condition the moment two orgs' work overlaps on the same Cloud Run instance. Two full singleton agents per pipeline stage, one per tier, sidesteps that entirely. And vision attachments moved from base64-in-Firestore (rejected once we hit its ~700KB effective ceiling under Firestore's 1MiB document limit) to a real Cloud Storage upload with `Part.from_uri()` reading it directly — which turned out to be the more natural Vertex AI integration anyway, not just a workaround for a size limit.

[Part 3](03-capability-expansion-and-the-roads-not-taken.md) covers the capability expansion that came after all of this held for a while: sub-agent spawning, a real sandboxed code-execution tool, and the research trail (accepted and rejected both) into realtime voice, OAuth connect flows, and Gemma/Veo/Lyria.
