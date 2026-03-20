from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional, Set

from runtime.logging import utc_now_iso
from runtime.tracing import get_tracer
from enforce_policy import enforce_tool_policy, enforce_shell
from tools.file_tools import write_text_file, write_json_file, write_run_summary
from tools.shell_tools import run_shell_command, run_sandboxed_shell_command
from tools.executors import LocalExecutor, SandboxExecutor, OpenShellExecutor


ToolFn = Callable[..., Any]


TOOL_REGISTRY: Dict[str, ToolFn] = {
    "write_text_file": write_text_file,
    "write_json_file": write_json_file,
    "write_run_summary": write_run_summary,
    "run_shell_command": run_shell_command,
    "run_sandboxed_shell_command": run_sandboxed_shell_command,
}


TOOL_CLASS_MAP: Dict[str, Set[str]] = {
    "file_tools": {"write_text_file", "write_json_file", "write_run_summary"},
    "validation_tools": set(),
    "shell_tools": {"run_shell_command", "run_sandboxed_shell_command"},
}


TOOL_BACKEND_MAP: Dict[str, str] = {
    "write_text_file": "local",
    "write_json_file": "local",
    "write_run_summary": "local",
    "run_shell_command": "openshell",
    "run_sandboxed_shell_command": "sandbox",
}


EXECUTOR_BACKENDS = {
    "local": LocalExecutor(),
    "sandbox": SandboxExecutor(),
    "openshell": OpenShellExecutor(),
}


def get_tool(tool_name: str) -> ToolFn:
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{tool_name}' is not registered")
    return TOOL_REGISTRY[tool_name]


def is_tool_allowed(tool_name: str, allowed_tool_classes: list[str]) -> bool:
    allowed_concrete_tools: Set[str] = set()
    for tool_class in allowed_tool_classes:
        allowed_concrete_tools.update(TOOL_CLASS_MAP.get(tool_class, set()))
    return tool_name in allowed_concrete_tools


def get_backend_for_tool(tool_name: str) -> str:
    return TOOL_BACKEND_MAP.get(tool_name, "local")


def execute_tool(tool_name: str, allowed_tool_classes: list[str], **kwargs: Any) -> Any:
    if not is_tool_allowed(tool_name, allowed_tool_classes):
        raise PermissionError(
            f"Tool '{tool_name}' is not allowed for this task. "
            f"Allowed classes: {allowed_tool_classes}"
        )

    enforce_tool_policy(tool_name)

    backend_name = get_backend_for_tool(tool_name)
    if backend_name in ("openshell", "sandbox"):
        enforce_shell(tool_name)

    tool_fn = get_tool(tool_name)

    if backend_name not in EXECUTOR_BACKENDS:
        raise ValueError(f"Execution backend '{backend_name}' is not configured")

    executor = EXECUTOR_BACKENDS[backend_name]

    _t0 = time.monotonic()
    _started_at = utc_now_iso()
    _error: Optional[str] = None
    try:
        result = executor.execute(tool_name=tool_name, tool_fn=tool_fn, **kwargs)
    except Exception as exc:
        _error = str(exc)
        raise
    finally:
        tracer = get_tracer()
        if tracer is not None:
            tracer.record_tool_call(
                tool_name=tool_name,
                backend=backend_name,
                started_at=_started_at,
                duration_ms=int((time.monotonic() - _t0) * 1000),
                error=_error,
            )
    return result
