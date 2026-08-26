# Corporate

A virtual company: a 2D pixel-art office-floor web app where autonomous AI employees work across real departments (Finance, Engineering, Legal, and more), coordinated by a CEO agent, all visible and controllable through a "Command Center" dashboard.

Built for the **All Things Agentic** hackathon. Track: The Fortified Enterprise Fleet.

## Status

**Live**: backend at [corporate-backend-2wv6ilt7fa-uc.a.run.app](https://corporate-backend-2wv6ilt7fa-uc.a.run.app/api/healthz), frontend at [project-f0b6b4ce-541f-43ff-9f7.web.app](https://project-f0b6b4ce-541f-43ff-9f7.web.app), Sales & CRM's A2A agent card at [corporate-a2a-sales-2wv6ilt7fa-uc.a.run.app/.well-known/agent-card.json](https://corporate-a2a-sales-2wv6ilt7fa-uc.a.run.app/.well-known/agent-card.json).

All 9 planned departments implemented (Finance & Audit, Engineering & SRE, Legal & Risk, Office of the CEO, Sales & CRM, HR & People Ops, Customer Support, Marketing & Comms, Product & Data Analytics — Sales & CRM is also exposed externally over A2A), the CEO orchestrator, Pub/Sub messaging with loop-cap protection, Firestore-backed ADK sessions, schedule/webhook triggers, ephemeral workers, real semantic memory (Vertex AI text-embedding-004 + naive-cosine search), an agent-to-agent message graph, a secrets-isolated integration broker (Slack/Jira/GitHub/Stripe/Notion/HubSpot templates) with per-department access control and an owner-resolved access-request queue, an org-uploadable per-department knowledge base, agent-callable sub-agent spawning (structurally depth-capped at one level), a sandboxed `execute_python` tool for combining several tool calls into one round trip (real OS subprocess + RestrictedPython, not just an in-process mock), and Firebase Auth + org-membership checks enforced in both Firestore Security Rules and the backend independently. Every agent has a real persona (name, bio, sprite) and lives in a responsive 3×3 room-and-corridor office floor. The full Command Center tab set is implemented: Monitor, Tasks, Ask-me, Activity, Triggers, Workers, Memory, Knowledge, Graph, Settings, Commands. The dispatch path is idempotent (Pub/Sub redelivery is a no-op, not a re-run) and fails closed — a department failure is always caught, surfaced through the Ask-me flow, and replied to, never left as a silently stuck task (ADR-0011). See `/docs/adr/` for architectural decisions, `/docs/PROJECT_HISTORY.md` for the full narrative of how the project got here (including what was explored and deliberately not built), and `/docs/system_prompt.md` for the canonical engineering rules this project follows.

## Stack

- **Frontend:** React + Vite + TypeScript, Pixi.js (office floor), xterm.js (agent thought-stream)
- **Backend:** Python 3.12, FastAPI, [Google ADK](https://google.github.io/adk-docs) `2.7.1`
- **LLM:** Gemini, via Vertex AI
- **Cloud infra:** Cloud Run, Firestore, Pub/Sub, Cloud Scheduler, Secret Manager
- **Hosting:** Firebase Hosting (frontend) + Cloud Run (backend)

## Repository layout

```
/frontend    React/Vite app — office floor, Command Center tabs
/backend     FastAPI + ADK service — agents, tools, Pub/Sub, Firestore access
/departments Declarative per-department config (YAML)
/shared      Cross-language schema definitions
/infra       Deployment scripts (gcloud, Firestore indexes, Pub/Sub setup)
/docs        Architecture Decision Records, architecture rules, diagrams
```

## Local development

Prerequisites: Python 3.11+, Node 20+, a GCP project with Firestore (native mode) and the `agent-bus` Pub/Sub topic created (see Deployment below), and `gcloud auth application-default login` run once so the backend's Firestore/Pub-Sub clients can authenticate.

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

Run the test suite with `pytest` from `backend/` (all current tests mock Firestore/Pub-Sub/Gemini, so they run without any live GCP credentials).

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

## Deployment

See `/docs/ARCHITECTURE.md` for the full system diagram and component list. `/infra/deploy/setup.sh` (one-time: enable APIs, create Firestore + the `agent-bus` topic, create the backend service account) and `/infra/deploy/deploy.sh` (build + deploy both Cloud Run services, wire Pub/Sub push IAM, seed Firestore, deploy the frontend) are both live and idempotent — `setup.sh` has already been run once against `project-f0b6b4ce-541f-43ff-9f7`, and `deploy.sh` is safe to re-run any time to ship new changes (redeploys both Cloud Run services, reseeds Firestore, and redeploys Firestore rules + the frontend):
```bash
PROJECT_ID=project-f0b6b4ce-541f-43ff-9f7 REGION=us-central1 ./infra/deploy/setup.sh   # one-time, already done
PROJECT_ID=project-f0b6b4ce-541f-43ff-9f7 REGION=us-central1 ./infra/deploy/deploy.sh  # every deploy
```

Firestore Security Rules (`firestore.rules`) and Hosting config (`firebase.json`) deploy via the Firebase CLI (also run automatically by `deploy.sh`):
```bash
npm install -g firebase-tools   # once
firebase deploy --only firestore:rules
firebase deploy --only hosting
```

## Contributing

Read `/docs/system_prompt.md` before writing code — it's the canonical source of the architectural conventions this project follows (department contract, ADK/Gemini conventions, Firestore/Pub-Sub access rules, secrets policy). `CLAUDE.md` and `.cursor/rules/` both derive from it.

Every non-obvious architectural decision gets an ADR in `/docs/adr/` — see that folder for the template and the existing record. `/docs/PROJECT_HISTORY.md` ties every ADR together into one chronological story, including the alternatives that were seriously considered and deliberately not built.
