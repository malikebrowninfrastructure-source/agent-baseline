from dotenv import load_dotenv
load_dotenv(override=True)
from uuid import uuid4
from datetime import datetime, timezone
from tools import write_json_file
from tools.trace_tools import write_trace_file, write_trace_md

from workflows import build_graph
from runtime import RunState
from runtime.tracing import RunTracer, set_tracer
from schemas.task_schema import TaskSchema
from schemas.policy_schema import RunPolicy
from schemas.common_types import RiskLevel, WorkflowStage
from enforce_policy import PolicyEnforcer, PolicyViolationError, set_enforcer, enforce_approval
from runtime.approval import ApprovalRequiredError


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

	policy = RunPolicy(
		allowed_backends=["local", "cloud"],
		denied_tools=[],
		allow_cloud_fallback=True,
		allow_shell_execution=False,
		require_approval_above=RiskLevel.HIGH,
		approved=False,
	)

	initial_state = RunState(
		run_id=f"run-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M')}-{uuid4().hex[:8]}",
		current_stage=WorkflowStage.INTAKE,
		task=task,
		policy=policy,
	)

	enforcer = PolicyEnforcer(policy)
	set_enforcer(enforcer)
	enforce_approval(task=initial_state.task)

	tracer = RunTracer(run_id=initial_state.run_id, started_at=initial_state.started_at)
	set_tracer(tracer)

	graph = build_graph()
	try:
		result = graph.invoke(initial_state)
	except ApprovalRequiredError as exc:
		print(f"\n[AWAITING APPROVAL] Run paused at checkpoint '{exc.checkpoint}'")
		print(f"  Artifact : {exc.artifact_path}")
		print(f"  Next step: edit 'decision' to 'approved' or 'rejected', then run:")
		print(f"             python resume.py {exc.artifact_path}")
		write_trace_file(run_id=initial_state.run_id, tracer=tracer)
		write_trace_md(run_id=initial_state.run_id, tracer=tracer)
		return
	except PolicyViolationError as exc:
		print(f"\n[POLICY VIOLATION] Run halted: {exc}")
		write_trace_file(run_id=initial_state.run_id, tracer=tracer)
		write_trace_md(run_id=initial_state.run_id, tracer=tracer)
		raise

	json_result = RunState.model_validate(result).to_jsonable()
	output_path = write_json_file(
		run_id=initial_state.run_id,
		filename="result.json",
		payload=json_result
	)
	trace_json_path = write_trace_file(run_id=initial_state.run_id, tracer=tracer)
	trace_md_path = write_trace_md(run_id=initial_state.run_id, tracer=tracer)

	for path in json_result.get("execution", {}).get("artifacts_created", []):
		print(f"wrote artifact to {path}")
	print(f"saved run result to {output_path}")
	print(f"saved trace json to {trace_json_path}")
	print(f"saved trace markdown to {trace_md_path}")

if __name__ == "__main__":
	main()