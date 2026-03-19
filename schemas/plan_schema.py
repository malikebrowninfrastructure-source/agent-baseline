from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .common_types import BoundedStr, NonBlankStr, ToolName


class PlanSchema(BaseModel):
    task_summary: BoundedStr = Field(
        ...,
        description="Planner summary of the task",
    )
    assumptions: list[NonBlankStr] = Field(
        default_factory=list,
        max_length=50,
        description="Explicit assumptions made during planning",
    )
    execution_steps: list[BoundedStr] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Ordered execution steps — at least one required",
    )
    required_tools: list[ToolName] = Field(
        default_factory=list,
        max_length=50,
        description="Tools needed for execution",
    )
    expected_artifacts: list[NonBlankStr] = Field(
        default_factory=list,
        max_length=50,
        description="Artifacts expected from execution",
    )
    risks: list[NonBlankStr] = Field(
        default_factory=list,
        max_length=50,
        description="Meaningful risks and failure concerns",
    )
    escalation_needed: bool = Field(
        ...,
        description="Whether escalation is required before proceeding",
    )
    escalation_reason: Optional[BoundedStr] = Field(
        default=None,
        description="Required explanation when escalation_needed is True",
    )

    @field_validator(
        "assumptions", "execution_steps", "required_tools",
        "expected_artifacts", "risks",
        mode="after",
    )
    def no_duplicate_entries(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        duplicates = [x for x in v if x in seen or seen.add(x)]  # type: ignore[func-returns-value]
        if duplicates:
            raise ValueError(f"Duplicate entries are not allowed: {duplicates}")
        return v

    @model_validator(mode="after")
    def escalation_reason_required_when_escalating(self) -> PlanSchema:
        if self.escalation_needed and not self.escalation_reason:
            raise ValueError(
                "escalation_reason is required when escalation_needed is True"
            )
        if not self.escalation_needed and self.escalation_reason is not None:
            raise ValueError(
                "escalation_reason must be None when escalation_needed is False"
            )
        return self
