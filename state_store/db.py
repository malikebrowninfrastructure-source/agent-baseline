"""
state_store/db.py

SQLite connection factory and schema bootstrap.

The database lives at outputs/agent.db alongside the per-run artifact
directories.  WAL journal mode makes it safe for concurrent access from
the API server (reader) and CLI processes (writers) without locking.

Usage:
    from state_store.db import bootstrap, get_conn

    bootstrap()          # once at startup — idempotent
    conn = get_conn()    # new connection each call; caller closes it
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "state.db"

_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,
    task_id           TEXT,
    task_title        TEXT,
    task_risk         TEXT,
    current_stage     TEXT NOT NULL,
    final_status      TEXT,
    final_summary     TEXT,
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    retry_count       INTEGER NOT NULL DEFAULT 0,
    escalated         INTEGER NOT NULL DEFAULT 0,
    total_spans       INTEGER NOT NULL DEFAULT 0,
    model_calls       INTEGER NOT NULL DEFAULT 0,
    tool_calls        INTEGER NOT NULL DEFAULT 0,
    fallbacks         INTEGER NOT NULL DEFAULT 0,
    policy_violations INTEGER NOT NULL DEFAULT 0,
    errors            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id    TEXT PRIMARY KEY,
    run_id         TEXT NOT NULL REFERENCES runs(run_id),
    checkpoint     TEXT NOT NULL,
    reason         TEXT,
    requested_at   TEXT NOT NULL,
    decision       TEXT NOT NULL DEFAULT 'pending',
    decided_at     TEXT,
    operator_note  TEXT,
    task_title     TEXT,
    task_risk      TEXT,
    task_objective TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode and Row factory enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every process startup."""
    with get_conn() as conn:
        conn.executescript(_DDL)
