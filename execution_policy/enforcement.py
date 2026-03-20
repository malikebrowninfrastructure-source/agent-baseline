from __future__ import annotations

from contextvars import ContextVar
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from schemas.policy_schema import RunPolicy
    from schemas.task_schema import TaskSchema


class PolicyViolationError(Exception):
    """Raised when an action violates the active RunPolicy. Run halts immediately."""

    def __init__(self, violation_type: str, detail: str) -> None:
        self.violation_type = violation_type
        self.detail = detail
        super().__init__(f"[policy:{violation_type}] {detail}")


_current_policy: ContextVar[Optional["RunPolicy"]] = ContextVar(
    "current_policy", default=None
)


def get_policy() -> Optional["RunPolicy"]:
    return _current_policy.get()


def set_policy(policy: "RunPolicy") -> None:
    _current_policy.set(policy)


# ---------------------------------------------------------------------------
# Enforcement functions — each raises PolicyViolationError on violation.
# All are no-ops when policy is None (no policy set = no enforcement).
# ---------------------------------------------------------------------------


def enforce_tool_policy(tool_name: str, policy: Optional["RunPolicy"] = None) -> None:
    """Fail if tool_name appears on the policy deny list."""
    if policy is None:
        policy = get_policy()
    if policy is None:
        return
    if policy.is_tool_denied(tool_name):
        raise PolicyViolationError(
            "tool_denied",
            f"Tool '{tool_name}' is explicitly denied by the active run policy.",
        )


def enforce_backend_allowed(
    agent_role: str,
    backend: str,
    policy: Optional["RunPolicy"] = None,
) -> None:
    """Fail if the routing decision picked a backend not in policy.allowed_backends."""
    if policy is None:
        policy = get_policy()
    if policy is None:
        return
    if not policy.is_backend_allowed(backend):
        raise PolicyViolationError(
            "backend_not_allowed",
            f"Agent '{agent_role}' routed to backend '{backend}', "
            f"which is not in allowed_backends {policy.allowed_backends}.",
        )


def enforce_cloud_fallback(
    agent_role: str,
    local_error: Exception,
    policy: Optional["RunPolicy"] = None,
) -> None:
    """Fail if cloud fallback is disabled and the local model just failed."""
    if policy is None:
        policy = get_policy()
    if policy is None:
        return
    if not policy.allow_cloud_fallback:
        raise PolicyViolationError(
            "cloud_fallback_denied",
            f"Agent '{agent_role}' local model failed but cloud fallback is disabled "
            f"by policy. Local error: {local_error}",
        )


def enforce_approval(
    task: "TaskSchema",
    policy: Optional["RunPolicy"] = None,
) -> None:
    """Fail early if the task risk level requires approval and it hasn't been granted."""
    if policy is None:
        policy = get_policy()
    if policy is None:
        return
    if policy.approval_required_for(task.risk_level) and not policy.approved:
        raise PolicyViolationError(
            "approval_required",
            f"Task '{task.task_id}' has risk level '{task.risk_level.value}' which meets "
            f"or exceeds the approval threshold '{policy.require_approval_above.value}'. "
            "Set policy.approved=True to proceed.",
        )
