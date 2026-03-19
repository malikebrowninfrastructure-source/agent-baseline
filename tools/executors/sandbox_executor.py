from __future__ import annotations

from typing import Any, Callable

from tools.executors.base import BaseExecutor


class SandboxExecutor(BaseExecutor):
    def execute(self, tool_name: str, _tool_fn: Callable[..., Any], **_kwargs: Any) -> Any:
        raise NotImplementedError(
            f"Sandbox execution backend not implemented yet for tool '{tool_name}'"
        )
