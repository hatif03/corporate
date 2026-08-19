---
name: new-department
description: Scaffold a new Corporate department — a Python package under backend/departments/ implementing the DepartmentSpec contract (ADR-0005), wired into audit logging and the shared verifier by default. Use whenever the user asks to add a new department/team to the office (e.g. "add a Marketing department", "create a Support department").
---

# Scaffold a new department

This skill generates a complete, working-but-minimal department package following the contract in `backend/departments/base.py` (see `/docs/adr/0005-department-contract-and-scaffolding.md` and `.cursor/rules/department-template.mdc`).

## Inputs to collect from the user before generating anything

1. **Department id** — lowercase snake_case, e.g. `marketing_comms`.
2. **Display name** — e.g. "Marketing & Comms".
3. **One-paragraph concept** — what this department does, in plain language.
4. **Pipeline stage names** — the ordered list of ADK sub-agents in its `SequentialAgent` (or note if it should be a `ParallelAgent` fan-out instead, like Legal & Risk's judge panel).
5. **Accepted task types** — the string task-type values the CEO can dispatch to this department.
6. Whether this department should be **A2A-exposed** (external-facing, like Sales/Support — see ADR-0004). Default: no.

If any of these are missing or ambiguous, ask before generating files — don't guess a department's purpose.

## Files to generate

Under `backend/departments/<dept_id>/`:

- **`__init__.py`** — exports `SPEC = DepartmentSpec(...)` populated from the collected inputs (including `on_task_received=on_task_received` imported from `agents.py`), `a2a_exposed` set per input 6.
- **`agents.py`** — a `SequentialAgent` (or `ParallelAgent`, per input 4) skeleton with one `LlmAgent` stub per pipeline stage, each with a placeholder `instruction=` pointing at its prompt file, model set to the project's pinned Gemini model constant (never hardcode a model string here — import from `backend/app/adk_agents/factory.py`'s shared constant).
- **`tools.py`** — empty stub with a comment pointing at the universal tools (`send_message`, `read_memory`, `write_memory`, `update_status`, `claim_task`, `report_result`) already available to every department; add department-specific `FunctionTool`s here as needed.
- **`schemas.py`** — Pydantic stubs for this department's task input/output payloads.
- **`aspects.py`** — empty dict stub (`ASPECTS: dict[str, Callable] = {}`) with a comment explaining these are verifier checkers for `backend/shared/verification.py`'s `vote_aspects()`, only needed if this department produces claims-with-evidence.
- **`prompts/*.md`** — one prompt file per pipeline stage, seeded with the one-paragraph concept and a `TODO` for the actual system prompt.
- **`tests/test_<dept_id>_smoke.py`** — one test that constructs a representative task, calls `on_task_received`, and asserts the writeback contract (task status changes, a reply message is produced).

## Wiring that must happen automatically, not left to the generated stub

- The generated `agents.py` must decorate its `on_task_received` function with `@audited_task(DEPARTMENT_ID)` (from `backend/departments/base.py`) and `__init__.py` must pass it as `SPEC.on_task_received` — this is what wires in hash-chained audit logging and the task-status/reply writeback; a department that forgets the decorator silently loses both.
- If the department has any `aspects.py` checkers, confirm they're actually registered in `SPEC.aspects` — a checker defined but not registered is a silent no-op.
- Append a row for the new department to the roster table in `/docs/system_prompt.md` (create the table if it doesn't exist yet).
- Remind the user (don't do it automatically) to add a matching entry to `/departments/<dept_id>.yaml` (zone/desk positions, accent palette, character roster) and to `frontend/src/scene/office/departments.ts` so it renders on the office floor — this skill only generates the backend package.
- If `a2a_exposed` is true, add a one-line note in the generated `__init__.py` pointing at ADR-0004 and the `to_a2a()` wiring pattern in `backend/app/main.py` — do not wire the A2A mount itself unless explicitly asked; that's a platform-level change, not a per-department one.

## After generating

Run the smoke test. Report which files were created and what's still a `TODO` (real prompts, real tool implementations) — this skill produces a correctly-wired skeleton, not a finished department.
