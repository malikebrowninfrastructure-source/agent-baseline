from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.common_types import RiskLevel


_RISK_RANK = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
}


class RunPolicy(BaseModel):
    """
    Execution policy bound to a single run. Defaults are restrictive.
    Callers must explicitly opt into permissive capabilities.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- Model governance ---
    allowed_backends: list[str] = Field(
        default=["local", "cloud"],
        description="Model backends permitted for this run. Any unlisted backend is blocked.",
    )
    allow_cloud_fallback: bool = Field(
        default=False,
        description=(
            "If False (default), agents hard-fail when local model is unavailable "
            "instead of silently escalating to cloud."
        ),
    )

    # --- Tool governance ---
    denied_tools: list[str] = Field(
        default_factory=list,
        description="Tools blocked unconditionally, even if present in task.allowed_tools.",
    )
    allow_shell_execution: bool = Field(
        default=False,
        description=(
            "If False (default), shell tools (run_shell_command, run_sandboxed_shell_command) "
            "are blocked. Must be True to permit any shell execution."
        ),
    )

    # --- Approval gate ---
    require_approval_above: Optional[RiskLevel] = Field(
        default=RiskLevel.MEDIUM,
        description=(
            "Tasks at or above this risk level require approved=True before execution. "
            "Defaults to MEDIUM, blocking all non-low-risk tasks without explicit sign-off."
        ),
    )
    approved: bool = Field(
        default=False,
        description="Explicit approval grant. Must be True when task risk meets require_approval_above.",
    )

    # --- Helpers (no mutation, safe on frozen model) ---
    def is_backend_allowed(self, backend: str) -> bool:
        return backend in self.allowed_backends

    def is_tool_denied(self, tool_name: str) -> bool:
        return tool_name in self.denied_tools

    def is_shell_tool(self, tool_name: str) -> bool:
        return tool_name in ("run_shell_command", "run_sandboxed_shell_command")

    def approval_required_for(self, risk_level: RiskLevel) -> bool:
        if self.require_approval_above is None:
            return False
        return _RISK_RANK[risk_level] >= _RISK_RANK[self.require_approval_above]
