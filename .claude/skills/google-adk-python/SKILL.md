---
name: google-adk-python
description: Google Agent Development Kit (ADK) Python conventions for this project — pinned to 2.7.1, async Runner/session patterns, Firestore-backed sessions, and this project's specific rule that CEO-to-department delegation goes over Pub/Sub, not sub_agents. Use whenever writing or reviewing code in backend/adk_agents/, backend/departments/*/agents.py, or anything importing google.adk.
metadata:
  source: adapted from mrgoonie/claudekit-skills' google-adk-python skill, corrected against ADK 2.7.1 (2026-08-20) for this project's async/session/A2A conventions
---

# Google ADK Python — conventions for Corporate

ADK is Google's code-first, open-source toolkit for building, evaluating, and deploying LLM agents. This project pins **`google-adk==2.7.1`** (Python 3.11+ required since 2.0 — the session/storage schema changed at 2.0 and is not compatible with 1.x data, so never mix them). Every agent in this codebase runs on **Gemini via Vertex AI** — no other LLM provider, no raw Gemini API key path in product code.

## When to use this skill

Writing or reviewing anything under `backend/app/adk_agents/`, a department's `agents.py`/`tools.py`, or any code that imports `google.adk`.

## Core agent types

- **`LlmAgent`** — LLM-powered, dynamic routing based on instruction + tools. Every department's individual pipeline stages and the CEO agent are `LlmAgent`s.
- **Workflow agents** — `SequentialAgent`, `ParallelAgent`, `LoopAgent`: structured, deterministic composition. **Use these only within one department's own pipeline** (e.g. Finance's `doc_intel → accountant → fraud → verifier → explainer` chain). Never use `sub_agents=` for CEO-to-department delegation — that's a Pub/Sub message in this project (see `backend/app/services/pubsub_client.py` and `/docs/system_prompt.md`).
- **`BaseAgent`** — subclass only for genuinely custom control flow that the workflow agents can't express.

## Installation

```bash
pip install google-adk==2.7.1
```
Do not install `git+https://github.com/google/adk-python.git@main` in this project — pin the release version.

## Building an agent (this project's pattern)

Agents are built through `backend/app/adk_agents/factory.py`, not instantiated ad hoc:

```python
from google.adk.agents import LlmAgent

ceo_agent = LlmAgent(
    name="ceo",
    model="gemini-2.5-flash",  # or higher — must satisfy the project's Gemini 3.5+ constraint
    instruction=CEO_SYSTEM_PROMPT,
    tools=[create_task, update_task, write_board, send_message, list_agents, list_tasks],
)
```

A department's internal pipeline composes with a workflow agent:

```python
from google.adk.agents import SequentialAgent

finance_audit_pipeline = SequentialAgent(
    name="finance_audit_pipeline",
    sub_agents=[doc_intel, accountant, fraud, verifier, explainer],
)
```
(Note: workflow agents in current ADK take `sub_agents=`, not `agents=` — this differs from some older blog-post examples.)

## Tools

- Plain Python functions become tools automatically when passed in `tools=[...]` — no manual `Tool.from_function()` wrapping needed in current ADK.
- Tools can return **media** (e.g. images) in function responses as of ADK 2.7 — relevant for Finance's invoice-image handling.
- Every tool a department uses must go through the platform client for any Firestore/Pub-Sub/integration access — never reach for a raw client inside a tool function.

## Running an agent — async only

This project is async end-to-end on the backend. **Do not** write synchronous "call the agent and get a string back" code — that's not how the real API works, regardless of what simplified examples elsewhere show. The actual pattern:

```python
session = await session_service.get_or_create_session(
    app_name="corporate", user_id=org_id, session_id=agent_id
)
runner = Runner(agent=agent_for(agent_id), session_service=session_service, app_name="corporate")
async for event in runner.run_async(user_id=org_id, session_id=agent_id, new_message=to_adk_content(msg)):
    handle_event(event)
```

## Session persistence — Firestore-backed, always

Cloud Run instances are ephemeral and this project's architecture delivers one inbound Pub/Sub message per agent turn, potentially to a different instance each time. **`InMemorySessionService` will silently lose context** — never use it outside a local unit test. This project implements `FirestoreSessionService(BaseSessionService)`, persisting to `orgs/{orgId}/agent_sessions/{agentId}`. `VertexAiSessionService` is an acceptable fallback if ever needed, but not the default.

## Lifecycle callbacks → Firestore → UI

ADK's callback hooks (`before_agent_callback`, `before_tool_callback`, `after_tool_callback`, `after_agent_callback`) are how this project drives the office-floor UI's live agent status, replacing what would otherwise need a bespoke event bus:
- `before_agent_callback` → Firestore `agents/{id}.status = "thinking"`
- `before_tool_callback` → `status = "working"`, `carrying = <tool token>`
- `after_tool_callback` → append a `agents/{id}/trace` doc, clear `carrying`
- `after_agent_callback` → resolve `status` to `idle`/`waiting`/`blocked`
- unhandled exception → `status = "blocked"` + activity log entry + `hasPendingHumanQA = true`

## ADK 2.0+ things worth using

- **Jinja2-templated instructions** (`use_jinja2=True`) — use this for department prompt templates defined in `/departments/*.yaml` rather than hand-rolled string formatting.
- **Models self-declare capabilities** as of 2.7 — simplifies tool/schema pairing if this project ever needs multi-provider tool definitions (it currently doesn't; Gemini-only).
- **A2A support since 2.2.0** (`to_a2a()`, `RemoteA2aAgent`) — used in this project **only** at the external boundary (exposing Sales/Support as A2A servers). Never for internal CEO-to-department messaging. See ADR-0004 in `/docs/adr/` before touching anything A2A-related.

## What NOT to do (corrections to generic ADK examples you may see elsewhere)

- Don't use `sub_agents=` for cross-department delegation — that's Pub/Sub in this project.
- Don't use `InMemorySessionService` in any code path that runs on Cloud Run.
- Don't wire in a non-Gemini model, even for comparison/experimentation, in product code.
- Don't call Firestore/Pub-Sub clients directly from inside a tool function or agent — always through `app/services/`.
- Don't assume `Tool.from_function()` is required — recent ADK versions accept plain functions directly in `tools=[...]`.

## Resources

- GitHub: https://github.com/google/adk-python
- Docs: https://google.github.io/adk-docs/
- This project's architecture rules: `/docs/system_prompt.md`, `/docs/adr/`
