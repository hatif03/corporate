"""Engineering & SRE-specific integration calls. notify_slack_channel is
the first real consumer of app/services/integration_broker.py — proof the
broker is actually wired into a department, not just a standalone module.

This is called directly from on_task_received (deterministic: "high
severity -> notify Slack" is mechanism, not LLM judgment) rather than
exposed as an ADK tool the pipeline's LLM stages could choose to invoke or
skip — see docs/system_prompt.md's note that routing/notification decisions
are mechanism, the same reasoning already applied to publish_message's
hop-cap and requires_reply derivation.
"""

from __future__ import annotations

from app.services.integration_broker import call_integration

SLACK_INTEGRATION_ID = "slack"
JIRA_INTEGRATION_ID = "jira"
DEPARTMENT_ID = "engineering_sre"


async def notify_slack_channel(org_id: str, channel: str, text: str) -> dict:
    """Post a message to a Slack channel via the configured Slack integration.
    Fails soft (returns posted=False) if no Slack integration is configured
    for this org yet, or if engineering_sre isn't in that integration's
    connected_departments allowlist — the incident's own task result already
    carries the same information regardless."""
    try:
        response = await call_integration(
            org_id, SLACK_INTEGRATION_ID, DEPARTMENT_ID, "POST", "/chat.postMessage", json={"channel": channel, "text": text}
        )
    except ValueError as exc:
        return {"posted": False, "reason": str(exc)}
    return {"posted": response.status_code == 200, "status_code": response.status_code}


async def create_jira_ticket(org_id: str, project_key: str, summary: str, description: str) -> dict:
    """File a Jira issue via the configured Jira integration, for
    high-cascade-risk incidents. Same deterministic-call-site,
    fail-soft-when-unconfigured shape as notify_slack_channel above — the
    INTEGRATION_TEMPLATES catalog has declared a jira template since ADR-0013
    but nothing in the codebase actually called it until now."""
    try:
        response = await call_integration(
            org_id,
            JIRA_INTEGRATION_ID,
            DEPARTMENT_ID,
            "POST",
            "/issue",
            json={
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "issuetype": {"name": "Bug"},
                    "description": description,
                }
            },
        )
    except ValueError as exc:
        return {"filed": False, "reason": str(exc)}
    return {"filed": response.status_code in (200, 201), "status_code": response.status_code}
