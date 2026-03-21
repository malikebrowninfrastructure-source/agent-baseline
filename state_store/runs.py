"""
state_store/runs.py

Run row CRUD helpers.

Each function opens and closes its own connection so callers don't need to
manage connection lifetimes.  All writes use INSERT OR IGNORE / UPDATE so they
are safe to call more than once for the same run_id.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .db import get_conn


def create_run(
    *,
    run_id: str,
    task_id: Optional[str],
    task_title: Optional[str],
    task_risk: Optional[str],
    current_stage: str,
    started_at: str,
) -> None:
    """Insert a new run row, or leave an existing row untouched.

    Called once at the very start of main.py / resume.py so the run appears
    in the dashboard immediately even before any spans are recorded.
    """
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO runs
                (run_id, task_id, task_title, task_risk, current_stage, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, task_id, task_title, task_risk, current_stage, started_at),
        )


def update_run_stage(run_id: str, stage: str) -> None:
    """Update current_stage for a run.

    Called from runtime/realtime.py write_live_status() on every stage
    transition so the dashboard reflects the live workflow position.
    """
    with get_conn() as conn:
        conn.execute(
            "UPDATE runs SET current_stage = ? WHERE run_id = ?",
            (stage, run_id),
        )


def update_run(
    *,
    run_id: str,
    final_status: str,
    final_summary: Optional[str],
    finished_at: Optional[str],
    retry_count: int = 0,
    escalated: bool = False,
    total_spans: int = 0,
    model_calls: int = 0,
    tool_calls: int = 0,
    fallbacks: int = 0,
    policy_violations: int = 0,
    errors: int = 0,
) -> None:
    """Write terminal run state and span counters.

    Called from main.py and resume.py after graph.invoke() returns (success
    or policy violation).  Span counts are computed from tracer.spans by the
    caller so no file I/O is needed here.
    """
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE runs SET
                current_stage     = ?,
                final_status      = ?,
                final_summary     = ?,
                finished_at       = ?,
                retry_count       = ?,
                escalated         = ?,
                total_spans       = ?,
                model_calls       = ?,
                tool_calls        = ?,
                fallbacks         = ?,
                policy_violations = ?,
                errors            = ?
            WHERE run_id = ?
            """,
            (
                final_status,      # mirror final_status into current_stage for display
                final_status,
                final_summary,
                finished_at,
                retry_count,
                int(escalated),
                total_spans,
                model_calls,
                tool_calls,
                fallbacks,
                policy_violations,
                errors,
                run_id,
            ),
        )


def get_run_db(run_id: str) -> Optional[Dict[str, Any]]:
    """Return a single run row as a plain dict, or None if not found."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    return dict(row) if row else None


def list_runs_db(limit: int = 200) -> List[Dict[str, Any]]:
    """Return all run rows ordered newest-first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
