import time

from runtime.state import RunState
from runtime.logging import utc_now_iso
from runtime.tracing import get_tracer
from schemas.verification_schema import VerificationSchema
from schemas.common_types import Verdict
from models import get_model_adapter, ModelRequest
from routing_policy import route_role, estimate_prompt_size
from execution_policy import enforce_backend_allowed, enforce_cloud_fallback
from config import CLOUD_MODEL, VERIFIER_MODEL


def run_verifier(state: RunState) -> VerificationSchema:
    execution = state.execution

    user_prompt = (
        f"Task title: {state.task.title}\n"
        f"Execution present: {execution is not None}\n"
        f"Execution summary: {execution}"
    )

    decision = route_role(
        role="verifier",
        risk_level=state.task.risk_level.value,
        retry_count=state.retry_count,
        token_estimate=estimate_prompt_size(user_prompt),
        externally_visible=False,
    )

    enforce_backend_allowed("verifier", decision.backend)

    model = get_model_adapter(decision.backend, "verifier")
    model_request = ModelRequest(
        role="verifier",
        system_prompt=(
            "You are the verification component in a schema-driven agent system. "
            "Assess quality, policy boundaries, and next-step guidance."
        ),
        user_prompt=user_prompt,
    )
    actual_backend = decision.backend
    _t0 = time.monotonic()
    _span_started_at = utc_now_iso()
    _fallback_reason = None
    try:
        model_response = model.generate(model_request)
    except RuntimeError as exc:
        enforce_cloud_fallback("verifier", exc)
        print(f"[verifier] local model failed, falling back to cloud. Reason: {exc}")
        _fallback_reason = str(exc)
        actual_backend = "cloud"
        model_response = get_model_adapter("cloud", "verifier").generate(model_request)

    selected_model = VERIFIER_MODEL if actual_backend == "local" else CLOUD_MODEL

    tracer = get_tracer()
    if tracer is not None:
        tracer.record_model_call(
            agent_role="verifier",
            started_at=_span_started_at,
            duration_ms=int((time.monotonic() - _t0) * 1000),
            requested_backend=decision.backend,
            actual_backend=actual_backend,
            model_name=selected_model,
            prompt_chars=len(model_request.system_prompt) + len(model_request.user_prompt),
            response_chars=len(model_response),
            fallback_reason=_fallback_reason,
        )

    if execution is None:
        return VerificationSchema(
            backend=actual_backend,
            model_used=selected_model,
            verdict=Verdict.FAIL,
            issues_found=["Execution output is missing"],
            policy_violations=[],
            quality_assessment=(
                f"Verification failed because execution data was absent. "
                f"Model summary: {model_response[:160]}"
            ),
            recommended_next_step="Retry execution",
        )

    if execution.completion_status.value == "completed":
        return VerificationSchema(
            backend=actual_backend,
            model_used=selected_model,
            verdict=Verdict.PASS,
            issues_found=[],
            policy_violations=[],
            quality_assessment=(
                f"Execution output is complete and reviewable for the baseline workflow. "
                f"Model summary: {model_response[:160]}"
            ),
            recommended_next_step="Proceed to finalization",
        )

    return VerificationSchema(
        backend=decision.backend,
        model_used=selected_model,
        verdict=Verdict.RETRY,
        issues_found=["Execution did not complete successfully"],
        policy_violations=[],
        quality_assessment=(
            f"Execution output is incomplete. "
            f"Model summary: {model_response[:160]}"
        ),
        recommended_next_step="Retry execution or escalate",
    )


class VerifierAgent:
    def run(self, task, plan, execution):
        from types import SimpleNamespace
        state = SimpleNamespace(task=task, plan=plan, execution=execution, retry_count=0)
        return run_verifier(state)