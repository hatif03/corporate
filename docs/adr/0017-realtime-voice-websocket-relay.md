# ADR-0017: Realtime voice dispatch via a backend-held WebSocket relay to Vertex AI's Live API

Status: Accepted

## Context

Studying a reference app's UI for a pixel-exact clone (see ADR-0016, `docs/PROJECT_HISTORY.md`) surfaced a real feature worth evaluating on its own merits, not just its look: talking to the CEO agent by voice. This needed real, evidence-based research before committing to anything — installed-source inspection of `google-genai==2.18.1` (already pinned) confirmed a genuine Live API (`client.aio.live.connect()`, bidirectional audio) that works through **Vertex AI specifically** (not just the Gemini Developer API with a raw key), GA since 2025-12-13, authenticated via the same Application Default Credentials this backend already uses — no new provider, no new auth mechanism, consistent with the hard Gemini-via-Vertex-AI-only constraint (ADR-0002/0014).

One hard constraint the same research surfaced: Vertex's Live API has **no ephemeral-token path** — the installed SDK's `client.aio.auth_tokens.create()` raises `ValueError` outright when `vertexai=True`. A browser can never safely hold the credential a Live session needs.

## Decision

A real OS-process backend relay is the only legitimate architecture, not a corner cut: `backend/app/api/voice.py` exposes `@router.websocket("/ws/voice/{org_id}")` — the first WebSocket endpoint in this codebase. The backend opens `client.aio.live.connect()` (holding real ADC credentials, per the CEO's own system prompt so it answers in character) and relays raw PCM audio both directions over the browser WebSocket; the browser never touches a credential, only audio bytes.

**Auth**: browsers cannot set arbitrary headers on a WebSocket handshake, so the router is deliberately **not** wired with the `require_org_member` HTTP dependency (which reads an `Authorization` header) — instead `_authorized_uid()` verifies a Firebase ID token passed as a `?token=` query parameter and checks org membership the same way `require_org_member` does, just as a plain function suited to a WebSocket route instead of FastAPI's header-based `Depends()`.

**Scope, stated plainly**: v1 is a real-time voice *conversation* with the CEO's persona, not yet wired to the CEO's actual tools (`create_task`, etc.) — that needs routing through ADK's `Runner.run_live`/`LiveRequestQueue` (a real, verified-to-exist reference implementation lives in ADK's own installed `cli/api_server.py`) instead of the raw `genai` client. Not built now because that integration wasn't independently verified this session, and shipping an unverified control-flow change to how the CEO's tools are invoked is a worse trade than shipping a smaller, verified voice feature.

## Alternatives considered

- **Direct browser-to-Vertex connection via an ephemeral token** — ruled out by evidence, not preference: the installed SDK explicitly disallows it for Vertex.
- **OpenAI's Realtime API** (what the reference app itself uses, `@openai/agents-realtime`) — rejected outright; a second LLM provider is exactly what this project's Gemini-only constraint exists to prevent.
- **Routing through ADK's `Runner.run_live` now**, for real tool-calling from voice — considered, deferred. Genuinely more valuable, but the exact `LiveRequestQueue` API shape wasn't independently verified against installed source this session (only located as a reference, not read line-by-line); shipping it unverified risked a silently broken relay. Real follow-up, not abandoned.
- **`ScriptProcessorNode` vs `AudioWorklet`** for browser-side mic capture — `ScriptProcessorNode` (deprecated but universally supported, no separate worklet module to load/serve) chosen over `AudioWorklet` for this pass; noted inline as a `ponytail:`-style upgrade path, not a blind default.

## Consequences

- This is the first WebSocket endpoint in the backend — `main.py`'s comment on the router registration explains explicitly why it's excluded from the standard `_org_scoped_dependency` list, so a future contributor doesn't "fix" it into breaking.
- Real tests cover the auth gate (missing token, invalid token, non-member all rejected before a Live session ever opens) and the relay's own control flow (mocked session, real `asyncio.wait`/task-cancellation path exercised) — the full audio round trip against a live Vertex endpoint is a manual verification step, not automated in CI, same as any feature requiring real audio hardware.
- `VOICE_MODEL`'s exact id is a preview-suffixed Vertex model name, flagged inline as something to reconfirm against Google's docs if it ever 404s — the same discipline already applied to other externally-versioned identifiers in this codebase.
