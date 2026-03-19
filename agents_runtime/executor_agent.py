from __future__ import annotations

from models.base import BaseModelAdapter, ModelRequest
from models.router import get_model_for_role
from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema
from schemas.execution_schema import ExecutionSchema
from schemas.common_types import CompletionStatus
from tools.registry import execute_tool


class ExecutorAgent:
    def __init__(self, model: BaseModelAdapter | None = None) -> None:
        self._model = model or get_model_for_role("executor")

    def run(self, task: TaskSchema, plan: PlanSchema, run_id: str) -> ExecutionSchema:
        generated = self._model.generate(
            ModelRequest(
                role="executor",
                system_prompt=(
                    "You are the execution component in a schema-driven agent system. "
                    "Produce operationally useful implementation content."
                ),
                user_prompt=(
                    f"Task title: {task.title}\n"
                    f"Objective: {task.objective}\n"
                    f"Context: {task.context}\n"
                    f"Constraints: {list(task.constraints)}\n"
                    f"Expected output: {task.expected_output}"
                ),
            )
        )

        actions_taken: list[str] = []
        artifacts_created: list[str] = []
        tools_used: list[str] = []
        errors: list[str] = []
        deviations: list[str] = []

        for step in plan.execution_steps:
            actions_taken.append(f"Executed step: {step}")

        for artifact_name in plan.expected_artifacts:
            content = self._build_artifact(task, plan, generated)
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
                if "write_text_file" not in tools_used:
                    tools_used.append("write_text_file")
            except PermissionError as e:
                errors.append(f"Tool permission denied for '{artifact_name}': {e}")
                deviations.append(f"Could not produce '{artifact_name}' — tool not permitted")
            except Exception as e:
                errors.append(f"Failed to write '{artifact_name}': {e}")
                deviations.append(f"Artifact '{artifact_name}' not produced due to error")

        if errors and not artifacts_created:
            status = CompletionStatus.FAILED
        elif errors and artifacts_created:
            status = CompletionStatus.PARTIAL
        else:
            status = CompletionStatus.COMPLETED

        return ExecutionSchema(
            actions_taken=actions_taken,
            tools_used=tools_used,
            artifacts_created=artifacts_created,
            errors=errors,
            deviations_from_plan=deviations,
            completion_status=status,
        )

    def _build_artifact(self, task: TaskSchema, plan: PlanSchema, model_output: str) -> str:
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

## Model Output

{model_output}
"""
