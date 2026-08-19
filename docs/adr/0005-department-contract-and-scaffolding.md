# ADR-0005: A single DepartmentSpec contract for every department

Status: Accepted

## Context

Corporate is meant to grow to a full roster of departments (Finance, Engineering, Legal, Executive, HR, Sales, Support, Marketing, Product/Analytics, and likely more over time). Without a fixed contract, each new department risks reinventing its own way of touching Firestore, Pub/Sub, memory, and the audit/verification utilities — increasing both bug surface and onboarding cost.

## Decision

Every department is a Python package implementing one `DepartmentSpec` (department id, display name, an ADK root agent, accepted task types, a memory namespace, contributed verifier "aspect" checkers, and an optional human-review predicate) and one method, `on_task_received(task) -> TaskResult`, which is the *only* entrypoint the platform ever calls. The base class wraps every call with the shared audit-logging decorator and handles the task-status/reply writeback contract. Departments never touch Firestore, Pub/Sub, or the integration broker directly — only through the platform client.

A Claude Code skill (`new-department`) scaffolds this package structure from a short description, so adding a department is a matter of filling in a template, not designing a new integration surface each time.

## Alternatives considered

- **Ad hoc per-department integration** (each department wires up its own Firestore/Pub-Sub calls as needed). Rejected — this is exactly the "every department reinvents its own plumbing" risk described above, and makes cross-cutting changes (e.g. changing the message schema) require touching every department instead of one base class.

## Consequences

Adding a department is: create a folder, define a `SPEC`, implement `on_task_received`. The platform auto-discovers every `SPEC` at startup. Cross-cutting guarantees (audit logging, task writeback) are enforced by the base class rather than by convention.
