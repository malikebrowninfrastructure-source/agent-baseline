from typing import List
from pydantic import BaseModel, Field

from .common_types import CompletionStatus, ToolName


class ExecutionSchema(BaseModel):
	actions_taken: List[str] = Field(default_factory=list)
	tools_used: List[ToolName] = Field(default_factory=list)
	artifacts_created: List[str] = Field(default_factory=list)
	errors: List[str] = Field(default_factory=list)
	deviations_from_plan: List[str] = Field(default_factory=list)
	completion_status: CompletionStatus