# ADR-0020: Upgrade default Gemini tier to 3.5 for hackathon eligibility

Status: Accepted

## Context

Re-reading the hackathon's own rules page directly (allthingsagentichackathon.devpost.com, not assumed from memory) ahead of submission surfaced a hard eligibility requirement, not a scoring nuance: every track requires **"Gemini 3.5 or newer"**. This project's `app/config.py` defaulted to `gemini-2.5-flash` / `gemini-2.5-pro` / `gemini-2.5-flash-lite` (the last being the independent-review verifier tier from ADR-0019's Gemma post-mortem), and `app/api/voice.py` hardcoded `gemini-2.0-flash-live-preview-04-09` for the Live API voice relay — all below the 3.5 floor.

Same discipline as ADR-0019's Gemma post-mortem: model id strings and their region availability are not trustworthy from documentation alone (web search results during this research directly conflicted with each other on whether Gemini 3.5 Pro exists yet, and one fetched doc page rendered model ids with dashes instead of dots — a nav-menu-slug artifact, not the real API string). Everything below was confirmed by actually calling this project's live Vertex AI access, the same way the Gemma 404s were originally discovered.

## What was live-tested

- `client.models.list()` against this project's real Vertex AI access (not the Model Garden docs) enumerated the actual Gemini catalog available here. `gemini-3.5-flash`, `gemini-3.5-flash-lite`, and `gemini-3.1-pro-preview` are present and call successfully; `gemini-3.5-pro` and `gemini-3-pro`/`gemini-3-pro-preview` are **not** callable in this project — 3.5 Pro has no public model id yet anywhere (matches independent web research), only Pro's prior generation (`3.1-preview`) is actually reachable.
- **Region matters and differs by model generation.** `gemini-2.5-*` calls fine at `us-central1` (this project's existing default region for everything). The new `gemini-3.5-*`/`gemini-3.1-pro-preview` models **404 at `us-central1`** but work at Vertex's `global` location. This could have meant a real config change (a second `vertex_location`-style setting threaded through `app/adk_agents/factory.py`) — except:
- **ADK's `LlmAgent` never passes an explicit Vertex location.** Reading `google.adk.models.google_llm.Gemini.api_client` (the installed package source, not docs) shows it constructs `google.genai.Client(**kwargs)` with no `project`/`location` kwargs at all — those come from `google.genai`'s own env-var resolution (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`), and critically, `google.genai._api_client`'s own source shows that when neither an explicit `location` nor `GOOGLE_CLOUD_LOCATION` is set, it silently defaults to `location = 'global'`. This project has never set `GOOGLE_CLOUD_LOCATION` (only the unrelated custom `VERTEX_LOCATION` var, read solely by this project's own explicit `genai.Client(location=settings.vertex_location)` call sites — embeddings, Veo, Lyria, compaction, voice). So every ADK-driven `LlmAgent` call was already resolving to Vertex's `global` endpoint by default, with zero code change needed to make the 3.x models reachable. Confirmed with a real end-to-end ADK `Runner.run_async()` turn (not just a raw `generate_content` call) against all three new model ids before committing any of this.
- **`app/api/voice.py`'s Live API model had already quietly gone dead in production** — `gemini-2.0-flash-live-preview-04-09` 404s in this project today, independent of this eligibility push (preview-suffixed Live API ids churn, as the old code comment already warned). The replacement, `gemini-live-2.5-flash-native-audio`, was confirmed via a real `client.aio.live.connect()` round-trip — and needs `us-central1`, not `global` (the Live API tier hasn't moved off the region-pinned endpoint the way the main text-generation models have), so `voice.py` keeps using `settings.vertex_location` unchanged.

## Decision

- `corporate_gemini_model` → `gemini-3.5-flash` (default/flash tier, used by every department and the CEO).
- `corporate_gemini_model_pro` → `gemini-3.1-pro-preview` (the `model_tier="pro"` escalation path, ADR-0013).
- `corporate_verifier_model` → `gemini-3.5-flash-lite` (independent-review checker, ADR-0019).
- `app/api/voice.py`'s `VOICE_MODEL` → `gemini-live-2.5-flash-native-audio`.
- No change to `app/config.py`'s `vertex_location` (`us-central1`) or to any of the explicit `genai.Client(location=...)` call sites (Veo, Lyria, embeddings, compaction, voice) — only the ADK-driven models needed the (already-happening) `global` resolution, and that required no code change at all.

## Honest note on the Pro-tier version number

`gemini-3.1-pro-preview` is, read literally, a lower version number than "3.5" — Google does not version its Pro and Flash lines in lockstep (Flash reached 3.5 while Pro's newest reachable generation is 3.1-preview; 3.5 Pro doesn't have a model id yet in this or apparently any project). The eligibility requirement is satisfied unambiguously by the default/primary model every department actually runs on (`gemini-3.5-flash`) and the verifier tier (`gemini-3.5-flash-lite`); the pro-tier escalation path is a secondary, opt-in path (ADR-0013) upgraded to the current frontier Pro model as a genuine capability improvement over the previous `gemini-2.5-pro`, not claimed as itself satisfying the "3.5" requirement. Documented here rather than glossed over, matching this project's own established practice of surfacing exactly this kind of nuance instead of hiding it (see ADR-0019's Gemma correction).

## Consequences

- Any test asserting a literal model-id string needed updating alongside this (none did at time of writing — the suite reads `settings.corporate_gemini_model` etc. dynamically rather than hardcoding the string).
- `docs/ARCHITECTURE.md`, `README.md`, and `hackathon.md` all need their stated default model updated to match (tracked as part of this same submission push, not deferred).
- If Google ships a public `gemini-3.5-pro` id before the deadline, `corporate_gemini_model_pro` should move to it — same live-verification discipline as above, not a docs-only bump.
