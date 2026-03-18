from typing import List
from pydantic import BaseModel, Field

from .common_types import BoundedStr, Verdict

class VerificationSchema(BaseModel):
    verdict: Verdict
    issues_found: List[BoundedStr] = Field(default_factory=list)
    policy_violations: List[BoundedStr] = Field(default_factory=list)
    quality_assessment: BoundedStr
    recommended_next_step: BoundedStr