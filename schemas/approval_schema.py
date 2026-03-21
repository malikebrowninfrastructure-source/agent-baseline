from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(..., description="Unique identifier for this approval request")
    run_id: str = Field(..., description="Run that requires approval")
    checkpoint: str = Field(..., description="Named checkpoint where approval was requested")
    reason: str = Field(..., description="Human-readable reason approval is required")
    requested_at: str = Field(..., description="UTC ISO timestamp when approval was requested")
    decision: ApprovalDecision = Field(
        default=ApprovalDecision.PENDING,
        description="Operator decision. Set to 'approved' or 'rejected' to resume the run.",
    )
    decided_at: Optional[str] = Field(
        default=None,
        description="UTC ISO timestamp when the operator made their decision",
    )
    operator_note: Optional[str] = Field(
        default=None,
        description="Optional operator note explaining the decision",
    )
    state_snapshot: Dict[str, Any] = Field(
        ...,
        description="Full RunState at the time of the request. Used by resume.py to continue.",
    )
