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

A full pixel-level clone of an MIT-licensed reference app's UI, at the
user's explicit request ("copy everything, to the last detail"), fetched
directly from the live repo via `gh api` (not docs, not assumptions) and
ported with attribution:

- `frontend/src/design/tokens.css` / `global.css`: the complete light and
  dark token sets (colors, type scale, spacing, shadows), the cream
  noise-texture background, custom scrollbars, the custom text cursor, the
  focus ring, the `.corp-tip` tooltip system, and the step-timing
  animations are direct ports, not just "adapted."
- `frontend/src/lib/theme.ts`: the light/dark theme-toggle module, ported
  near-verbatim.
- `frontend/src/components/{PixelButton,PixelBadge,PixelPanel,Icon,
  AgentCard,AgentStrip,SidebarSplitter}.tsx`: component primitives and the
  bottom-strip roster layout, ported with data fields adapted to
  Corporate's own model (Agent.action/note/progress) in place of fields
  with no Corporate equivalent (a context-token gauge, drag-to-reorder).
  `Icon.tsx`'s 24 pixel-SVG icons are the reference's literal path data;
  icons for tabs the reference doesn't have (Knowledge, Graph, Memory,
  etc.) are original, drawn in the same 16x16/hairline style.
- The title-bar -> office-floor -> bottom-roster-strip layout skeleton is
  a direct structural port.

**Not copied, and why** (see `docs/PROJECT_HISTORY.md` and
`docs/adr/0016-agent-capability-expansion.md` for the full reasoning):
the reference's own tileset art (LimeZu "Modern Interiors", separately
licensed, not covered by the MIT grant on their original code — Corporate
keeps its Kenney CC0 tileset, rearranged into the same open-plan-floor
layout philosophy instead), "The Office" character names/personas/
dialogue and the "Munder Difflin" brand (thematic/trademark-adjacent
parody content specific to their product identity — Corporate keeps its
own name, logo, and original agent personas), and anything with no
Corporate equivalent (a real interactive pty terminal, Monaco/git/file-tree
panels, AI-engine/MCP settings, Electron-only window chrome).

| Source | Author | License | Link |
|---|---|---|---|
| Design system + UI components (colors, type, spacing, shadows, animation, layout, icons) | chaitanyagiri | MIT | https://github.com/chaitanyagiri/munder-difflin |

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
