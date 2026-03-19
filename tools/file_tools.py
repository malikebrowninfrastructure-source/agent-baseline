from __future__ import annotations

import json
from pathlib import Path


def ensure_run_dir(run_id: str) -> Path:
    run_dir = Path("outputs") / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_text_file(run_id: str, filename: str, content: str) -> str:
    run_dir = ensure_run_dir(run_id)
    file_path = run_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


def write_json_file(run_id: str, filename: str, payload: dict) -> str:
    run_dir = ensure_run_dir(run_id)
    file_path = run_dir / filename
    file_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(file_path)


def write_run_summary(run_id: str, summary: str) -> str:
    run_dir = ensure_run_dir(run_id)
    file_path = run_dir / "run_summary.md"
    file_path.write_text(summary, encoding="utf-8")
    return str(file_path)
