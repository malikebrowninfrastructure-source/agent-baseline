from __future__ import annotations

from typing import Any, Dict

from langsmith import traceable


@traceable(run_type="chain", name="approval_checkpoint")
def _emit_approval_event(run_id: str, checkpoint: str, reason: str, artifact_path: str) -> dict:
    """Emits a named LangSmith span for an approval checkpoint before the run is paused."""
    return {
        "run_id": run_id,
        "checkpoint": checkpoint,
        "reason": reason,
        "artifact_path": artifact_path,
    }


class ApprovalRequiredError(Exception):
    """
    Raised when a run reaches a checkpoint requiring operator approval.
    This is a clean halt, not a failure. The run can be resumed via resume.py
    after the operator edits approval_request.json and sets decision to
    'approved' or 'rejected'.
    """

    def __init__(self, run_id: str, checkpoint: str, artifact_path: str) -> None:
        self.run_id = run_id
        self.checkpoint = checkpoint
        self.artifact_path = artifact_path
        super().__init__(
            f"[awaiting_approval:{checkpoint}] Run paused. "
            f"Edit '{artifact_path}' then run: python resume.py {artifact_path}"
        )


def request_approval(
    *,
    run_id: str,
    checkpoint: str,
    reason: str,
    state_snapshot: Dict[str, Any],
) -> None:
    """
    Write an approval_request.json artifact and raise ApprovalRequiredError.

    The run halts cleanly. The operator edits the artifact (sets decision to
    'approved' or 'rejected'), then runs resume.py to continue or abort.
    """
    from runtime.logging import utc_now_iso
    from runtime.tracing import get_tracer
    from tools.file_tools import write_json_file
    from schemas.approval_schema import ApprovalRequest, ApprovalDecision

    approval = ApprovalRequest(
        approval_id=f"approval-{run_id}-{checkpoint.replace(':', '-')}",
        run_id=run_id,
        checkpoint=checkpoint,
        reason=reason,
        requested_at=utc_now_iso(),
        decision=ApprovalDecision.PENDING,
        state_snapshot=state_snapshot,
    )

    artifact_path = write_json_file(
        run_id=run_id,
        filename="approval_request.json",
        payload=approval.model_dump(mode="json"),
    )

    tracer = get_tracer()
    if tracer is not None:
        tracer.record_approval_request(
            checkpoint=checkpoint,
            reason=reason,
            artifact_path=artifact_path,
        )

    _emit_approval_event(
        run_id=run_id,
        checkpoint=checkpoint,
        reason=reason,
        artifact_path=artifact_path,
    )

    raise ApprovalRequiredError(run_id=run_id, checkpoint=checkpoint, artifact_path=artifact_path)
