from __future__ import annotations

from contextvars import ContextVar
from typing import Optional, TYPE_CHECKING

from langsmith import traceable


@traceable(run_type="chain", name="policy_violation")
def _emit_violation_event(violation_type: str, detail: str, context: str) -> dict:
    """Emits a named LangSmith span for a policy violation before the run is halted."""
    return {"violation_type": violation_type, "detail": detail, "context": context}

if TYPE_CHECKING:
    from schemas.policy_schema import RunPolicy
    from schemas.task_schema import TaskSchema


class PolicyViolationError(Exception):
    """
    Raised when any action violates the active RunPolicy.
    The run halts immediately — no silent continuation.
    The violation is recorded to the active RunTracer before this is raised,
    so it appears in trace.json and trace.md even when the run is aborted mid-flight.
    """

    def __init__(self, violation_type: str, detail: str) -> None:
        self.violation_type = violation_type
        self.detail = detail
        super().__init__(f"[policy:{violation_type}] {detail}")


_current_enforcer: ContextVar[Optional["PolicyEnforcer"]] = ContextVar(
    "current_enforcer", default=None
)


def get_enforcer() -> Optional["PolicyEnforcer"]:
    return _current_enforcer.get()


def set_enforcer(enforcer: "PolicyEnforcer") -> None:
    _current_enforcer.set(enforcer)


class PolicyEnforcer:
    """
    Single enforcement point for all policy gates on a run.

    Instantiate once per run from a RunPolicy, then call set_enforcer() to make
    it ambient. All agents and the tool registry call the module-level
    convenience functions below, which resolve to this instance via ContextVar.

    Every check_* method records the violation to the active RunTracer *before*
    raising, so violations always appear in trace.json/trace.md even when the
    run is aborted mid-flight.
    """

    def __init__(self, policy: "RunPolicy") -> None:
        self.policy = policy

    # ------------------------------------------------------------------
    # Approval gate — checked once at run start, before graph.invoke()
    # ------------------------------------------------------------------

    def check_approval(self, task: "TaskSchema") -> None:
        """Block execution if task risk requires approval that hasn't been granted."""
        if self.policy.approval_required_for(task.risk_level) and not self.policy.approved:
            self._violate(
                "approval_required",
                f"Task '{task.task_id}' risk level '{task.risk_level.value}' meets or exceeds "
                f"approval threshold '{self.policy.require_approval_above.value}'. "
                "Set policy.approved=True to proceed.",
                context="run:approval_gate",
            )

    # ------------------------------------------------------------------
    # Model governance — checked in each agent after routing decision
    # ------------------------------------------------------------------

    def check_backend(self, agent_role: str, backend: str) -> None:
        """Block routing to a backend not in policy.allowed_backends."""
        if not self.policy.is_backend_allowed(backend):
            self._violate(
                "backend_not_allowed",
                f"Agent '{agent_role}' routed to backend '{backend}', "
                f"which is not in allowed_backends {self.policy.allowed_backends}.",
                context=f"{agent_role}:model_routing",
            )

    def check_cloud_fallback(self, agent_role: str, local_error: Exception) -> None:
        """Block cloud fallback when policy.allow_cloud_fallback is False."""
        if not self.policy.allow_cloud_fallback:
            self._violate(
                "cloud_fallback_denied",
                f"Agent '{agent_role}' local model failed but cloud fallback is disabled. "
                f"Local error: {local_error}",
                context=f"{agent_role}:cloud_fallback",
            )

    # ------------------------------------------------------------------
    # Tool governance — checked in registry.execute_tool()
    # ------------------------------------------------------------------

    def check_tool(self, tool_name: str) -> None:
        """Block any tool on the policy deny list."""
        if self.policy.is_tool_denied(tool_name):
            self._violate(
                "tool_denied",
                f"Tool '{tool_name}' is explicitly denied by the active run policy.",
                context=f"tool:{tool_name}",
            )

    def check_shell(self, tool_name: str) -> None:
        """Block shell execution unless policy.allow_shell_execution is True."""
        if not self.policy.allow_shell_execution:
            self._violate(
                "shell_not_approved",
                f"Shell tool '{tool_name}' requires policy.allow_shell_execution=True. "
                "Shell execution is off by default.",
                context=f"tool:{tool_name}",
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _violate(self, violation_type: str, detail: str, context: str) -> None:
        from runtime.tracing import get_tracer
        tracer = get_tracer()
        if tracer is not None:
            tracer.record_policy_violation(
                violation_type=violation_type,
                detail=detail,
                context=context,
            )
        _emit_violation_event(violation_type=violation_type, detail=detail, context=context)
        raise PolicyViolationError(violation_type, detail)


# ---------------------------------------------------------------------------
# Module-level convenience functions.
# Resolve the ambient enforcer from ContextVar; all are no-ops when none is set.
# ---------------------------------------------------------------------------


def enforce_approval(task: "TaskSchema") -> None:
    e = get_enforcer()
    if e is not None:
        e.check_approval(task)


def enforce_backend_allowed(agent_role: str, backend: str) -> None:
    e = get_enforcer()
    if e is not None:
        e.check_backend(agent_role, backend)


def enforce_cloud_fallback(agent_role: str, local_error: Exception) -> None:
    e = get_enforcer()
    if e is not None:
        e.check_cloud_fallback(agent_role, local_error)


def enforce_tool_policy(tool_name: str) -> None:
    e = get_enforcer()
    if e is not None:
        e.check_tool(tool_name)


def enforce_shell(tool_name: str) -> None:
    e = get_enforcer()
    if e is not None:
        e.check_shell(tool_name)
