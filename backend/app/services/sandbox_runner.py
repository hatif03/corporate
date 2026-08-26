"""The execute_python sandbox's CHILD process — run via
`python -m app.services.sandbox_runner`, never imported directly. This
process never touches Firestore, Pub/Sub, or any credential: it has no
app.services.store import, no Gemini client, nothing. When the snippet it's
given calls a whitelisted tool, it writes a line-delimited JSON "tool_call"
request to stdout and blocks reading a "tool_result"/"tool_error" response
line from stdin — the parent (app/services/sandbox.py), which DOES have
real org/agent context, is the only side that ever executes a real tool.

Isolation model (see docs/system_prompt.md's B4 design note): a real OS
subprocess is the actual security boundary (the parent can always kill()
it, unlike an in-process thread with a `while True`). RestrictedPython's
compile_restricted runs inside that boundary as defense-in-depth on top —
it closes the classic `().__class__.__bases__` gadget that a bare
in-process exec() with a builtins allowlist alone can't. Neither
alone would be enough; both together is the real design.

ponytail: RLIMIT_CPU/RLIMIT_AS are POSIX-only (Cloud Run's actual Linux
runtime) and silently no-op on local Windows dev, where the parent's own
SANDBOX_TIMEOUT_SECONDS kill remains the operative control either way.
"""

from __future__ import annotations

import json
import operator
import sys

from RestrictedPython import compile_restricted_exec, safe_globals
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import full_write_guard, guarded_iter_unpack_sequence, safer_getattr

try:
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
except ImportError:
    pass  # no `resource` module on Windows — see module docstring

_INPLACE_OPS = {
    "+=": operator.iadd, "-=": operator.isub, "*=": operator.imul, "/=": operator.itruediv,
    "//=": operator.ifloordiv, "%=": operator.imod, "**=": operator.ipow,
}


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _recv() -> dict:
    line = sys.stdin.readline()
    if not line:
        raise EOFError("parent closed the pipe")
    return json.loads(line)


def _make_call_tool():
    def call_tool(name: str, **kwargs):
        _send({"type": "tool_call", "name": name, "args": kwargs})
        response = _recv()
        if response.get("type") == "tool_error":
            raise RuntimeError(response.get("message", "tool call failed"))
        return response.get("result")

    return call_tool


def run() -> None:
    request = _recv()
    code = request["code"]

    compiled = compile_restricted_exec(code)
    if compiled.errors:
        _send({"type": "error", "message": "; ".join(compiled.errors)})
        return

    restricted_globals: dict = dict(safe_globals)
    restricted_globals.update(
        {
            "_getattr_": safer_getattr,
            "_write_": full_write_guard,
            "_getiter_": default_guarded_getiter,
            "_getitem_": default_guarded_getitem,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_inplacevar_": lambda op, x, y: _INPLACE_OPS[op](x, y),
            "call_tool": _make_call_tool(),
        }
    )
    local_vars: dict = {}
    try:
        exec(compiled.code, restricted_globals, local_vars)  # noqa: S102 - the whole point of this module
    except Exception as exc:  # noqa: BLE001 - any snippet failure becomes a structured error, never a crash
        _send({"type": "error", "message": str(exc)})
        return

    try:
        json.dumps(local_vars.get("result"))  # ensure it's actually serializable before claiming success
    except TypeError:
        _send({"type": "error", "message": "the snippet's `result` value isn't JSON-serializable"})
        return
    _send({"type": "done", "result": local_vars.get("result")})


if __name__ == "__main__":
    run()
