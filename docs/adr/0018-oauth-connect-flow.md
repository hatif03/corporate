# ADR-0018: OAuth "Connect with X" flow for Slack, GitHub, Notion

Status: Accepted

## Context

The integration setup flow (`POST /api/org/{org_id}/integrations`) requires pasting a raw API token/secret — fine for a technical user, a real barrier for the non-technical audience this product is now aimed at. The user asked for a real "Connect with X" button for at least Slack, GitHub, and Notion.

Real research into each provider's current OAuth documentation (not assumed) found: all three require a **manual, one-time app registration in that provider's own developer console** (api.slack.com/apps, github.com/settings/developers, notion.so/my-integrations) — this yields the `client_id`/`client_secret` and requires pre-registering an exact redirect URL; no API can create this registration on a developer's behalf. Notion additionally requires the resulting **public integration be submitted for Notion's own review** before its authorization URL activates at all — real lead time, not a code problem. Each provider's token-exchange transport genuinely differs: Slack and GitHub exchange the authorization code via a form POST with `client_secret` as a form field; Notion exchanges via a JSON body with `client_secret` sent as HTTP Basic Auth.

## Decision

Confirmed via AskUserQuestion: build the OAuth code path for all three now — Slack and GitHub work as soon as the app registrations exist and their client IDs/secrets are provided; Notion's button ships too but won't function until Notion approves the review.

- `app/services/oauth_providers.py`: a small per-provider adapter (`authorize_url()`, `exchange_code()`) for each of the three, rather than one generic OAuth helper — the transport differences above make a shared abstraction actively wrong for at least one provider.
- `Integration.auth_type` already had an unused `OAUTH2` enum value (`app/models/integration.py`) — this is what marks an OAuth-connected integration now. `call_integration()` (`integration_broker.py`) previously only attached an `Authorization: Bearer` header for `BEARER` auth type — `OAUTH2` fell through with no header at all, a real bug this ADR's work surfaced and fixed (OAuth tokens are sent the same way a pasted bearer token is; every provider we support OAuth for expects it).
- `app/api/oauth.py`: `GET /api/org/{org_id}/integrations/{kind}/oauth/start` (query-param Firebase token auth — a plain browser navigation can't carry an `Authorization` header, same reasoning as `voice.py`'s WebSocket auth, ADR-0017) redirects to the provider's real consent screen; `GET /api/oauth/{kind}/callback` (no org-scoped auth at all — the provider calls this directly, org identity travels in a signed `state` param instead) exchanges the code and writes the resulting token through the existing `store_secret()`, same as a manually-pasted one.
- `state` is HMAC-signed (`oauth_state_secret`, a new plain env var — not a third-party credential, just a locally-generated signing key) with a 10-minute TTL, verified before any org write happens — this is the only thing stopping a forged callback from writing an integration into an arbitrary org, since the callback route itself has no other auth.
- OAuth app client IDs are plain config (`app/config.py`); client **secrets** are resolved from Secret Manager at request time via the same `_resolve_secret()` every other credential in this app already goes through, at a fixed per-provider resource name (`oauth-{kind}-client-secret`) — a one-time `gcloud secrets create` alongside the app registration, not a new secrets-handling pattern.

## Alternatives considered

- **A single generic OAuth helper across all three providers.** Rejected — the real transport differences (form vs. JSON body, form-field vs. Basic-Auth client secret) mean a shared abstraction would need provider-specific branches inside it anyway; three small explicit adapters are more honest about what's actually different.
- **Storing the OAuth `state` server-side in a new Firestore collection.** Rejected — a signed, self-contained token (org_id + nonce + timestamp + HMAC) carries everything needed to verify itself, with no new collection, no cleanup job for expired entries, and no extra Firestore round trip on the hot callback path.
- **Skipping Notion given its review lead time.** Considered, rejected per the user's explicit choice — the code ships now regardless of when the review clears, so there's no reason to gate the engineering work on an external approval timeline that doesn't block anything else.

## Consequences

- Real one-time manual prerequisite before any of this works in production: register an app with each provider (redirect URL `{CORPORATE_BACKEND_URL}/api/oauth/{kind}/callback`), create the `oauth-{kind}-client-secret` secrets, and set `SLACK_OAUTH_CLIENT_ID`/`GITHUB_OAUTH_CLIENT_ID`/`NOTION_OAUTH_CLIENT_ID`/`OAUTH_STATE_SECRET` on the Cloud Run service. Until then, `/oauth/start` fails closed with a clear 500 ("OAuth isn't configured yet") rather than silently proceeding with an empty signing key.
- The existing paste-a-token flow is unchanged and still the only path for Jira, Stripe, and HubSpot — this ADR doesn't attempt OAuth for every integration kind, only the three where the user asked for it and a real provider OAuth flow exists to build against.
