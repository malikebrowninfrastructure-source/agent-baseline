import json
from tools import write_json_file
from enum import Enum
from pydantic import BaseModel

from workflows import build_graph
from runtime import RunState
from schemas.task_schema import TaskSchema
from schemas.common_types import RiskLevel, WorkflowStage


def to_jsonable(obj):
	if isinstance(obj, BaseModel):
		return obj.model_dump()
	if isinstance(obj, Enum):
		return obj.value
	if isinstance(obj, dict):
		return {k: to_jsonable(v) for k, v in obj.items()}
	if isinstance(obj, list):
		return [to_jsonable(v) for v in obj]
	return obj


def main():
	task = TaskSchema(
		task_id="task-001",
		title="Generate baseline engineering artifact",
		objective="Run the first LangGraph-based baseline workflow",
		context="This is a controlled v1 workflow test for the agent baseline system",
		constraints=[
			"Stay inside baseline workflow scope",
			"Use structured outputs only",
		],
		allowed_tools=["file_tools", "validation_tools"],
		expected_output="baseline_report.md",
		risk_level=RiskLevel.LOW,
	)

	initial_state = RunState(
		run_id="run-001",
		current_stage=WorkflowStage.INTAKE,
		task=task,
	)

	graph = build_graph()
	result = graph.invoke(initial_state)
	
	json_result = to_jsonable(result)
	output_path = write_json_file(
		run_id=initial_state.run_id,
		filename="result.json",
		payload=json_result
	)

	print("=== FINAL RESULT ===")
	print(json.dumps(to_jsonable(result), indent=2))
	print(f"\nSaved run result to: {output_path}")

if __name__ == "__main__":
	main()