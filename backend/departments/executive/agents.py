"""Office of the CEO: a cross-department digest agent, distinct from the CEO
orchestrator itself. Reads every department's Firestore task/agent state and
publishes a company-wide announcement to the shared board.

ponytail: the plan's third stage (an okr_tracker reasoning about progress
against goals) is deferred — there's no real OKR/goals data model yet, and a
stage that always says "no OKRs configured" would be dead weight, not a
genuine third pipeline step. Add it back once goals actually have somewhere
to live (a new Firestore collection, presumably), not before.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.adk_agents.tools.universal import write_board
from app.models import Task, TaskResult
from app.services import store
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task

DEPARTMENT_ID = "executive"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_stage_agents(name: str, prompt_file: str, extra_tools: list | None = None) -> dict:
    return build_tiered_stage_agents(
        name,
        instruction=_load_prompt(prompt_file),
        description=f"Office of the CEO pipeline stage: {name}",
        extra_tools=extra_tools,
    )


digest_agents = _build_stage_agents("executive_digest", "cross_department_digest")
announcement_agents = _build_stage_agents(
    "executive_announcement", "announcement_drafter", extra_tools=[write_board]
)

_session_service = FirestoreSessionService()


def _company_snapshot(org_id: str) -> dict:
    tasks_by_department: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for task in store.list_tasks(org_id):
        department = task.assignee or "unassigned"
        tasks_by_department[department][task.status.value] += 1

    agents_snapshot = [
        {"id": a.id, "department": a.department, "status": a.status.value} for a in store.list_agents(org_id)
    ]
    return {"tasksByDepartment": tasks_by_department, "agents": agents_snapshot}


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    tier = task.model_tier  # ADR-0013: the CEO picks flash/pro at create_task time
    # No attachment wiring here: this department's input is a synthesized
    # company-wide snapshot, not user-facing content — a vision attachment
    # has nowhere sensible to land.
    snapshot = _company_snapshot(org_id)
    digest = await run_agent_turn(
        digest_agents[tier], _session_service, org_id, DEPARTMENT_ID, json.dumps(snapshot, default=dict)
    )
    announcement = await run_agent_turn(
        announcement_agents[tier], _session_service, org_id, DEPARTMENT_ID, digest
    )

    return TaskResult(
        success=True,
        summary=announcement,
        data={"digest": digest, "snapshot": {k: dict(v) for k, v in snapshot["tasksByDepartment"].items()}},
        needs_human=False,
    )
