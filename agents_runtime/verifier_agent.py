from __future__ import annotations

from models.base import BaseModelAdapter, ModelRequest
from models.router import get_model_for_role
from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema
from schemas.execution_schema import ExecutionSchema
from schemas.verification_schema import VerificationSchema
from schemas.common_types import CompletionStatus, Verdict
from tools.registry import TOOL_CLASS_MAP


# Reverse map: concrete tool name → tool class name
# e.g. "write_text_file" → "file_tools"
_TOOL_TO_CLASS: dict[str, str] = {
    tool: class_name
    for class_name, tools in TOOL_CLASS_MAP.items()
    for tool in tools
}


class VerifierAgent:
    def __init__(self, model: BaseModelAdapter | None = None) -> None:
        self._model = model or get_model_for_role("verifier")

    def run(
        self,
        task: TaskSchema,
        plan: PlanSchema,
        execution: ExecutionSchema,
    ) -> VerificationSchema:
        issues: list[str] = []
        policy_violations: list[str] = []

        # Check completion status
        if execution.completion_status == CompletionStatus.FAILED:
            issues.append("Execution failed — no artifacts were produced")
        elif execution.completion_status == CompletionStatus.PARTIAL:
            issues.append("Execution partially completed — some artifacts may be missing")

        # Check all expected artifacts were produced
        for expected in plan.expected_artifacts:
            produced = any(expected in path for path in execution.artifacts_created)
            if not produced:
                issues.append(f"Expected artifact not produced: '{expected}'")

        # Check for recorded errors
        for error in execution.errors:
            issues.append(f"Execution error recorded: {error}")

        # Check for plan deviations
        for deviation in execution.deviations_from_plan:
            issues.append(f"Deviation from plan: {deviation}")

        # Policy check: resolve concrete tool names → class, then check against allowed_tool_classes
        allowed_classes = set(task.allowed_tools)
        for tool in execution.tools_used:
            tool_class = _TOOL_TO_CLASS.get(tool)
            if tool_class is None:
                policy_violations.append(
                    f"Tool '{tool}' is not registered in any tool class"
                )
            elif tool_class not in allowed_classes:
                policy_violations.append(
                    f"Tool '{tool}' belongs to class '{tool_class}' "
                    f"which is not in task.allowed_tools"
                )

        # Policy check: plan expected artifacts but none were created
        if plan.expected_artifacts and not execution.artifacts_created:
            policy_violations.append(
                "Plan declared expected artifacts but none were created"
            )

        # Determine verdict
        if policy_violations:
            verdict = Verdict.FAIL
            quality = "Execution produced policy violations and cannot be approved."
            next_step = "Review policy violations and retry with compliant tool usage"
        elif issues and execution.completion_status == CompletionStatus.FAILED:
            verdict = Verdict.RETRY
            quality = "Execution failed. No usable output was produced."
            next_step = "Retry execution — investigate errors before re-running"
        elif issues:
            verdict = Verdict.RETRY
            quality = "Execution completed with deficiencies. Output is incomplete or deviated from plan."
            next_step = "Retry execution or escalate if root cause is unclear"
        else:
            verdict = Verdict.PASS
            quality = (
                "Execution output is complete, artifact was produced, "
                "no errors or policy violations recorded."
            )
            next_step = "Proceed to finalization"

        return VerificationSchema(
            verdict=verdict,
            issues_found=issues,
            policy_violations=policy_violations,
            quality_assessment=quality,
            recommended_next_step=next_step,
        )
