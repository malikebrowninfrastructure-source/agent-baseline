"""
runtime/realtime.py

File-based bridge between the CLI process and the SSE API for live streaming.

Two files are written inside each run's output directory:
  spans.ndjson      — one span per line, appended as each span is recorded
  live_status.json  — current workflow stage, overwritten at each transition

These files are polled by the SSE endpoint in api.py and forwarded to the
browser without requiring the CLI process and API server to share memory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.logging import utc_now_iso

RUNS_DIR = Path("outputs") / "runs"


def init_run_stream(run_id: str, started_at: str, current_stage: str = "intake") -> None:
    """Create/truncate spans.ndjson and write the initial live_status.json.

    Called once at RunTracer construction (run start). Subsequent stage
    transitions call write_live_status() directly.
    """
    nd = RUNS_DIR / run_id / "spans.ndjson"
    nd.parent.mkdir(parents=True, exist_ok=True)
    nd.write_text("")  # truncate / create
    write_live_status(run_id=run_id, stage=current_stage, started_at=started_at)


def emit_span(run_id: str, span: Dict[str, Any]) -> None:
    """Append a span as a single JSON line to spans.ndjson.

    Called by RunTracer after every record_* call so the SSE endpoint
    can deliver spans to the browser in real time.
    """
    try:
        with (RUNS_DIR / run_id / "spans.ndjson").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(span, default=str) + "\n")
    except OSError:
        pass


def write_live_status(run_id: str, stage: str, started_at: Optional[str] = None) -> None:
    """Overwrite live_status.json with the current workflow stage.

    Called at the start of each workflow node so the SSE endpoint can emit
    stage-transition events to the browser before any spans are recorded.
    """
    p = RUNS_DIR / run_id / "live_status.json"
    try:
        existing = json.loads(p.read_text()) if p.exists() else {}
        p.write_text(json.dumps({
            "run_id": run_id,
            "current_stage": stage,
            "started_at": started_at or existing.get("started_at", utc_now_iso()),
            "updated_at": utc_now_iso(),
        }))
    except OSError:
        pass
