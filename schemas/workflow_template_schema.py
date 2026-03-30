from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common_types import NonBlankStr


class TemplateSectionRequirement(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	section_name: NonBlankStr = Field(..., description="Name of the required section")
	required: bool = Field(default=True, description="Whether this section must be present")
	min_items: Optional[int] = Field(default=None, ge=1, description="Minimum items for list sections")
	description: Optional[NonBlankStr] = Field(default=None, description="What this section should contain")


class TemplateDefaultStep(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	action: NonBlankStr = Field(..., description="Default step action")
	requires_approval: bool = Field(default=False)
	rollback_action: Optional[NonBlankStr] = Field(default=None)


class WorkflowTemplate(BaseModel):
	model_config = ConfigDict(frozen=True, extra="forbid")

	template_id: str = Field(..., pattern=r"^[a-z_]+$", description="Template identifier")
	template_name: NonBlankStr = Field(..., description="Human-readable template name")
	description: NonBlankStr = Field(..., description="What this template is for")

	required_sections: list[TemplateSectionRequirement] = Field(
		...,
		min_length=1,
		description="Sections the workflow output must contain",
	)

	default_steps: list[TemplateDefaultStep] = Field(
		default_factory=list,
		description="Default workflow steps for this template type",
	)

	approval_expectations: dict[str, bool] = Field(
		default_factory=dict,
		description="Map of section_name -> whether approval is expected",
	)

	validation_expectations: dict[str, str] = Field(
		default_factory=dict,
		description="Map of section_name -> validation description",
	)
