"""Parent-side orchestrator for the execute_python sandbox — spawns the
child (app/services/sandbox_runner.py) as a real OS subprocess, is the only
side of the pipe that ever executes a real tool call, and is the only side
that ever holds org/agent context. See sandbox_runner.py's module docstring
for the full isolation design.

Tool allowlist v1 is deliberately read-only: a sandboxed snippet can look
things up (tasks, agents, memory) but can't write anything — write tools
stay individually visible in the outer turn's own trace/audit log instead
of proxied opaquely through a snippet. Add write tools once a sandboxed-
write audit story is designed, not now.
"""

from __future__ import annotations

import asyncio
import json
import sys

from app.models import TaskStatus
from app.services import store
from app.services.memory_search import search_memory as _search_memory

SANDBOX_TIMEOUT_SECONDS = 20
# Reuses the same runaway-loop backstop app/adk_agents/runtime.py applies to
# a whole agent turn, as the sandbox's own per-snippet tool-call cap.
from app.adk_agents.runtime import MAX_TOOL_CALLS_PER_TURN  # noqa: E402


async def _dispatch_tool(org_id: str, agent_id: str, name: str, args: dict) -> object:
    if name == "list_tasks_tool":
        status = args.get("status")
        filt = TaskStatus(status) if status else None
        return [t.model_dump(mode="json", by_alias=True) for t in store.list_tasks(org_id, filt)]
    if name == "list_agents_tool":
        return [a.model_dump(mode="json", by_alias=True) for a in store.list_agents(org_id)]
    if name == "search_memory_tool":
        hits = _search_memory(org_id, args["query"], agent_id=agent_id, top_k=args.get("top_k", 5))
        return [{"agent_id": h.agent_id, "text": h.text, "score": h.score} for h in hits]
    if name == "read_memory":
        entries = store.list_memory(org_id, agent_id, limit_count=args.get("limit", 10))
        return "\n".join(f"- {e['text']}" for e in reversed(entries)) if entries else ""
    raise ValueError(f"'{name}' is not in the sandbox's read-only tool allowlist")


async def run_sandboxed(org_id: str, agent_id: str, code: str) -> dict:
    """Runs `code` in an isolated subprocess, servicing any whitelisted
    tool calls it makes with real data, and returns
    {"success": True, "result": ...} or {"success": False, "error": ...}.
    Never raises — every failure mode (compile error, snippet exception,
    timeout, tool-budget overrun) comes back as a structured result."""
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.services.sandbox_runner",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    assert process.stdin and process.stdout

    async def _converse() -> dict:
        process.stdin.write((json.dumps({"code": code}) + "\n").encode())
        await process.stdin.drain()

        tool_calls = 0
        while True:
            line = await process.stdout.readline()
            if not line:
                stderr = (await process.stderr.read()).decode(errors="replace") if process.stderr else ""
                return {"success": False, "error": f"sandbox process exited without a result: {stderr[-500:]}"}

            message = json.loads(line)
            if message["type"] == "done":
                return {"success": True, "result": message["result"]}
            if message["type"] == "error":
                return {"success": False, "error": message["message"]}

            # message["type"] == "tool_call"
            tool_calls += 1
            if tool_calls > MAX_TOOL_CALLS_PER_TURN:
                process.stdin.write((json.dumps({"type": "tool_error", "message": "tool call budget exceeded"}) + "\n").encode())
                await process.stdin.drain()
                continue
            try:
                result = await _dispatch_tool(org_id, agent_id, message["name"], message.get("args", {}))
                process.stdin.write((json.dumps({"type": "tool_result", "result": result}) + "\n").encode())
            except Exception as exc:  # noqa: BLE001 - reported back to the snippet as a normal exception
                process.stdin.write((json.dumps({"type": "tool_error", "message": str(exc)}) + "\n").encode())
            await process.stdin.drain()

    try:
        return await asyncio.wait_for(_converse(), timeout=SANDBOX_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return {"success": False, "error": f"sandbox exceeded {SANDBOX_TIMEOUT_SECONDS}s and was killed"}
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
