# Corporate

A virtual company: a 2D pixel-art office-floor web app where autonomous AI employees work across real departments (Finance, Engineering, Legal, and more), coordinated by a CEO agent, all visible and controllable through a "Command Center" dashboard.

Built for the **All Things Agentic** hackathon. Track: The Fortified Enterprise Fleet.

## Status

Early build. See `/docs/adr/` for architectural decisions and `/docs/system_prompt.md` for the canonical engineering rules this project follows.

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

_Setup instructions land here as Phase 0/1 infrastructure is stood up — this section is a living document, kept in sync with `/infra/deploy/`._

## Deployment

See `/infra/deploy/` and `/docs/ARCHITECTURE.md` for the full GCP setup and `gcloud`/`firebase` deploy sequence.

## Contributing

Read `/docs/system_prompt.md` before writing code — it's the canonical source of the architectural conventions this project follows (department contract, ADK/Gemini conventions, Firestore/Pub-Sub access rules, secrets policy). `CLAUDE.md` and `.cursor/rules/` both derive from it.

Every non-obvious architectural decision gets an ADR in `/docs/adr/` — see that folder for the template and the existing record.
