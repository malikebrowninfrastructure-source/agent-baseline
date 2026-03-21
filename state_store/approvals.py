"""
state_store/approvals.py

Approval row CRUD helpers.

Task metadata (title, risk, objective) is stored directly on the approvals
row (denormalized) so list_pending_approvals() can return everything the
UI needs in a single query without a JOIN.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .db import get_conn


def create_approval(
    *,
    approval_id: str,
    run_id: str,
    checkpoint: str,
    reason: str,
    requested_at: str,
    task_title: Optional[str] = None,
    task_risk: Optional[str] = None,
    task_objective: Optional[str] = None,
) -> None:
    """Insert a pending approval row.

    Called from runtime/approval.py immediately after approval_request.json
    is written to disk.  INSERT OR IGNORE so calling twice is safe.
    """
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO approvals
                (approval_id, run_id, checkpoint, reason, requested_at,
                 task_title, task_risk, task_objective)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id, run_id, checkpoint, reason, requested_at,
                task_title, task_risk, task_objective,
            ),
        )


def resolve_approval(
    *,
    run_id: str,
    decision: str,
    decided_at: str,
    operator_note: Optional[str] = None,
) -> None:
    """Write operator decision back to the approval row.

    Called from api.py POST /approvals/{run_id}/decide after the JSON
    artifact has already been updated.
    """
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE approvals
            SET decision = ?, decided_at = ?, operator_note = ?
            WHERE run_id = ? AND decision = 'pending'
            """,
            (decision, decided_at, operator_note, run_id),
        )


def list_pending_approvals() -> List[Dict[str, Any]]:
    """Return all pending approval rows ordered by request time, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM approvals
            WHERE decision = 'pending'
            ORDER BY requested_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_approval(run_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recent approval row for a run, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM approvals WHERE run_id = ? ORDER BY requested_at DESC LIMIT 1",
            (run_id,),
        ).fetchone()
    return dict(row) if row else None
