from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import StringConstraints


NonBlankStr = Annotated[
str,
StringConstraints(strip_whitespace=True, min_length=1),
]

BoundedStr = Annotated[
str,
StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]

ToolName = Annotated[
str,
StringConstraints(
strip_whitespace=True,
min_length=1,
max_length=128,
pattern=r"^[A-Za-z0-9_\-\.]+$",
),
]


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CompletionStatus(str, Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    RETRY = "retry"
    ESCALATE = "escalate"


class WorkflowStage(str, Enum):
    INTAKE = "intake"
    PLANNING = "planning"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    FINALIZATION = "finalization"
    COMPLETE = "complete"
    ESCALATED = "escalated"
    FAILED = "failed"


class FinalStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"
    PARTIAL = "partial"
