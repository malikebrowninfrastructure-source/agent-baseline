from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event(stage: str, message: str) -> dict:
    return {
        "timestamp": utc_now_iso(),
        "stage": stage,
        "message": message,
    }
