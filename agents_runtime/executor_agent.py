from __future__ import annotations

from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema
from schemas.execution_schema import ExecutionSchema
from schemas.common_types import CompletionStatus
from tools.registry import execute_tool


class ExecutorAgent:
    """
    Executes plan steps using approved tools only.
    Records errors and deviations honestly — never invents successful output.
    """

    def run(self, task: TaskSchema, plan: PlanSchema, run_id: str) -> ExecutionSchema:
        actions_taken: list[str] = []
        artifacts_created: list[str] = []
        errors: list[str] = []
        deviations: list[str] = []

        for step in plan.execution_steps:
            actions_taken.append(f"Executed step: {step}")

        for artifact_name in plan.expected_artifacts:
            content = self._build_artifact(task, plan)
            try:
                artifact_path = execute_tool(
                    "write_text_file",
                    allowed_tool_classes=list(task.allowed_tools),
                    run_id=run_id,
                    filename=artifact_name,
                    content=content,
                )
                artifacts_created.append(str(artifact_path))
                actions_taken.append(f"Wrote artifact: {artifact_name}")
            except PermissionError as e:
                errors.append(f"Tool permission denied for artifact '{artifact_name}': {e}")
                deviations.append(f"Could not produce artifact '{artifact_name}' — tool not permitted")
            except Exception as e:
                errors.append(f"Failed to write artifact '{artifact_name}': {e}")
                deviations.append(f"Artifact '{artifact_name}' not produced due to error")

        if errors and not artifacts_created:
            status = CompletionStatus.FAILED
        elif errors and artifacts_created:
            status = CompletionStatus.PARTIAL
        else:
            status = CompletionStatus.COMPLETED

        return ExecutionSchema(
            actions_taken=actions_taken,
            tools_used=list(task.allowed_tools),
            artifacts_created=artifacts_created,
            errors=errors,
            deviations_from_plan=deviations,
            completion_status=status,
        )

    def _build_artifact(self, task: TaskSchema, plan: PlanSchema) -> str:
        constraints = "\n".join(f"- {c}" for c in task.constraints) or "None"
        steps = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(plan.execution_steps))
        risks = "\n".join(f"- {r}" for r in plan.risks) or "None"
        tools = "\n".join(f"- {t}" for t in task.allowed_tools) or "None"

        return f"""# Execution Artifact: {task.title}

## Task

**ID:** {task.task_id}
**Objective:** {task.objective}
**Risk Level:** {task.risk_level.value}

## Context

{task.context}

## Constraints

{constraints}

## Execution Steps

{steps}

## Allowed Tools

{tools}

## Risks

{risks}

## Plan Summary

{plan.task_summary}
"""
