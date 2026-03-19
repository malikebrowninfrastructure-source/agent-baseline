from __future__ import annotations

from typing import Any, Callable, Dict, Set

from tools.file_tools import write_text_file, write_json_file


ToolFn = Callable[..., Any]


TOOL_REGISTRY: Dict[str, ToolFn] = {
    "write_text_file": write_text_file,
    "write_json_file": write_json_file,
}


TOOL_CLASS_MAP: Dict[str, Set[str]] = {
    "file_tools": {"write_text_file", "write_json_file"},
    "validation_tools": set(),
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


def execute_tool(tool_name: str, allowed_tool_classes: list[str], **kwargs: Any) -> Any:
    if not is_tool_allowed(tool_name, allowed_tool_classes):
        raise PermissionError(
            f"Tool '{tool_name}' is not allowed for this task. Allowed classes: {allowed_tool_classes}"
        )

    tool_fn = get_tool(tool_name)
    return tool_fn(**kwargs)