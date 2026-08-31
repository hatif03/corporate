# Testing & running locally

Prerequisites: Python 3.11+, Node 20+, a GCP project with Firestore (native mode) and the `agent-bus` Pub/Sub topic created (see `/infra/deploy/setup.sh`), and `gcloud auth application-default login` run once so the backend's Firestore/Pub-Sub clients can authenticate.

## Run it locally

**Backend:**
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # fill in your GCP project id
python scripts/seed.py --owner-uid <your-firebase-uid>   # seeds agents + grants you org access
uvicorn app.main:app --reload --env-file .env
```
Set `LOCAL_DEV=1` in `.env` to run the Pub/Sub pull-loop instead of expecting real push delivery — useful before you've deployed a public backend URL for push subscriptions to target.

Every `/api/org/{org_id}/*` endpoint requires a Firebase ID token from a user who's a member of that org (see `docs/system_prompt.md`'s Auth section) — sign in once via the frontend to create your Firebase user, grab your uid from the Firebase Console (or `firebase auth:export`), then re-run `seed.py --owner-uid` with it. Without this step every API call returns 401/403 by design.

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env           # fill in your Firebase web app config
npm run dev
```

**A2A server (Sales & CRM, optional):** a second, standalone entrypoint exposing the Sales & CRM pipeline over the A2A protocol for external callers — see `docs/adr/0004-a2a-scoped-to-external-boundary-only.md`.
```bash
cd backend
uvicorn app.a2a_server:app --port 8001 --reload
curl http://localhost:8001/.well-known/agent-card.json
```
Deployed separately from the main backend (its own Cloud Run service) so `/.well-known/agent-card.json` sits at that service's own root, as the A2A spec expects.

## Backend tests

```bash
cd backend
pytest -q          # 228+ tests, no live GCP credentials needed
```

Every test mocks Firestore, Pub/Sub, Gemini, and Secret Manager — the suite runs offline, with no `.env` or `gcloud` login required. A few conventions worth knowing before adding to it:

- **Every department ships a smoke test** at `backend/departments/<dept_id>/tests/test_<dept_id>_smoke.py` — at minimum, one real call through `on_task_received` with a representative task and an assertion on the writeback. This is the fastest way to check a new or changed department actually completes the dispatch contract end to end.
- **Shared utilities have their own unit tests**, independent of any department: `backend/tests/test_audit_chain.py` (`verify_chain()`, including a deliberate-tamper test that flips one byte in a logged entry and asserts the chain now reports broken) and the `shared/verification.py` tests (`ground_quote`/`vote_aspects`, including a deliberate-ungroundable-claim test proving the drop-not-fabricate path actually fires). If you're adding a new department that produces a claim-with-evidence, route it through `ground_quote`/`vote_aspects` rather than writing a new ad hoc check — see `docs/system_prompt.md`.
- **Dispatch-path tests** (`test_dispatch.py` and similar) cover the idempotency and failure-containment behavior every department gets for free via `@audited_task` — redelivered Pub/Sub messages are a no-op, and any exception a department raises gets caught, marked `BLOCKED`, and replied to rather than left stuck. If you touch `backend/departments/base.py` or `app/services/dispatch.py`, re-run this file specifically.
- Run a single file or department's tests directly rather than the whole suite while iterating: `pytest departments/finance_audit/tests/ -q` or `pytest tests/test_dispatch.py -q`.

## Frontend checks

There's no frontend test framework in this project — checks are type-checking and linting:
```bash
cd frontend
npm run build   # tsc -b && vite build — fails on any type error
npm run lint    # oxlint
```
Run both before committing a frontend change; `npm run build` in particular catches the kind of Firestore-`Timestamp`-typed-as-`string` mismatch that's bitten this project in production before (see part 4 of the [blog series](blog/04-the-final-72-hours.md)).

## Testing against the live deployment

Fastest way to see real behavior end to end, without running anything locally: open the live app, sign in with Google, and:
1. Watch the office floor — agents idle, then animate (thinking/working/blocked dots) as they get work.
2. Go to **Tasks**, or dispatch a goal through the CEO (via the Terminal in the CEO's Agent Detail view, or a Trigger).
3. Watch **Activity** for the live audit-chain integrity badge, **Ask-me** for any human-in-the-loop questions a department raises, **Graph** for the live agent-to-agent message graph, **Workers** to spawn an ephemeral one-off worker and watch its real execution trace, and **Board** for the CEO's shared company blackboard.
4. Open a department's Agent Detail view for its persona, voice, current goal, model tier, and skills.
5. Try the mic icon for a realtime voice conversation with the CEO.

Live URLs are in [`README.md`](../README.md)'s Status section.

## Deploying changes

See [`README.md`](../README.md#deployment) and [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) for the deploy scripts and full system diagram.
