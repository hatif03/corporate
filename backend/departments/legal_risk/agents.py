"""Legal & Risk / Chief of Staff: 5 parallel judge lenses, each producing an
unverified Finding, then a deterministic grounding pass drops any finding
whose evidence_quote isn't verbatim in the context — "only an LLM judges,
only deterministic code verifies" (see docs/adr/0007).

Expected task.description format:
    STATEMENT: <the new decision/statement to check>
    CONTEXT:
    <freeform prior-decisions/constraints/commitments text>

ponytail: the 5 judges all see the same full CONTEXT text rather than a
domain-gated slice (legal_compliance only seeing legal facts, etc.) — real
domain-gated retrieval needs a tagged memory store that doesn't exist yet.
Upgrade path: once departments/legal_risk grows a memory_namespace-scoped
Firestore corpus with per-fact tags, filter CONTEXT per judge before this
call instead of passing the same block to all five.

ponytail: the plan's self-learning memory write-back (a fire-and-forget
fact_extractor that appends new durable facts after each statement) is not
implemented yet — deferred until the tagged memory store above exists, since
extracting facts with nowhere durable/queryable to put them would be dead
weight. The hot path (detect conflicts against existing context) is complete
and independent of that enhancement.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.adk_agents.factory import build_tiered_stage_agents
from app.adk_agents.runtime import run_agent_turn
from app.models import Task, TaskResult
from app.services.session_service import FirestoreSessionService
from departments.base import audited_task
from departments.legal_risk.schemas import Finding, GroundedConflict
from shared.custom_skills import with_custom_guidance
from shared.verification import ground_quote

DEPARTMENT_ID = "legal_risk"

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_LENSES = ["legal_compliance", "previous_decision", "priority_capacity", "dependency_blocker", "customer_promise"]


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _build_judge(lens: str) -> dict:
    return build_tiered_stage_agents(
        f"legal_judge_{lens}", instruction=_load_prompt(lens), description=f"Legal & Risk conflict judge: {lens}"
    )


_judges = {lens: _build_judge(lens) for lens in _LENSES}
_session_service = FirestoreSessionService()


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned)


def _split_statement_and_context(description: str) -> tuple[str, str]:
    if "CONTEXT:" not in description:
        return description.strip(), ""
    statement_part, context_part = description.split("CONTEXT:", 1)
    statement = statement_part.replace("STATEMENT:", "", 1).strip()
    return statement, context_part.strip()


@audited_task(DEPARTMENT_ID)
async def on_task_received(org_id: str, task: Task) -> TaskResult:
    tier = task.model_tier  # ADR-0013: the CEO picks flash/pro at create_task time
    statement, context_text = _split_statement_and_context(task.description)
    judge_input = with_custom_guidance(org_id, DEPARTMENT_ID, task.description)

    # No attachment wiring here (ADR-0013): 5 parallel text-only judges over
    # STATEMENT/CONTEXT, not a sequential "first stage sees the image" shape
    # — this department's whole job is text conflict-detection, so a vision
    # attachment has no natural place to land.
    async def run_judge(lens: str) -> Finding:
        raw = await run_agent_turn(_judges[lens][tier], _session_service, org_id, DEPARTMENT_ID, judge_input)
        data = _extract_json(raw)
        data["lens"] = lens
        return Finding(**data)

    findings = await asyncio.gather(*(run_judge(lens) for lens in _LENSES))

    grounded: list[GroundedConflict] = []
    for finding in findings:
        if not finding.conflict or not finding.evidence_quote or not finding.claim:
            continue
        located = ground_quote(finding.evidence_quote, context_text)
        if located is None:
            continue  # ungroundable claim — dropped, never surfaced
        grounded.append(
            GroundedConflict(lens=finding.lens, claim=finding.claim, grounded_quote=located, confidence=finding.confidence)
        )

    if not grounded:
        return TaskResult(
            success=True,
            summary=f"No grounded conflicts found for: {statement}",
            data={"conflicts": []},
            needs_human=False,
        )

    summary_lines = [f"- [{c.lens}] {c.claim} (evidence: \"{c.grounded_quote}\")" for c in grounded]
    summary = f"Potential conflict(s) detected for: {statement}\n" + "\n".join(summary_lines)

    return TaskResult(
        success=True,
        summary=summary,
        data={"conflicts": [c.model_dump() for c in grounded]},
        needs_human=True,
        human_question=f"{len(grounded)} grounded conflict(s) found for statement: {statement}",
    )
