# ADR-0008: Ponytail enforcement starts lite, moves to full for the wider department roster

Status: Accepted

## Context

Ponytail (an anti-overengineering discipline ruleset for AI coding agents, installed on both Claude Code and Cursor for this project) enforces a "simplest sufficient implementation" bias with configurable strictness (`lite`/`full`/`ultra`). The project has a hard hackathon deadline and two distinct build phases: building the three core department designs (Finance & Audit, Engineering/SRE, Legal & Risk), and later building an additional department roster largely from scratch (Executive, HR, Sales, Support, Marketing, Product/Analytics).

## Decision

Run Ponytail at **`lite`** while building the three core departments, and switch to **`full`** once building the from-scratch additional roster. Never `ultra`, given the deadline.

## Alternatives considered

- **`full` or `ultra` throughout.** Rejected for the initial build phase — stricter enforcement adds friction that isn't worth paying while the team is still establishing the department contract and core platform plumbing (ADR-0005), where getting a working end-to-end loop matters more than minimality.
- **`lite` throughout.** Rejected for the later phase — five to six new departments built from scratch is exactly the situation where over-engineering risk compounds (each one an opportunity to introduce an unnecessary abstraction), and `full` enforcement is worth the friction there.

## Consequences

Enforcement level is a project-wide setting tracked in `/docs/system_prompt.md` and mirrored in `.cursor/rules/ponytail-hackathon.mdc` — update both together when the phase changes, and note the change here or in a follow-up ADR if the reasoning shifts.
