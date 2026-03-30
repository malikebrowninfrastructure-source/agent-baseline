from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common_types import BoundedStr, NonBlankStr, RiskLevel, WorkflowCategory


class ClassificationSection(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	category: WorkflowCategory = Field(..., description="Workflow category")
	severity: RiskLevel = Field(..., description="Severity / risk level")
	impact_scope: NonBlankStr = Field(..., description="e.g. single_host, network_segment, site_wide")
	change_type: Optional[NonBlankStr] = Field(default=None, description="e.g. standard, emergency, normal")


class NavigationSection(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	affected_systems: list[NonBlankStr] = Field(..., min_length=1, description="Systems involved")
	affected_services: list[NonBlankStr] = Field(default_factory=list, description="Services involved")
	entry_point: NonBlankStr = Field(..., description="Where to start the workflow")


class DependencyEntry(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	name: NonBlankStr = Field(..., description="Dependency name")
	type: NonBlankStr = Field(..., description="service, config, credential, network")
	status: NonBlankStr = Field(..., description="verified, assumed, unknown")


class WorkflowStep(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	step_number: int = Field(..., ge=1)
	action: NonBlankStr = Field(..., description="What to do")
	expected_outcome: NonBlankStr = Field(..., description="What success looks like")
	requires_approval: bool = Field(default=False)
	rollback_action: Optional[BoundedStr] = Field(default=None)


class ValidationStep(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	check: NonBlankStr = Field(..., description="What to verify")
	expected_result: NonBlankStr = Field(..., description="Expected outcome of the check")
	is_blocking: bool = Field(default=True)


class RollbackStep(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	step_number: int = Field(..., ge=1)
	action: NonBlankStr = Field(..., description="Rollback action")
	verification: NonBlankStr = Field(..., description="How to verify rollback succeeded")


class PlaybookEntry(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	playbook_id: NonBlankStr = Field(..., description="Unique playbook identifier")
	title: NonBlankStr = Field(..., description="Playbook title")
	last_updated: NonBlankStr = Field(..., description="Last update timestamp")
	linked_tasks: list[NonBlankStr] = Field(default_factory=list, description="Related task IDs")


class WorkflowOutput(BaseModel):
	"""Complete workflow package produced by every successful run.
	All 9 sections are required — missing or empty sections cause validation failure."""

	model_config = ConfigDict(frozen=True, extra="forbid")

	classification: ClassificationSection
	navigation: NavigationSection
	dependencies: list[DependencyEntry] = Field(..., min_length=1)
	workflow_steps: list[WorkflowStep] = Field(..., min_length=1)
	risks: list[NonBlankStr] = Field(..., min_length=1)
	validation_steps: list[ValidationStep] = Field(..., min_length=1)
	rollback_steps: list[RollbackStep] = Field(..., min_length=1)
	documentation: list[NonBlankStr] = Field(..., min_length=1)
	playbook_entry: PlaybookEntry
	known_facts: list[NonBlankStr] = Field(
		default_factory=list,
		description="Facts sourced from task input or retrieved lab context",
	)
	unknown_facts: list[NonBlankStr] = Field(
		default_factory=list,
		description="Facts that must be discovered before execution can proceed",
	)

	@model_validator(mode="after")
	def rollback_covers_workflow(self) -> WorkflowOutput:
		steps_with_rollback = [s for s in self.workflow_steps if s.rollback_action]
		if steps_with_rollback and not self.rollback_steps:
			raise ValueError("Workflow steps define rollback actions but no rollback_steps provided")
		return self
