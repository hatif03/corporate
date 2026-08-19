# ADR-0001: Cloud-native hosted architecture, not a desktop app

Status: Accepted

## Context

The hackathon this project targets requires a hosted project URL, and every submission must demonstrably use Gemini, a Google Agent Framework, and a Google Cloud infrastructure service running server-side, with the demo video proving live Google Cloud usage. An early design direction modeled this as a local desktop application that would spawn agent processes on the user's own machine — that model has no "hosted URL" to submit and no server-side Google Cloud footprint to demonstrate.

## Decision

Build Corporate as a hosted web application from the start: a React/Vite single-page frontend and a Python/FastAPI + Google ADK backend, deployed to Cloud Run, with Firestore for state and Pub/Sub for inter-agent messaging. No desktop shell, no locally-spawned agent processes.

## Alternatives considered

- **Local desktop app spawning agent CLI processes**, with a thin cloud sync layer bolted on to technically touch Google Cloud. Rejected — Google Cloud usage would be peripheral rather than load-bearing, which scores poorly against the "Architectural Discipline & Tech Stack" judging criterion, and there is no real "hosted URL" to submit.
- **Hybrid**: desktop app for local development/demo, separate cloud deployment for submission. Rejected for now as unnecessary duplicated effort — revisit only if a genuinely compelling desktop-specific feature emerges.

## Consequences

Every agent's execution, state, and messaging must be designed for an ephemeral, horizontally-scaled, stateless-compute environment (Cloud Run instances) from day one — this drives the Firestore-backed ADK session service (see ADR-0003) rather than any in-memory or local-filesystem state. It also means the UI must be built as a normal multi-tenant web app with real auth (see the platform architecture notes in `/docs/system_prompt.md`), not a single-user local tool.
