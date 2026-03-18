from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema
from schemas.execution_schema import ExecutionSchema
from schemas.verification_schema import VerificationSchema
from schemas.common_types import FinalStatus, WorkflowStage


class RunState(BaseModel):

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
    )

    run_id: str = Field(
        min_length=1,
        max_length=64,
        strip_whitespace=True,
        pattern=r"^[A-Za-z0-9_\-]+$",
        description="Unique identifier for the workflow run",
    )

    current_stage: WorkflowStage = Field(
        description="Current workflow stage",
    )

    task: TaskSchema = Field(
        description="Input task contract",
    )

    plan: Optional[PlanSchema] = Field(
        default=None,
        description="Planner output",
    )

    execution: Optional[ExecutionSchema] = Field(
        default=None,
        description="Executor output",
    )

    verification: Optional[VerificationSchema] = Field(
        default=None,
        description="Verifier output",
    )

    final_status: Optional[FinalStatus] = Field(
        default=None,
        description="Final run outcome",
    )

    # ------------------------------------------------------------------
    # Model validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def enforce_stage_ordering(self) -> RunState:
        """
        Execution requires a plan. Verification requires execution.
        final_status is only valid in a terminal stage.
        These are cross-field invariants that cannot be expressed
        with field validators alone.
        """
        if self.execution is not None and self.plan is None:
            raise ValueError(
                "execution cannot be set without a plan — "
                "RunState stage ordering violated"
            )
        if self.verification is not None and self.execution is None:
            raise ValueError(
                "verification cannot be set without execution — "
                "RunState stage ordering violated"
            )

        terminal_stages = {
            WorkflowStage.COMPLETE,
            WorkflowStage.ESCALATED,
            WorkflowStage.FAILED,
        }
        if self.final_status is not None and self.current_stage not in terminal_stages:
            raise ValueError(
                f"final_status may only be set in a terminal stage "
                f"({[s.value for s in terminal_stages]}), "
                f"got: {self.current_stage.value!r}"
            )
        if self.final_status is None and self.current_stage in terminal_stages:
            raise ValueError(
                f"final_status is required when current_stage is terminal "
                f"({self.current_stage.value!r})"
            )
        return self
