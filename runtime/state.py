from __future__ import annotations

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from runtime.logging import utc_now_iso
from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema
from schemas.execution_schema import ExecutionSchema
from schemas.verification_schema import VerificationSchema
from schemas.policy_schema import RunPolicy
from schemas.common_types import WorkflowStage, FinalStatus


class RunState(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(..., description="Unique identifier for the workflow run")
    current_stage: WorkflowStage = Field(..., description="Current workflow stage")
    task: TaskSchema = Field(..., description="Input task contract")
    policy: Optional[RunPolicy] = Field(default=None, description="Execution policy governing this run")

    plan: Optional[PlanSchema] = Field(default=None, description="Planner output")
    execution: Optional[ExecutionSchema] = Field(default=None, description="Executor output")
    verification: Optional[VerificationSchema] = Field(default=None, description="Verifier output")

    final_status: Optional[FinalStatus] = Field(default=None, description="Final run outcome")
    final_summary: Optional[str] = Field(default=None, description="Human-readable run summary")

    started_at: str = Field(default_factory=utc_now_iso, description="Run start timestamp (UTC ISO)")
    finished_at: Optional[str] = Field(default=None, description="Run finish timestamp (UTC ISO)")

    retry_count: int = Field(default=0, ge=0, description="Number of retries performed")
    max_retries: int = Field(default=3, description="Maximum allowed retries before escalation")
    escalated: bool = Field(default=False, description="Whether the run was escalated")

    events: List[Dict[str, Any]] = Field(default_factory=list, description="Structured event log")

    def to_jsonable(self) -> dict:
        return self.model_dump(mode="json")
