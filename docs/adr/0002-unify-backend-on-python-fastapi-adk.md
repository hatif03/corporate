# ADR-0002: Unify the backend on Python/FastAPI/ADK, no polyglot departments

Status: Accepted

## Context

Corporate is organized as multiple departments (Finance, Engineering, Legal, and more), each with its own agent pipeline. Each department could in principle be built in whatever language best suits its individual workload.

## Decision

Every department, and the platform core (routing, session management, Firestore/Pub-Sub access), is Python, built on FastAPI and Google ADK. No department introduces a second backend language or a second agent framework.

## Alternatives considered

- **Polyglot per department** (e.g. a Node/TypeScript service for one department, Python for others). Rejected: Google ADK's most mature, actively developed SDK is Python (see `/docs/system_prompt.md` for the pinned version); a second language would mean a second agent-framework integration to maintain, duplicated Firestore/Pub-Sub client code, and a harder story for the "Architectural Discipline" judging criterion, which rewards a coherent, single stack over a patchwork of "whatever the original prototype happened to use."

## Consequences

Every department shares one `DepartmentSpec` contract (see ADR-0005), one Firestore access pattern, one Pub/Sub client, and one set of ADK conventions. Onboarding a new department is "write Python against an established contract," not "integrate a new language's tooling into the platform."
