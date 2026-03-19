from __future__ import annotations

from schemas.task_schema import TaskSchema
from schemas.plan_schema import PlanSchema


class PlannerAgent:
    """
    Converts a validated TaskSchema into a structured PlanSchema.
    Does not execute, mutate files, or claim work is done.
    """

    def run(self, task: TaskSchema) -> PlanSchema:
        escalation_needed = len(task.allowed_tools) == 0

        return PlanSchema(
            task_summary=f"Execute task '{task.title}': {task.objective}",
            assumptions=[
                "Task input has been validated against the task contract",
                "Required project context is present in the task description",
                f"Risk level is acceptable for autonomous execution: {task.risk_level.value}",
            ],
            execution_steps=[
                f"Review task objective: {task.objective}",
                f"Prepare output structure for artifact: {task.expected_output}",
                "Execute approved actions using only allowed tool classes",
                f"Write output artifact using allowed tools",
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
