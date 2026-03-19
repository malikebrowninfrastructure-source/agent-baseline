from __future__ import annotations

from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema
from schemas.execution_schema import ExecutionSchema
from schemas.verification_schema import VerificationSchema
from schemas.common_types import CompletionStatus, Verdict


class VerifierAgent:
    """
    Reviews task, plan, and execution outputs.
    Issues an explicit verdict. Never passes incomplete or policy-violating work silently.
    """

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

        if execution.completion_status == CompletionStatus.PARTIAL:
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

        # Policy check: tools_used must be subset of task.allowed_tools
        allowed = set(task.allowed_tools)
        for tool in execution.tools_used:
            if tool not in allowed:
                policy_violations.append(
                    f"Tool '{tool}' was used but is not in task.allowed_tools"
                )

        # Policy check: artifacts_created must be non-empty if plan expected them
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
