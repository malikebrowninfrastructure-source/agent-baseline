from __future__ import annotations

from models.base import BaseModelAdapter, ModelRequest
from models.router import get_model_for_role
from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema


class PlannerAgent:
    def __init__(self, model: BaseModelAdapter | None = None) -> None:
        self._model = model or get_model_for_role("planner")

    def run(self, task: TaskSchema) -> PlanSchema:
        response = self._model.generate(
            ModelRequest(
                role="planner",
                system_prompt=(
                    "You are the planning component in a schema-driven agent system. "
                    "Return a clear, concise summary of how the task will be executed."
                ),
                user_prompt=(
                    f"Task title: {task.title}\n"
                    f"Objective: {task.objective}\n"
                    f"Context: {task.context}\n"
                    f"Constraints: {list(task.constraints)}\n"
                    f"Allowed tools: {list(task.allowed_tools)}\n"
                    f"Expected output: {task.expected_output}"
                ),
            )
        )

        escalation_needed = len(task.allowed_tools) == 0

        return PlanSchema(
            task_summary=response,
            assumptions=[
                "Task input has been validated against the task contract",
                "Required project context is present in the task description",
                f"Risk level is acceptable for autonomous execution: {task.risk_level.value}",
            ],
            execution_steps=[
                f"Review task objective: {task.objective}",
                f"Prepare output structure for artifact: {task.expected_output}",
                "Execute approved actions using only allowed tool classes",
                "Write output artifact using allowed tools",
            ],
            required_tools=list(task.allowed_tools),
            expected_artifacts=[task.expected_output],
            risks=(
                [
                    "Missing context may reduce output fidelity",
                    "Tool restrictions may limit full task completion",
                    f"Active constraints may block execution steps: {list(task.constraints)}",
                ]
                if task.constraints
                else [
                    "Missing context may reduce output fidelity",
                    "Tool restrictions may limit full task completion",
                ]
            ),
            escalation_needed=escalation_needed,
            escalation_reason=(
                "No allowed tools specified — execution cannot proceed safely"
                if escalation_needed
                else None
            ),
        )
