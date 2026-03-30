import asyncio
import json
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import state_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    state_store.init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "outputs" / "runs"


async def _run_resume(artifact_path: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "resume.py", artifact_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    await proc.communicate()  # wait for completion; output goes to server logs


def _load_spans(run_dir: Path) -> list:
    ndjson = run_dir / "spans.ndjson"
    if ndjson.exists():
        raw = ndjson.read_text(encoding="utf-8")
        return [json.loads(l) for l in raw.splitlines() if l.strip()]
    trace = run_dir / "trace.json"
    if trace.exists():
        return json.loads(trace.read_text(encoding="utf-8")).get("spans", [])
    return []


@app.get("/runs/stream")
async def stream_runs():
    async def event_generator():
        known: dict = {}  # run_id → {stage, final_status}
        heartbeat_tick = 0
        while True:
            heartbeat_tick += 1
            if heartbeat_tick % 30 == 0:
                yield ": keepalive\n\n"

            if not RUNS_DIR.exists():
                await asyncio.sleep(1.0)
                continue

            for run_dir in sorted(RUNS_DIR.iterdir()):
                if not run_dir.is_dir():
                    continue
                run_id = run_dir.name

                if run_id not in known:
                    st_file = run_dir / "live_status.json"
                    stage, started_at = "intake", None
                    if st_file.exists():
                        try:
                            st = json.loads(st_file.read_text(encoding="utf-8"))
                            stage = st.get("current_stage", "intake")
                            started_at = st.get("started_at")
                        except (OSError, json.JSONDecodeError):
                            pass
                    bo = 0
                    ndjson_file = run_dir / "spans.ndjson"
                    if ndjson_file.exists():
                        try:
                            bo = ndjson_file.stat().st_size
                        except OSError:
                            pass
                    known[run_id] = {"stage": stage, "final_status": None, "byte_offset": bo}
                    payload = {"run_id": run_id, "current_stage": stage, "started_at": started_at}
                    yield f"event: run_created\ndata: {json.dumps(payload)}\n\n"
                    continue

                prev = known[run_id]
                if prev["final_status"]:
                    continue

                result_file = run_dir / "result.json"
                if result_file.exists():
                    try:
                        r = json.loads(result_file.read_text(encoding="utf-8"))
                        if r.get("final_status"):
                            spans = _load_spans(run_dir)
                            payload = {
                                "run_id":        run_id,
                                "final_status":  r.get("final_status"),
                                "final_summary": r.get("final_summary"),
                                "finished_at":   r.get("finished_at"),
                                "total_spans":   len(spans),
                                "model_calls":   len([s for s in spans if s.get("span_type") == "model_call"]),
                                "tool_calls":    len([s for s in spans if s.get("span_type") == "tool_call"]),
                                "fallbacks":     len([s for s in spans if s.get("fallback_occurred")]),
                            }
                            known[run_id]["final_status"] = r["final_status"]
                            yield f"event: run_completed\ndata: {json.dumps(payload)}\n\n"
                            continue
                    except (OSError, json.JSONDecodeError):
                        pass

                st_file = run_dir / "live_status.json"
                if st_file.exists():
                    try:
                        st = json.loads(st_file.read_text(encoding="utf-8"))
                        new_stage = st.get("current_stage")
                        if new_stage and new_stage != prev["stage"]:
                            known[run_id]["stage"] = new_stage
                            payload = {"run_id": run_id, "current_stage": new_stage,
                                       "updated_at": st.get("updated_at")}
                            yield f"event: run_stage_changed\ndata: {json.dumps(payload)}\n\n"
                    except (OSError, json.JSONDecodeError):
                        pass

                ndjson_file = run_dir / "spans.ndjson"
                if ndjson_file.exists():
                    try:
                        size = ndjson_file.stat().st_size
                        bo = prev["byte_offset"]
                        if size > bo:
                            with ndjson_file.open("rb") as fh:
                                fh.seek(bo)
                                chunk = fh.read(size - bo).decode("utf-8", errors="replace")
                            known[run_id]["byte_offset"] = size
                            for line in chunk.splitlines():
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    span = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                payload = {
                                    "run_id":            run_id,
                                    "span_type":         span.get("span_type"),
                                    "fallback_occurred": span.get("fallback_occurred", False),
                                }
                                yield f"event: run_span\ndata: {json.dumps(payload)}\n\n"
                    except OSError:
                        pass

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/approvals")
def list_approvals():
    return {"approvals": state_store.list_pending_approvals()}


@app.post("/approvals/{run_id}/decide")
async def decide_approval(run_id: str, background_tasks: BackgroundTasks, body: dict = Body(...)):
    decision = body.get("decision")
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    artifact = RUNS_DIR / run_id / "approval_request.json"
    if not artifact.exists():
        raise HTTPException(status_code=404, detail="Approval request not found")

    try:
        data = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500, detail=str(e))

    if data.get("decision") != "pending":
        raise HTTPException(status_code=409, detail=f"Already decided: {data['decision']}")

    data["decision"]      = decision
    data["operator_note"] = body.get("operator_note") or None
    data["decided_at"]    = datetime.now(timezone.utc).isoformat()
    artifact.write_text(json.dumps(data, indent=2), encoding="utf-8")

    state_store.resolve_approval(
        run_id=run_id,
        decision=decision,
        decided_at=data["decided_at"],
        operator_note=data["operator_note"],
    )

    if decision == "approved":
        background_tasks.add_task(_run_resume, str(artifact))
    else:  # rejected — terminal state, update DB now
        state_store.update_run(
            run_id=run_id,
            final_status="failed",
            final_summary=f"Rejected by operator. Note: {data['operator_note'] or 'none'}",
            finished_at=data["decided_at"],
            retry_count=0,
            escalated=False,
            total_spans=0,
            model_calls=0,
            tool_calls=0,
            fallbacks=0,
            policy_violations=0,
            errors=0,
        )

    return {"status": "ok", "decision": decision}


