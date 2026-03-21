from dotenv import load_dotenv
load_dotenv(override=True)
import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python resume.py <path-to-approval_request.json>")
        sys.exit(1)

    artifact_path = Path(sys.argv[1])
    if not artifact_path.exists():
        print(f"[ERROR] Artifact not found: {artifact_path}")
        sys.exit(1)

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    decision = artifact.get("decision", "pending")
    run_id = artifact["run_id"]
    checkpoint = artifact["checkpoint"]

    if decision == "pending":
        print(f"[RESUME] Decision is still 'pending' for checkpoint '{checkpoint}'.")
        print(f"  Edit '{artifact_path}': set 'decision' to 'approved' or 'rejected'.")
        sys.exit(1)

    if decision == "rejected":
        note = artifact.get("operator_note") or "No note provided."
        print(f"[RESUME] Run '{run_id}' rejected at checkpoint '{checkpoint}'.")
        print(f"  Operator note: {note}")
        sys.exit(1)

    if decision != "approved":
        print(f"[RESUME] Unknown decision value '{decision}'. Expected 'approved' or 'rejected'.")
        sys.exit(1)

    # --- Approved: restore state and re-invoke graph ---
    from runtime.state import RunState
    from schemas.policy_schema import RunPolicy
    from enforce_policy import PolicyEnforcer, PolicyViolationError, set_enforcer
    from runtime.tracing import RunTracer, set_tracer
    from runtime.approval import ApprovalRequiredError
    from tools.trace_tools import write_trace_file, write_trace_md
    from tools import write_json_file
    from workflows import build_graph

    state_data = artifact["state_snapshot"]
    # Patch the policy to approved=True before reconstructing state
    if state_data.get("policy"):
        state_data["policy"]["approved"] = True

    resumed_state = RunState.model_validate(state_data)

    policy = resumed_state.policy
    if policy is None:
        policy = RunPolicy(approved=True)

    enforcer = PolicyEnforcer(policy)
    set_enforcer(enforcer)

    tracer = RunTracer(run_id=run_id, started_at=resumed_state.started_at)
    set_tracer(tracer)

    graph = build_graph()
    try:
        result = graph.invoke(resumed_state)
    except ApprovalRequiredError as exc:
        print(f"\n[AWAITING APPROVAL] Run paused again at checkpoint '{exc.checkpoint}'")
        print(f"  Artifact : {exc.artifact_path}")
        print(f"  Next step: python resume.py {exc.artifact_path}")
        write_trace_file(run_id=run_id, tracer=tracer)
        write_trace_md(run_id=run_id, tracer=tracer)
        return
    except PolicyViolationError as exc:
        print(f"\n[POLICY VIOLATION] Run halted: {exc}")
        write_trace_file(run_id=run_id, tracer=tracer)
        write_trace_md(run_id=run_id, tracer=tracer)
        raise

    json_result = RunState.model_validate(result).to_jsonable()
    output_path = write_json_file(
        run_id=run_id,
        filename="result.json",
        payload=json_result,
    )
    trace_json_path = write_trace_file(run_id=run_id, tracer=tracer)
    trace_md_path = write_trace_md(run_id=run_id, tracer=tracer)

    for path in json_result.get("execution", {}).get("artifacts_created", []):
        print(f"wrote artifact to {path}")
    print(f"saved run result to {output_path}")
    print(f"saved trace json to {trace_json_path}")
    print(f"saved trace markdown to {trace_md_path}")


if __name__ == "__main__":
    main()
