"""Per-org, per-agent custom guidance, added from the frontend (Settings ->
agent detail -> Skills tab). Department LlmAgents are module-level
singletons shared across every org (ADR-0013's per-tier-not-per-org
constraint), so per-org customization can't live in the shared agent
object's system instruction — it's injected into the per-call INPUT text
instead, which is already unique per task/org. Every department's
on_task_received wraps its first pipeline stage's input through
with_custom_guidance(); app/services/dispatch.py does the same for the
CEO's own turn.
"""

from __future__ import annotations

from app.services import store


def with_custom_guidance(org_id: str, agent_id: str, base_input: str) -> str:
    # "pending" skills (an agent's own propose_skill tool call, not yet
    # approved by the org owner) are deliberately excluded — see
    # app/services/store.py's add_agent_custom_skill docstring.
    skills = [s for s in store.list_agent_custom_skills(org_id, agent_id) if s.get("status", "active") == "active"]
    if not skills:
        return base_input
    guidance = "\n".join(f"- {s['title']}: {s['instructions']}" for s in skills)
    return f"Org-specific guidance for this agent:\n{guidance}\n\n{base_input}"
