from __future__ import annotations

from pathlib import Path
import json

def ensure_run_dir(run_id: str) -> Path:
    run_dir = Path("outputs") / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
def write_text_file(run_id: str, filename: str, content: str) -> Path:
    run_dir = ensure_run_dir(run_id)
    file_path = run_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)

def write_json_file(run_id: str, filename: str, payload: any) -> Path:
    run_dir = ensure_run_dir(run_id)
    file_path = run_dir / filename
    file_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(file_path)