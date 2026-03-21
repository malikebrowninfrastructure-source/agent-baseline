from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS_DIR = Path("outputs/runs")


@app.get("/runs")
def list_runs():
    if not RUNS_DIR.exists():
        return {"runs": []}
    runs = []
    for run_dir in RUNS_DIR.iterdir():
        if run_dir.is_dir():
            summary = "No summary available"
            result_file = run_dir / "result.json"
            if result_file.exists():
                data = json.loads(result_file.read_text(encoding="utf-8"))
                summary = data.get("final_summary") or "No summary available"
            runs.append({"run_id": run_dir.name, "summary": summary})
    return {"runs": runs}


@app.get("/runs/{run_id}")
def get_run_details(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    result: dict = {}

    result_file = run_dir / "result.json"
    if result_file.exists():
        result = json.loads(result_file.read_text(encoding="utf-8"))

    trace_file = run_dir / "trace.json"
    if trace_file.exists():
        result["trace"] = json.loads(trace_file.read_text(encoding="utf-8"))

    return result


@app.get("/runs/{run_id}/summary")
def get_run_summary(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    trace_file = run_dir / "trace.json"
    spans = []
    if trace_file.exists():
        data = json.loads(trace_file.read_text(encoding="utf-8"))
        spans = data.get("spans", [])

    return {
        "run_id": run_id,
        "total_spans": len(spans),
        "model_calls": len([s for s in spans if s.get("span_type") == "model_call"]),
        "tool_calls": len([s for s in spans if s.get("span_type") == "tool_call"]),
        "policy_violations": len([s for s in spans if s.get("span_type") == "policy_violation"]),
        "fallbacks": len([s for s in spans if s.get("fallback_occurred") is True]),
        "errors": [s for s in spans if s.get("error")],
    }


@app.get("/runs/{run_id}/spans")
def get_run_spans(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    trace_file = run_dir / "trace.json"
    if not trace_file.exists():
        return {"run_id": run_id, "spans": []}

    data = json.loads(trace_file.read_text(encoding="utf-8"))
    return {"run_id": run_id, "spans": data.get("spans", [])}


@app.get("/runs/{run_id}/artifacts")
def get_run_artifacts(run_id: str):
    run_dir = RUNS_DIR / run_id

    if not run_dir.exists():
        return {"error": "run not found"}

    files = [item.name for item in run_dir.iterdir() if item.is_file()]
    return {"run_id": run_id, "artifacts": sorted(files)}