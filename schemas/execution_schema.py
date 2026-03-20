from typing import List
from pydantic import BaseModel, Field

from .common_types import CompletionStatus, ToolName


class ExecutionSchema(BaseModel):
	backend: str = Field(..., description="Model backend used: local or cloud")
	model_used: str = Field(..., description="Model name used for execution")
	actions_taken: List[str] = Field(default_factory=list)
	tools_used: List[ToolName] = Field(default_factory=list)
	artifacts_created: List[str] = Field(default_factory=list)
	errors: List[str] = Field(default_factory=list)
	deviations_from_plan: List[str] = Field(default_factory=list)
	completion_status: CompletionStatus