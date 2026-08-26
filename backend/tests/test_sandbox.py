"""Real subprocess tests — no mocking of the sandbox boundary itself,
since the whole point of app/services/sandbox.py is that a real OS process
is what makes it safe. Only the org-scoped tool lookups underneath
call_tool are mocked (store/memory_search), same as everywhere else in this
suite. These spawn a real python -m app.services.sandbox_runner each time,
so they're slower than a typical unit test but exercise the actual
isolation boundary — see docs/system_prompt.md's B4 verification note."""

from unittest.mock import patch

from app.models import Task, TaskStatus
from app.services import sandbox


async def test_run_sandboxed_one_round_trip_for_multi_lookup():
    tasks = [
        Task(id="t1", title="a", description="d", task_type="x", status=TaskStatus.DOING, assignee="eng", created_by="ceo"),
        Task(id="t2", title="b", description="d", task_type="x", status=TaskStatus.DOING, assignee="eng", created_by="ceo"),
        Task(id="t3", title="c", description="d", task_type="x", status=TaskStatus.DONE, assignee="eng", created_by="ceo"),
    ]
    code = (
        'tasks = call_tool("list_tasks_tool")\n'
        'doing = [t for t in tasks if t["status"] == "doing"]\n'
        "result = {'doing_count': len(doing)}\n"
    )
    with patch("app.services.sandbox.store.list_tasks", return_value=tasks) as mock_list:
        out = await sandbox.run_sandboxed("org-test", "ceo", code)

    assert out == {"success": True, "result": {"doing_count": 2}}
    mock_list.assert_called_once()  # one round trip, not N


async def test_run_sandboxed_rejects_malicious_import():
    out = await sandbox.run_sandboxed("org-test", "ceo", "import os\nresult = os.listdir('.')")
    assert out["success"] is False
    assert "__import__" in out["error"]


async def test_run_sandboxed_rejects_dunder_gadget():
    out = await sandbox.run_sandboxed("org-test", "ceo", "result = ().__class__.__bases__[0].__subclasses__()")
    assert out["success"] is False


async def test_run_sandboxed_kills_runaway_loop_on_timeout():
    with patch.object(sandbox, "SANDBOX_TIMEOUT_SECONDS", 1):
        out = await sandbox.run_sandboxed("org-test", "ceo", "while True:\n    pass")
    assert out == {"success": False, "error": "sandbox exceeded 1s and was killed"}


async def test_run_sandboxed_enforces_tool_call_budget():
    code = "n = 0\nfor _ in range(10):\n    call_tool('list_tasks_tool')\n    n += 1\nresult = n\n"
    with (
        patch("app.services.sandbox.store.list_tasks", return_value=[]),
        patch.object(sandbox, "MAX_TOOL_CALLS_PER_TURN", 2),
    ):
        out = await sandbox.run_sandboxed("org-test", "ceo", code)

    assert out["success"] is False
    assert "budget" in out["error"]


async def test_run_sandboxed_unknown_tool_name_surfaces_as_error():
    out = await sandbox.run_sandboxed("org-test", "ceo", "result = call_tool('delete_everything')")
    assert out["success"] is False
    assert "not in the sandbox" in out["error"]


async def test_run_sandboxed_non_serializable_result_is_reported():
    out = await sandbox.run_sandboxed("org-test", "ceo", "result = 1j")  # complex — valid Python, not JSON
    assert out["success"] is False
    assert "JSON-serializable" in out["error"]


async def test_run_sandboxed_compile_error_is_reported():
    out = await sandbox.run_sandboxed("org-test", "ceo", "result = 1 +")
    assert out["success"] is False
