from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common_types import BoundedStr, NonBlankStr, RiskLevel, ToolName


class TaskSchema(BaseModel):
	model_config = ConfigDict(
		strict=True,
		frozen=True,
		extra="forbid",
	)

	task_id: Annotated[
		str,
		Field(
			...,
			min_length=1,
			max_length=64,
			strip_whitespace=True,
			pattern=r"^[A-Za-z0-9_\-]+$",
			description="Unique identifier for the task",
		),
	]

	title: Annotated[
		str,
		Field(
			...,
			min_length=1,
			max_length=200,
			strip_whitespace=True,
			description="Short human-readable task title",
		),
	]

	objective: BoundedStr = Field(
		...,
		description="What the system is trying to accomplish",
	)

	context: Annotated[
		str,
		Field(
			...,
			min_length=1,
			max_length=8000,
			strip_whitespace=True,
			description="Relevant supporting context",
		),
	]

	constraints: list[NonBlankStr] = Field(
		default_factory=list,
		max_length=50,
		description="Task constraints",
	)

	allowed_tools: list[ToolName] = Field(
		default_factory=list,
		max_length=50,
		description="Approved tool classes or tool names",
	)

	expected_output: BoundedStr = Field(
		...,
		description="Expected output artifact or result",
	)

	risk_level: RiskLevel = Field(
		...,
		description="Risk level: low | medium | high",
	)

	@field_validator("constraints", "allowed_tools", mode="after")
	def no_duplicate_entries(cls, v: list[str]) -> list[str]:
		seen: set[str] = set()
		duplicates = [x for x in v if x in seen or seen.add(x)]  # type: ignore[func-returns-value]
		if duplicates:
			raise ValueError(f"Duplicate entries are not allowed: {duplicates}")
		return v