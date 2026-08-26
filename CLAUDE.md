# Corporate

A hosted multi-agent web app: departments of autonomous AI employees (Finance & Audit, Engineering/SRE, Legal & Risk, and a growing roster) working on a 2D office floor, coordinated by a CEO agent. Built for the All Things Agentic hackathon (deadline 2026-08-31), track: The Fortified Enterprise Fleet.

## Architecture rules

@docs/system_prompt.md

The file above is the canonical source of truth for every architectural convention in this project — monorepo layout, the department contract, ADK/Gemini conventions, Firestore/Pub-Sub access rules, secrets policy, A2A scope, testing conventions, and the definition of done. Read it before making changes. If a convention needs to change, change it there first.

## Quick pointers

- Department contract: `backend/departments/base.py` (see ADR-0005 in `/docs/adr/`)
- Shared utilities (use before reimplementing): `backend/shared/audit_chain.py`, `backend/shared/verification.py`, `backend/shared/privacy_pipeline.py`
- Scaffolding a new department: use the `new-department` skill in `.claude/skills/`
- ADK conventions reference: `.claude/skills/google-adk-python/SKILL.md`
- Every architectural decision has a record in `/docs/adr/` — read the relevant ones before touching Pub/Sub routing, session persistence, A2A, or the fraud/verification pipelines.
- `/docs/PROJECT_HISTORY.md` is the full chronological narrative tying every ADR together — what was built, what was seriously explored and deliberately not built, and why. Read it for "how did we get here," not just "what's the rule."
