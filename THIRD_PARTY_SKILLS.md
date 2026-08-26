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
