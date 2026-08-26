"""Tools available to every agent (CEO and department agents alike).

Plain async functions — ADK wraps these as FunctionTools automatically from
their name, docstring, and type hints when passed in an LlmAgent's tools=[].
`tool_context: ToolContext` is auto-injected by ADK (matched by type
annotation), never exposed to the LLM as a schema parameter.

ponytail: claim_task/report_result (proactive task-claiming) aren't
implemented yet — nothing in the current CEO-dispatches/department-replies
flow needs them, since backend/departments/base.py's @audited_task already
handles the task status + reply writeback automatically. Add them when a
Workers-style proactive-claim flow (see docs/system_prompt.md, Phase 3)
actually needs an agent to pull from a shared queue.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from google.adk.tools.tool_context import ToolContext

from app.models import Act, Task, TaskStatus
from app.services import pubsub_client, store
from app.services.embeddings import embed_text
from app.services.firestore_client import org_doc
from app.services.memory_search import search_memory as _search_memory


def _ids(tool_context: ToolContext) -> tuple[str, str]:
    return tool_context.session.user_id, tool_context.session.id


async def send_message(
    to: str, act: str, subject: str, body: str, tool_context: ToolContext
) -> dict:
    """Send a message to another agent (or 'ceo' / 'broadcast').

    Args:
        to: recipient agent id, or the literal 'ceo' or 'broadcast'.
        act: one of request, inform, propose, query, agree, refuse, done.
        subject: a short human-readable summary of the message.
        body: the message content.
    """
    org_id, agent_id = _ids(tool_context)
    message = pubsub_client.publish_message(
        org_id=org_id, from_agent=agent_id, to=to, act=Act(act), subject=subject, body=body
    )
    return {"sent": True, "message_id": message.id}


async def create_task(
    title: str,
    description: str,
    task_type: str,
    assignee: str,
    tool_context: ToolContext,
    priority: int = 3,
    model_tier: Literal["flash", "pro"] = "flash",
    include_attachment: bool = True,
) -> dict:
    """Create a new task card on the kanban board and assign it to a department.

    Args:
        title: short task title.
        description: full task description / instructions for the assignee.
        task_type: the task-type string the assignee department accepts.
        assignee: the department id to assign this task to.
        priority: 1 (highest) to 5 (lowest), default 3.
        model_tier: which Gemini tier the assignee's turn(s) should run on —
            "flash" (default, fast/cheap) or "pro" (slower, more capable —
            use for genuinely complex reasoning, not routine work).
        include_attachment: whether to carry the image attached to the
            current dispatch (if any) onto this task. Defaults to true — a
            human dispatch is usually about one thing, so every task from it
            gets the image unless you set this false for a task you know is
            unrelated (e.g. the dispatch attached a screenshot for one bug
            but you're also creating an unrelated marketing task).
    """
    org_id, agent_id = _ids(tool_context)
    attachment = store.get_ceo_pending_attachment(org_id) if include_attachment else None
    task = Task(
        id=f"task-{uuid.uuid4().hex[:10]}",
        title=title,
        description=description,
        task_type=task_type,
        status=TaskStatus.TODO,
        assignee=assignee,
        created_by=agent_id,
        priority=priority,
        model_tier=model_tier,
        attachment=attachment,
    )
    store.create_task(org_id, task)
    # conversation == task.id is the correlation id the receiving department
    # uses to look the task back up in app/services/dispatch.py.
    pubsub_client.publish_message(
        org_id=org_id,
        from_agent=agent_id,
        to=assignee,
        act=Act.REQUEST,
        subject=title,
        body=description,
        conversation=task.id,
    )
    return {"task_id": task.id}


async def update_task_status(task_id: str, status: str, tool_context: ToolContext) -> dict:
    """Manually change a task's kanban column (todo/doing/blocked/done)."""
    org_id, _ = _ids(tool_context)
    store.update_task(org_id, task_id, status=TaskStatus(status).value)
    return {"updated": True}


async def write_board(markdown: str, tool_context: ToolContext) -> dict:
    """Overwrite the shared company blackboard (org-wide notes/status). CEO-only in practice."""
    org_id, agent_id = _ids(tool_context)
    org_doc(org_id, "board", "main").set(
        {"markdown": markdown, "updatedAt": datetime.now(timezone.utc), "updatedBy": agent_id}
    )
    return {"written": True}


async def list_agents_tool(tool_context: ToolContext) -> list[dict]:
    """List every agent in the company and their current status."""
    org_id, _ = _ids(tool_context)
    return [a.model_dump(mode="json", by_alias=True) for a in store.list_agents(org_id)]


async def list_tasks_tool(tool_context: ToolContext, status: str | None = None) -> list[dict]:
    """List tasks on the kanban board, optionally filtered by status."""
    org_id, _ = _ids(tool_context)
    filt = TaskStatus(status) if status else None
    return [t.model_dump(mode="json", by_alias=True) for t in store.list_tasks(org_id, filt)]


async def read_memory(tool_context: ToolContext, limit: int = 10) -> str:
    """Read your most recent long-term memory notes from previous turns."""
    org_id, agent_id = _ids(tool_context)
    entries = store.list_memory(org_id, agent_id, limit_count=limit)
    if not entries:
        return ""
    return "\n".join(f"- {e['text']}" for e in reversed(entries))


async def search_memory_tool(query: str, tool_context: ToolContext, top_k: int = 5) -> str:
    """Semantically search your long-term memory for notes relevant to
    `query` — use this instead of read_memory when you need something
    specific rather than just your most recent notes."""
    org_id, agent_id = _ids(tool_context)
    hits = _search_memory(org_id, query, agent_id=agent_id, top_k=top_k)
    if not hits:
        return ""
    return "\n".join(f"- ({h.score:.2f}) {h.text}" for h in hits)


async def write_memory(text: str, tool_context: ToolContext) -> dict:
    """Append a note to your own long-term memory for future turns (and
    semantic search, see the Memory tab) to find."""
    org_id, agent_id = _ids(tool_context)
    embedding = embed_text(text)
    memory_id = store.append_memory(org_id, agent_id, text, embedding)
    return {"saved": True, "memory_id": memory_id}


async def set_note(note: str, tool_context: ToolContext) -> dict:
    """Set a short human-readable status note shown on your office-floor avatar."""
    org_id, agent_id = _ids(tool_context)
    org_doc(org_id, "agents", agent_id).update({"note": note})
    return {"updated": True}
