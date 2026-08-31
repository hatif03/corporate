# Third-party skill excerpts

Several department prompts (`backend/departments/*/prompts/*.md`) include a
short "adapted from" section drawing on the domain technique from a curated,
open-source skill. See ADR-0014 for why and how these were chosen. Every
skill below is MIT-licensed; only a short, adapted excerpt is used — read
the original for the full skill.

| Department stage | Excerpt basis | Author | Source |
|---|---|---|---|
| `engineering_sre` / triage | `diagnosing-bugs` | Matt Pocock | https://github.com/mattpocock/skills |
| `engineering_sre` / cascade_predictor | `chaos-engineering` | claude-code-skills | https://github.com/alirezarezvani/claude-skills |
| `finance_audit` / accountant | `financial-analyst` | alirezarezvani | https://github.com/alirezarezvani/claude-skills |
| `marketing_comms` / brief_intake | `storybrand-messaging` | wondelai | https://github.com/wondelai/skills |
| `marketing_comms` / copy_drafter | `copywriting` | Corey Haines | https://github.com/coreyhaines31/marketingskills |
| `sales_crm` / lead_qualifier | `revops` | Corey Haines | https://github.com/coreyhaines31/marketingskills |
| `sales_crm` / outreach_drafter | `sales-enablement` | Corey Haines | https://github.com/coreyhaines31/marketingskills |
| `legal_risk` / legal_compliance | `general-counsel-advisor` | alirezarezvani | https://github.com/alirezarezvani/claude-skills |
| `executive` / cross_department_digest | `board-deck-builder` | alirezarezvani | https://github.com/alirezarezvani/claude-skills |
| `executive` / announcement_drafter | `internal-comms` | alirezarezvani | https://github.com/alirezarezvani/claude-skills |

Considered and dropped (see ADR-0014 for why): `security-guidance` (a
Claude-Code editor hook, not domain knowledge an LLM turn can act on),
`saas-metrics-coach` (ARR/MRR/churn coaching doesn't apply to per-invoice
review), `emails` (multi-email sequence design doesn't apply to
`copy_drafter`, which drafts one piece of copy per task).

## Departments with no genuine third-party fit — original house skills instead

A later research pass looked for real, well-used, permissively-licensed
skills for the remaining 3 departments and found none that genuinely fit
(not just name-matched) — every candidate assumed a domain (strategic HR,
CCO-level retention, product-growth/experiment analytics) these
departments' actual narrow tasks don't have. Per this project's own
"don't force fits" discipline, each got a short **original** house-skill
note instead (see each prompt's own "House skill" section for the full
text and reasoning) — not attributed to any external source:

| Department stage | House skill |
|---|---|
| `hr_people_ops` / handbook_qa | grounded-or-say-so |
| `customer_support` / response_drafter | cite-or-escalate |
| `product_analytics` / metrics_analyst | never-invent-a-number |

## Frontend design system and UI

An MIT-licensed reference app's UI was an early visual and structural
inspiration — a starting reference point looked up directly from the live
repo via `gh api` (not docs, not assumptions) — for Corporate's own
office-floor Command Center. Corporate's design system (`frontend/src/
design/tokens.css`/`global.css`, `frontend/src/lib/theme.ts`), its
component set (`PixelButton`, `PixelBadge`, `PixelPanel`, `Icon`,
`AgentCard`, `AgentStrip`, `SidebarSplitter`, and the rest), and its
title-bar → office-floor → bottom-roster-strip layout have since been
substantially built out and diverged from that starting point to fit
Corporate's own data model, tab set (Ask-me, Triggers, Workers, Knowledge,
Board, Graph — none of which the reference has), and product identity —
no code from the reference is reused as-is.

**Everything in the shipped app is Corporate's own**, not the reference's:
the office floor's tileset art is Kenney's CC0 "1-Bit Pack" (see below),
rearranged into Corporate's own 3×3 room-and-corridor layout, not the
reference's own separately-licensed tileset; agent names, personas,
dialogue, and branding are original, with no resemblance to "The Office"
or the "Munder Difflin" name the reference itself parodies; and anything
with no Corporate equivalent (a real interactive pty terminal, Monaco/
git/file-tree panels, AI-engine/MCP settings, Electron-only window chrome)
was never built at all.

| Source | Author | License | Link |
|---|---|---|---|
| Early visual/structural inspiration for the office-floor Command Center UI | chaitanyagiri | MIT | https://github.com/chaitanyagiri/munder-difflin |

## Office-floor tileset

The office floor's tiles (walls, doors, corridor floors, plants, the
bookshelf) come from Kenney's "1-Bit Pack" (`frontend/src/assets/kenney/
one_bit_pack_extracted/`), rearranged into Corporate's own 3×3
room-and-corridor layout — not the source repo's own layout. Mentioned in
prose in `docs/PROJECT_HISTORY.md` already; listed here too since this is
the canonical attribution file.

| Source | Author | License | Link |
|---|---|---|---|
| 1-Bit Pack tileset | Kenney | CC0 (public domain) | https://kenney.nl/assets/1-bit-pack |

## Agent loop hardening

`backend/app/adk_agents/runtime.py`'s doom-loop guard/per-turn tool-call cap
and `backend/app/services/compaction.py`'s session-compaction design (tail
budget kept verbatim, tool output truncated before summarizing anything
older, prior summaries chained rather than re-summarized) are adapted from
a real open-source coding agent's own agent-loop implementation. See
ADR-0015 for the full research and design rationale.

| Source | Author | License | Link |
|---|---|---|---|
| Doom-loop guard, session compaction | anomalyco (opencode) | MIT | https://github.com/anomalyco/opencode |
