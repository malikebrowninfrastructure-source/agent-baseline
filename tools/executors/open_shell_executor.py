from __future__ import annotations

from typing import Any, Callable

from tools.executors.base import BaseExecutor


class OpenShellExecutor(BaseExecutor):
    """
    Executes shell-backed tool functions via direct subprocess dispatch.

    Current behaviour: delegates to tool_fn(**kwargs) and logs the routing
    decision so backend activity is visible in execution logs.

    Future integration shape:
    - Add per-run working_directory scoping (scope cwd to outputs/runs/<run_id>)
    - Add timeout enforcement to cap long-running commands
    - Add an allowed_commands allowlist for policy-level shell access control
    - Add environment variable injection (clean env per run)
    - Replace with a proper isolation layer (Docker, nsjail, firejail) when
      moving from dev/test to production workloads
    - Wire return-code and stderr into structured ExecutionSchema fields rather
      than raising exceptions, so the verifier can assess shell failures
    """

    def execute(self, tool_name: str, tool_fn: Callable[..., Any], **kwargs: Any) -> Any:
        print(f"[OpenShellExecutor] routing '{tool_name}' via openshell backend")
        return tool_fn(**kwargs)
