from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Generator, List, Optional
from uuid import uuid4

from runtime.logging import utc_now_iso


_current_tracer: ContextVar[Optional[RunTracer]] = ContextVar(
    "current_tracer", default=None
)

_current_span_id: ContextVar[Optional[str]] = ContextVar(
    "current_span_id", default=None
)


def get_tracer() -> Optional[RunTracer]:
    return _current_tracer.get()


def set_tracer(tracer: RunTracer) -> None:
    _current_tracer.set(tracer)


class RunTracer:
    def __init__(self, run_id: str, started_at: str) -> None:
        self.run_id = run_id
        self.started_at = started_at
        self.spans: List[Dict[str, Any]] = []

    def record_model_call(
        self,
        *,
        agent_role: str,
        started_at: str,
        duration_ms: int,
        requested_backend: str,
        actual_backend: str,
        model_name: str,
        prompt_chars: int,
        response_chars: int,
        fallback_reason: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        span_id = uuid4().hex[:8]
        self.spans.append({
            "span_id": span_id,
            "parent_span_id": _current_span_id.get(),
            "span_type": "model_call",
            "agent_role": agent_role,
            "started_at": started_at,
            "duration_ms": duration_ms,
            "requested_backend": requested_backend,
            "actual_backend": actual_backend,
            "model_name": model_name,
            "prompt_chars": prompt_chars,
            "response_chars": response_chars,
            "fallback_occurred": actual_backend != requested_backend,
            "fallback_reason": fallback_reason,
            "error": error,
        })
        return span_id

    def record_tool_call(
        self,
        *,
        tool_name: str,
        backend: str,
        started_at: str,
        duration_ms: int,
        error: Optional[str] = None,
    ) -> str:
        span_id = uuid4().hex[:8]
        self.spans.append({
            "span_id": span_id,
            "parent_span_id": _current_span_id.get(),
            "span_type": "tool_call",
            "tool_name": tool_name,
            "backend": backend,
            "started_at": started_at,
            "duration_ms": duration_ms,
            "error": error,
        })
        return span_id

    def record_policy_violation(
        self,
        *,
        violation_type: str,
        detail: str,
        context: str,
    ) -> str:
        span_id = uuid4().hex[:8]
        self.spans.append({
            "span_id": span_id,
            "parent_span_id": _current_span_id.get(),
            "span_type": "policy_violation",
            "violation_type": violation_type,
            "detail": detail,
            "context": context,
            "timestamp": utc_now_iso(),
        })
        return span_id

    def record_approval_request(
        self,
        *,
        checkpoint: str,
        reason: str,
        artifact_path: str,
    ) -> str:
        span_id = uuid4().hex[:8]
        self.spans.append({
            "span_id": span_id,
            "parent_span_id": _current_span_id.get(),
            "span_type": "approval_request",
            "checkpoint": checkpoint,
            "reason": reason,
            "artifact_path": artifact_path,
            "timestamp": utc_now_iso(),
        })
        return span_id

    @contextmanager
    def span_context(self, span_id: str) -> Generator[None, None, None]:
        """Set span_id as the ambient parent for all record_* calls within this block."""
        token = _current_span_id.set(span_id)
        try:
            yield
        finally:
            _current_span_id.reset(token)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "spans": self.spans,
        }
