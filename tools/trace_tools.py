from __future__ import annotations

from typing import TYPE_CHECKING

from tools.file_tools import write_json_file, write_text_file

if TYPE_CHECKING:
    from runtime.tracing import RunTracer


def write_trace_file(run_id: str, tracer: RunTracer) -> str:
    return write_json_file(run_id=run_id, filename="trace.json", payload=tracer.to_dict())


def write_trace_md(run_id: str, tracer: RunTracer) -> str:
    spans = tracer.spans
    model_spans = [s for s in spans if s["span_type"] == "model_call"]
    tool_spans = [s for s in spans if s["span_type"] == "tool_call"]
    violation_spans = [s for s in spans if s["span_type"] == "policy_violation"]
    approval_spans = [s for s in spans if s["span_type"] == "approval_request"]
    fallback_spans = [s for s in model_spans if s.get("fallback_occurred")]
    error_spans = [s for s in spans if s.get("error")]

    lines: list[str] = []

    # Header
    violation_badge = f" | **{len(violation_spans)} POLICY VIOLATION(S)**" if violation_spans else ""
    approval_badge = f" | **{len(approval_spans)} AWAITING APPROVAL**" if approval_spans else ""

    lines += [
        f"# Run Trace: {tracer.run_id}",
        "",
        f"**Started:** {tracer.started_at}",
        f"**Spans:** {len(spans)} total ({len(model_spans)} model calls, {len(tool_spans)} tool calls){violation_badge}{approval_badge}",
        "",
        "---",
        "",
    ]

    # Timeline table
    lines += [
        "## Timeline",
        "",
        "| # | Type | Agent / Tool | Backend | Model | Duration | Fallback? | Error? |",
        "|---|------|--------------|---------|-------|----------|-----------|--------|",
    ]
    for i, span in enumerate(spans, start=1):
        if span["span_type"] == "model_call":
            backend = span["actual_backend"]
            if span["fallback_occurred"]:
                backend = f"{span['requested_backend']} → {span['actual_backend']} (fallback)"
            lines.append(
                f"| {i} | model_call | {span['agent_role']} | {backend} "
                f"| {span['model_name']} | {span['duration_ms']} ms "
                f"| {'YES' if span['fallback_occurred'] else '—'} "
                f"| {'YES' if span['error'] else '—'} |"
            )
        elif span["span_type"] == "tool_call":
            lines.append(
                f"| {i} | tool_call | {span['tool_name']} | {span['backend']} "
                f"| — | {span['duration_ms']} ms | — "
                f"| {'YES' if span['error'] else '—'} |"
            )
        elif span["span_type"] == "policy_violation":
            lines.append(
                f"| {i} | **policy_violation** | {span['violation_type']} | — "
                f"| — | — | — | BLOCKED |"
            )
        else:  # approval_request
            lines.append(
                f"| {i} | **approval_request** | {span['checkpoint']} | — "
                f"| — | — | — | PAUSED |"
            )
    lines += ["", "---", ""]

    # Model calls detail
    if model_spans:
        lines += ["## Model Calls", ""]
        for i, span in enumerate(model_spans, start=1):
            backend_label = span["actual_backend"]
            if span["fallback_occurred"]:
                backend_label = f"{span['requested_backend']} → {span['actual_backend']} (fallback)"
            lines += [
                f"### {i}. {span['agent_role']} ({backend_label})",
                f"- **Model:** {span['model_name']}",
                f"- **Started:** {span['started_at']}",
                f"- **Duration:** {span['duration_ms']} ms",
                f"- **Prompt size:** {span['prompt_chars']} chars | **Response size:** {span['response_chars']} chars",
                f"- **Fallback:** {'YES — ' + (span['fallback_reason'] or '') if span['fallback_occurred'] else 'No'}",
            ]
            if span["error"]:
                lines.append(f"- **Error:** {span['error']}")
            lines.append("")
        lines += ["---", ""]

    # Tool calls detail
    if tool_spans:
        lines += ["## Tool Calls", ""]
        for i, span in enumerate(tool_spans, start=1):
            lines += [
                f"### {i}. {span['tool_name']} ({span['backend']})",
                f"- **Started:** {span['started_at']}",
                f"- **Duration:** {span['duration_ms']} ms",
                f"- **Error:** {span['error'] if span['error'] else 'None'}",
                "",
            ]
        lines += ["---", ""]

    # Policy violations (only if any occurred)
    if violation_spans:
        lines += [
            "## Policy Violations",
            "",
            "| # | Type | Context | Detail |",
            "|---|------|---------|--------|",
        ]
        for i, span in enumerate(violation_spans, start=1):
            detail = span["detail"].replace("|", "\\|")
            lines.append(
                f"| {i} | `{span['violation_type']}` | {span['context']} | {detail} |"
            )
        lines += ["", "---", ""]

    # Approval checkpoints (only if any occurred)
    if approval_spans:
        lines += [
            "## Approval Checkpoints",
            "",
            "| # | Checkpoint | Reason | Artifact |",
            "|---|------------|--------|---------|",
        ]
        for i, span in enumerate(approval_spans, start=1):
            reason = span["reason"].replace("|", "\\|")
            lines.append(
                f"| {i} | `{span['checkpoint']}` | {reason} | `{span['artifact_path']}` |"
            )
        lines += ["", "---", ""]

    # Fallback summary (only if fallbacks occurred)
    if fallback_spans:
        lines += [
            "## Fallback Summary",
            "",
            "| Agent | Requested | Actual | Reason |",
            "|-------|-----------|--------|--------|",
        ]
        for span in fallback_spans:
            reason = (span["fallback_reason"] or "").replace("|", "\\|")
            lines.append(
                f"| {span['agent_role']} | {span['requested_backend']} "
                f"| {span['actual_backend']} | {reason} |"
            )
        lines += ["", "---", ""]

    # Error summary
    lines += ["## Error Summary", ""]
    if error_spans:
        for span in error_spans:
            label = span.get("agent_role") or span.get("tool_name", "unknown")
            lines.append(f"- **{label}:** {span['error']}")
    else:
        lines.append("No errors recorded.")
    lines.append("")

    return write_text_file(run_id=run_id, filename="trace.md", content="\n".join(lines))
