# ADR-0010: Firebase Auth + org membership, enforced independently in two layers

Status: Accepted

## Context

Corporate is multi-tenant from day one (every collection namespaced `orgs/{orgId}/...`, per ADR-0003), even though only `orgs/demo` is seeded for the hackathon. The frontend reads most state directly from Firestore via `onSnapshot` rather than through the backend, so Firestore Security Rules are a real access-control surface, not just a formality. At the same time, the backend itself writes to Firestore using its own elevated service-account credentials (not a per-user token), so a Firestore rule that only checks "is this org member" would not by itself stop a non-member from reaching a backend endpoint that then writes on their behalf with that elevated identity — the backend has to independently check membership too.

## Decision

Two independent layers, neither sufficient alone:
1. **Firestore Security Rules** (`firestore.rules`) — a client can only read an org's documents if `orgs/{orgId}/members/{uid}` exists for their authenticated uid. All client-side writes are rejected outright; every write path in this project goes through the backend.
2. **Backend membership check** (`app/services/auth.py`'s `require_org_member`) — verifies the caller's Firebase ID token and their org membership, wired once as a router-level FastAPI dependency on every `/api/org/{org_id}/*` router (`app/main.py`), not per-endpoint.

`/internal/*` routes (Pub/Sub push, Cloud Scheduler fire) are deliberately excluded from `require_org_member` — those callers authenticate via IAM/OIDC, not an end-user Firebase token, and wiring end-user auth onto them would be a category error, not extra security.

## Alternatives considered

- **Firestore rules only.** Rejected — doesn't protect the backend's own write path, since the backend's service-account credentials aren't subject to per-user Firestore rules at all.
- **Backend check only, permissive Firestore rules.** Rejected — the frontend's direct `onSnapshot` reads would then have no access control of their own; a leaked or forged client-side reference could read any org's data.
- **Per-endpoint `Depends(require_org_member)` instead of router-level wiring.** Rejected — router-level wiring means a new endpoint added to an existing router inherits the check automatically; a per-endpoint pattern relies on every future author remembering to add it, which is exactly the kind of thing that gets missed under deadline pressure.

## Consequences

Every `/api/org/{org_id}/*` test needed a way to bypass or supply auth — handled via FastAPI's `app.dependency_overrides` mechanism in `conftest.py`'s `_bypass_org_auth` autouse fixture, with a dedicated test (`test_org_scoped_endpoint_actually_rejects_unauthenticated_requests`) proving the override doesn't mask the real behavior. Org membership is currently granted manually via `scripts/seed.py --owner-uid` — there is no self-service invite/onboarding flow yet, which is fine for a single-org hackathon demo but would need building for real multi-tenant use.
