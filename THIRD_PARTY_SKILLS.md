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

Considered and dropped (see ADR-0014 for why): `security-guidance` (a
Claude-Code editor hook, not domain knowledge an LLM turn can act on),
`saas-metrics-coach` (ARR/MRR/churn coaching doesn't apply to per-invoice
review), `emails` (multi-email sequence design doesn't apply to
`copy_drafter`, which drafts one piece of copy per task).

## Frontend design system

`frontend/src/design/tokens.css` and `frontend/src/design/global.css` adapt
the color palette, type scale, spacing scale, shadow/border system, and CSS
animation mechanics (stepped-timing hover/press/tab/status-dot patterns)
from an MIT-licensed reference app's design system. Fonts (Press Start 2P,
Inter, JetBrains Mono), color tokens, and interaction timings are a close
adaptation; Corporate's own office-floor scene (`frontend/src/scene/office/`,
Kenney CC0 tileset), agent/department content, and all product copy are
original to this project — no branded characters or copy from the reference
are reproduced.

| Source | Author | License | Link |
|---|---|---|---|
| Design system (colors, type, spacing, shadows, animation) | chaitanyagiri | MIT | https://github.com/chaitanyagiri/munder-difflin |

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