@app.get("/runs")
def list_runs():
    return {"runs": state_store.list_runs_db()}


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
    row = state_store.get_run_db(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


@app.get("/runs/{run_id}/spans")
def get_run_spans(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    ndjson_file = run_dir / "spans.ndjson"
    if ndjson_file.exists():
        raw = ndjson_file.read_text(encoding="utf-8")
        spans = [json.loads(l) for l in raw.splitlines() if l.strip()]
        return {"run_id": run_id, "spans": spans, "byte_offset": len(raw.encode("utf-8"))}

    spans = _load_spans(run_dir)
    return {"run_id": run_id, "spans": spans, "byte_offset": 0}


@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, since: int = 0):
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        ndjson_file    = run_dir / "spans.ndjson"
        status_file    = run_dir / "live_status.json"
        result_file    = run_dir / "result.json"
        byte_offset    = since
        last_stage     = None
        heartbeat_tick = 0

        while True:
            heartbeat_tick += 1
            if heartbeat_tick % 30 == 0:
                yield ": keepalive\n\n"

            # Stage updates
            if status_file.exists():
                try:
                    st = json.loads(status_file.read_text(encoding="utf-8"))
                    if st.get("current_stage") != last_stage:
                        last_stage = st.get("current_stage")
                        yield f"event: stage\ndata: {json.dumps(st)}\n\n"
                except (OSError, json.JSONDecodeError):
                    pass

            # New spans (byte-seek into NDJSON)
            if ndjson_file.exists():
                try:
                    size = ndjson_file.stat().st_size
                    if size > byte_offset:
                        with ndjson_file.open("rb") as fh:
                            fh.seek(byte_offset)
                            chunk = fh.read(size - byte_offset).decode("utf-8", errors="replace")
                        byte_offset = size
                        for line in chunk.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                span = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            evt = "approval_request" if span.get("span_type") == "approval_request" else "span"
                            yield f"event: {evt}\ndata: {json.dumps(span)}\n\n"
                except OSError:
                    pass

            # Completion check
            if result_file.exists():
                try:
                    r = json.loads(result_file.read_text(encoding="utf-8"))
                    if r.get("final_status"):
                        done = {
                            "final_status":  r.get("final_status"),
                            "final_summary": r.get("final_summary"),
                            "finished_at":   r.get("finished_at"),
                        }
                        yield f"event: done\ndata: {json.dumps(done)}\n\n"
                        return
                except (OSError, json.JSONDecodeError):
                    pass

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/runs/{run_id}/artifacts")
def get_run_artifacts(run_id: str):
    run_dir = RUNS_DIR / run_id

    if not run_dir.exists():
        return {"error": "run not found"}

    files = [item.name for item in run_dir.iterdir() if item.is_file()]
    return {"run_id": run_id, "artifacts": sorted(files)}


@app.get("/runs/{run_id}/workflow")
def get_run_workflow(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")
    wf_file = run_dir / "workflow_output.json"
    if not wf_file.exists():
        raise HTTPException(status_code=404, detail="workflow_output.json not found for this run")
    return json.loads(wf_file.read_text(encoding="utf-8"))