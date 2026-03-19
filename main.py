from uuid import uuid4
from tools import write_json_file

from workflows import build_graph
from runtime import RunState
from schemas.task_schema import TaskSchema
from schemas.common_types import RiskLevel, WorkflowStage


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
		run_id=f"run-{uuid4().hex[:8]}",
		current_stage=WorkflowStage.INTAKE,
		task=task,
	)

	graph = build_graph()
	result = graph.invoke(initial_state)
	
	json_result = RunState.model_validate(result).to_jsonable()
	output_path = write_json_file(
		run_id=initial_state.run_id,
		filename="result.json",
		payload=json_result
	)

	for path in json_result.get("execution", {}).get("artifacts_created", []):
		print(f"wrote artifact to {path}")
	print(f"saved run result to {output_path}")

if __name__ == "__main__":
	main()