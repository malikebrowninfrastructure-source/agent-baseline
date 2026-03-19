from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseExecutor(ABC):
    @abstractmethod
    def execute(self, tool_name: str, tool_fn: Callable[..., Any], **kwargs: Any) -> Any: ...
