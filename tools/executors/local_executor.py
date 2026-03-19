from __future__ import annotations

from typing import Any, Callable

from tools.executors.base import BaseExecutor


class LocalExecutor(BaseExecutor):
    def execute(self, tool_name: str, tool_fn: Callable[..., Any], **kwargs: Any) -> Any:
        return tool_fn(**kwargs)
