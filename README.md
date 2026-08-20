# Corporate

A virtual company: a 2D pixel-art office-floor web app where autonomous AI employees work across real departments (Finance, Engineering, Legal, and more), coordinated by a CEO agent, all visible and controllable through a "Command Center" dashboard.

Built for the **All Things Agentic** hackathon. Track: The Fortified Enterprise Fleet.

## Status

All 9 planned departments implemented (Finance & Audit, Engineering & SRE, Legal & Risk, Office of the CEO, Sales & CRM, HR & People Ops, Customer Support, Marketing & Comms, Product & Data Analytics — Sales & CRM is also exposed externally over A2A), the CEO orchestrator, Pub/Sub messaging with loop-cap protection, Firestore-backed ADK sessions, schedule/webhook triggers, ephemeral workers, and a frontend covering Monitor, Tasks, Ask-me, Activity, Triggers, and Workers. Also has real semantic memory (Vertex AI text-embedding-004 + naive-cosine search across every agent's memory, exposed via a Memory tab). Not yet deployed to Cloud Run — see Local development below. See `/docs/adr/` for architectural decisions and `/docs/system_prompt.md` for the canonical engineering rules this project follows.

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
python scripts/seed.py        # creates the CEO + Finance agents in Firestore
uvicorn app.main:app --reload --env-file .env
```
Set `LOCAL_DEV=1` in `.env` to run the Pub/Sub pull-loop instead of expecting real push delivery — useful before you've deployed a public backend URL for push subscriptions to target.

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

See `/infra/deploy/` and `/docs/ARCHITECTURE.md` for the full GCP setup and `gcloud`/`firebase` deploy sequence. Not yet run against a live project as of this commit.

## Contributing

Read `/docs/system_prompt.md` before writing code — it's the canonical source of the architectural conventions this project follows (department contract, ADK/Gemini conventions, Firestore/Pub-Sub access rules, secrets policy). `CLAUDE.md` and `.cursor/rules/` both derive from it.

Every non-obvious architectural decision gets an ADR in `/docs/adr/` — see that folder for the template and the existing record.
