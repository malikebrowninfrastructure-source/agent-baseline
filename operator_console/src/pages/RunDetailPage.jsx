import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api";
import Timeline from "./Timeline";
import ModelCallsTab from "./ModelCallsTab";
import ToolCallsTab from "./ToolCallsTab";
import PolicyTab from "./PolicyTab";

const TABS = ["Summary", "Timeline", "Model Calls", "Tool Calls", "Policy & Fallbacks"];

const tdStyle = { padding: "8px 12px", borderBottom: "1px solid #eee", fontSize: "13px" };

const SEV_STYLE = {
  high:   { background: "#fce4ec", color: "#c62828", border: "1px solid #c6282844" },
  medium: { background: "#fff3e0", color: "#e65100", border: "1px solid #e6510044" },
  low:    { background: "#e8f5e9", color: "#2e7d32", border: "1px solid #2e7d3244" },
};

export default function RunDetailPage() {
  const { runId } = useParams();
  const [run, setRun]         = useState(null);
  const [summary, setSummary] = useState(null);
  const [spans, setSpans]     = useState([]);
  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [activeTab, setActiveTab] = useState("Summary");
  const [connStatus, setConnStatus] = useState(null); // null | "connecting" | "connected" | "reconnecting"
  const [runLoaded, setRunLoaded]   = useState(false);
  const [byteOffset, setByteOffset] = useState(0);
  const wasConnected = useRef(false);

  const fetchRunDetail = useCallback(() => {
    Promise.all([
      api.get(`/runs/${runId}`),
      api.get(`/runs/${runId}/summary`),
      api.get(`/runs/${runId}/spans`),
    ])
      .then(([runRes, summaryRes, spansRes]) => {
        setRun(runRes.data);
        setSummary(summaryRes.data);
        setSpans(spansRes.data.spans || []);
        setByteOffset(spansRes.data.byte_offset ?? 0);
        setRunLoaded(true);
      })
      .catch((err) => setError(err.message));
  }, [runId]);

  // Initial load
  useEffect(() => {
    Promise.all([
      api.get(`/runs/${runId}`),
      api.get(`/runs/${runId}/summary`),
      api.get(`/runs/${runId}/spans`),
      api.get(`/runs/${runId}/workflow`).catch(() => null),
    ])
      .then(([runRes, summaryRes, spansRes, wfRes]) => {
        setRun(runRes.data);
        setSummary(summaryRes.data);
        setSpans(spansRes.data.spans || []);
        setByteOffset(spansRes.data.byte_offset ?? 0);
        setWorkflow(wfRes?.data ?? null);
        setRunLoaded(true);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [runId]);

  useEffect(() => {
    if (!runLoaded || run?.final_status) return;

    const es = new EventSource(
      `http://127.0.0.1:8000/runs/${runId}/stream?since=${byteOffset}`
    );
    setConnStatus("connecting");

    es.onopen = () => {
      if (wasConnected.current) {
        fetchRunDetail();
      }
      wasConnected.current = true;
      setConnStatus("connected");
    };

    es.addEventListener("span", (e) => {
      const span = JSON.parse(e.data);
      setConnStatus("connected");
      setSpans(prev => prev.some(s => s.span_id === span.span_id) ? prev : [...prev, span]);
      setSummary(prev => !prev ? prev : {
        ...prev,
        total_spans:       (prev.total_spans ?? 0) + 1,
        model_calls:       span.span_type === "model_call"       ? (prev.model_calls ?? 0) + 1       : prev.model_calls,
        tool_calls:        span.span_type === "tool_call"        ? (prev.tool_calls ?? 0) + 1        : prev.tool_calls,
        policy_violations: span.span_type === "policy_violation" ? (prev.policy_violations ?? 0) + 1 : prev.policy_violations,
        fallbacks:         span.fallback_occurred                ? (prev.fallbacks ?? 0) + 1         : prev.fallbacks,
      });
    });

    es.addEventListener("approval_request", (e) => {
      const span = JSON.parse(e.data);
      setConnStatus("connected");
      setSpans(prev => prev.some(s => s.span_id === span.span_id) ? prev : [...prev, span]);
    });

    es.addEventListener("stage", (e) => {
      const st = JSON.parse(e.data);
      setConnStatus("connected");
      setRun(prev => prev ? { ...prev, current_stage: st.current_stage } : prev);
    });

    es.addEventListener("done", (e) => {
      const r = JSON.parse(e.data);
      setRun(prev => prev ? { ...prev, ...r } : prev);
      setConnStatus(null);
      es.close();
    });

    es.onerror = () => setConnStatus(wasConnected.current ? "reconnecting" : "connecting");

    return () => { es.close(); setConnStatus(null); wasConnected.current = false; };
  }, [runId, runLoaded, byteOffset, fetchRunDetail]);

  if (loading) return <div style={{ padding: "24px" }}>Loading...</div>;
  if (error)   return <div style={{ padding: "24px", color: "red" }}>Error: {error}</div>;

  const modelCalls       = spans.filter(s => s.span_type === "model_call");
  const toolCalls        = spans.filter(s => s.span_type === "tool_call");
  const fallbacks        = spans.filter(s => s.fallback_occurred === true);
  const policyViolations = spans.filter(s => s.span_type === "policy_violation");
  const approvalRequests = spans.filter(s => s.span_type === "approval_request");

  const statusColor = {
    success: "#2e7d32",
    failed:  "#c62828",
    error:   "#c62828",
  }[run?.final_status] ?? "#555";

  return (
    <div style={{ padding: "24px", fontFamily: "monospace" }}>
      <style>{`
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
        .live-dot { animation: blink 1.4s ease-in-out infinite; }
      `}</style>
      <Link to="/" style={{ fontSize: "13px", color: "#555" }}>← Back to Runs</Link>

      <div style={{ display: "flex", alignItems: "baseline", gap: "12px", margin: "12px 0 4px" }}>
        <h1 style={{ margin: 0, fontSize: "20px" }}>{runId}</h1>
        {run?.final_status ? (
          <span style={{
            padding: "2px 10px",
            borderRadius: "12px",
            fontSize: "12px",
            fontWeight: "bold",
            background: statusColor + "22",
            color: statusColor,
            border: `1px solid ${statusColor}44`,
          }}>
            {run.final_status}
          </span>
        ) : connStatus ? (
          <span style={{
            padding: "2px 10px",
            borderRadius: "12px",
            fontSize: "12px",
            fontWeight: "bold",
            background: connStatus === "connected" ? "#e8f5e9" : connStatus === "reconnecting" ? "#fce4ec" : "#fff8e1",
            color:      connStatus === "connected" ? "#2e7d32" : connStatus === "reconnecting" ? "#c62828" : "#f57f17",
            border:     `1px solid ${connStatus === "connected" ? "#2e7d3244" : connStatus === "reconnecting" ? "#c6282844" : "#f57f1744"}`,
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
          }}>
            <span className="live-dot">●</span>
            {connStatus === "connected" ? "connected" : connStatus === "reconnecting" ? "reconnecting…" : "connecting…"}
          </span>
        ) : null}
      </div>

      {/* Stale data banner */}
      {connStatus === "reconnecting" && (
        <div style={{
          margin: "12px 0", padding: "8px 14px", background: "#fff3e0",
          border: "1px solid #ffe0b2", borderRadius: "6px",
          fontSize: "13px", color: "#e65100",
        }}>
          Connection lost — data may be stale. Reconnecting…
        </div>
      )}

      {/* Drift warning banner */}
      {fallbacks.length > 0 && (
        <div style={{
          margin: "12px 0",
          padding: "10px 14px",
          background: "#fff8f0",
          border: "1px solid #ffcc8088",
          borderRadius: "6px",
          fontSize: "13px",
          color: "#e65100",
        }}>
          Backend drift detected — {fallbacks.length} agent{fallbacks.length > 1 ? "s" : ""} fell back from requested backend. See <strong>Policy & Fallbacks</strong> tab.
        </div>
      )}

      {/* Run summary card */}
      {(run || workflow) && (() => {
        const status    = run?.final_status ?? "—";
        const stepCount = workflow?.workflow_steps?.length ?? "—";
        const deps      = workflow?.dependencies ?? [];
        const verified  = deps.filter(d => d.status === "verified").length;
        const assumed   = deps.filter(d => d.status === "assumed").length;
        const hasDeps   = deps.length > 0;
        const isFailed  = status === "failed" || status === "error";
        const errText   = isFailed ? (run?.final_summary ?? null) : null;

        const STATUS_COLOR = {
          success: { bg: "#e8f5e9", color: "#2e7d32", border: "#2e7d3244" },
          failed:  { bg: "#fce4ec", color: "#c62828", border: "#c6282844" },
          error:   { bg: "#fce4ec", color: "#c62828", border: "#c6282844" },
          running: { bg: "#e3f2fd", color: "#1565c0", border: "#1565c044" },
        };
        const sc = STATUS_COLOR[status] ?? { bg: "#f5f5f5", color: "#555", border: "#55555544" };

        return (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", margin: "16px 0", alignItems: "flex-start" }}>
            <div style={{ padding: "6px 14px", borderRadius: "20px", fontSize: "13px", fontWeight: 600,
                          background: sc.bg, color: sc.color, border: `1px solid ${sc.border}` }}>
              {status}
            </div>
            {workflow && (
              <div style={{ padding: "6px 14px", borderRadius: "20px", fontSize: "13px",
                            background: "#f3f4f6", color: "#374151", border: "1px solid #d1d5db" }}>
                {stepCount} step{stepCount !== 1 ? "s" : ""}
              </div>
            )}
            {hasDeps && (
              <div style={{ padding: "6px 14px", borderRadius: "20px", fontSize: "13px",
                            background: "#f3f4f6", color: "#374151", border: "1px solid #d1d5db" }}>
                {verified} verified · {assumed} assumed
              </div>
            )}
            {errText && (
              <div style={{ padding: "6px 14px", borderRadius: "20px", fontSize: "13px",
                            background: "#fce4ec", color: "#c62828", border: "1px solid #c6282844",
                            maxWidth: "480px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                ⚠ {errText}
              </div>
            )}
          </div>
        );
      })()}

      {/* Tab bar */}
      <div style={{ display: "flex", gap: "6px", margin: "20px 0 24px", flexWrap: "wrap" }}>
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "7px 14px",
              background: activeTab === tab ? "#1a1a1a" : "#eee",
              color:      activeTab === tab ? "#fff"     : "#333",
              border: "none",
              cursor: "pointer",
              borderRadius: "4px",
              fontSize: "13px",
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Summary */}
      {activeTab === "Summary" && (
        <div>
          <table style={{ borderCollapse: "collapse", width: "500px" }}>
            <tbody>
              {[
                ["Status",            run?.final_status],
                ["Stage",             run?.current_stage],
                ["Started",           run?.started_at],
                ["Finished",          run?.finished_at],
                ["Total Spans",       summary?.total_spans],
                ["Model Calls",       summary?.model_calls],
                ["Tool Calls",        summary?.tool_calls],
                ["Policy Violations", summary?.policy_violations],
                ["Fallbacks",         summary?.fallbacks],
              ].map(([label, value]) => (
                <tr key={label}>
                  <td style={{ ...tdStyle, fontWeight: "bold", width: "180px" }}>{label}</td>
                  <td style={tdStyle}>{value ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {run?.final_summary && (
            <p style={{ marginTop: "16px", padding: "12px", background: "#f5f5f5", borderRadius: "4px", maxWidth: "700px", fontSize: "13px" }}>
              {run.final_summary}
            </p>
          )}

          {workflow && (
            <div style={{ marginTop: "24px", maxWidth: "700px", fontSize: "13px", fontFamily: "monospace" }}>
              {/* Section header */}
              <div style={{ color: "#888", marginBottom: "12px" }}>─── Workflow Plan ──────────────────────────────</div>

              {/* Header fields */}
              <table style={{ borderCollapse: "collapse", width: "100%", marginBottom: "20px" }}>
                <tbody>
                  {[
                    ["Title",     workflow.playbook_entry?.title],
                    ["Objective", workflow.navigation?.entry_point],
                  ].map(([label, value]) => value ? (
                    <tr key={label}>
                      <td style={{ ...tdStyle, fontWeight: "bold", width: "180px" }}>{label}</td>
                      <td style={tdStyle}>{value}</td>
                    </tr>
                  ) : null)}
                  {workflow.classification?.category && (
                    <tr>
                      <td style={{ ...tdStyle, fontWeight: "bold", width: "180px" }}>Execution Mode</td>
                      <td style={tdStyle}>
                        <span style={{ padding: "2px 8px", borderRadius: "10px", background: "#e3f2fd", color: "#1565c0", border: "1px solid #1565c044", fontSize: "12px" }}>
                          {workflow.classification.category}
                        </span>
                      </td>
                    </tr>
                  )}
                  {workflow.classification?.severity && (
                    <tr>
                      <td style={{ ...tdStyle, fontWeight: "bold", width: "180px" }}>Severity</td>
                      <td style={tdStyle}>
                        <span style={{ padding: "2px 8px", borderRadius: "10px", fontSize: "12px", ...(SEV_STYLE[workflow.classification.severity] ?? SEV_STYLE.low) }}>
                          {workflow.classification.severity}
                        </span>
                      </td>
                    </tr>
                  )}
                  {workflow.classification?.impact_scope && (
                    <tr>
                      <td style={{ ...tdStyle, fontWeight: "bold", width: "180px" }}>Scope</td>
                      <td style={tdStyle}>{workflow.classification.impact_scope}</td>
                    </tr>
                  )}
                </tbody>
              </table>

              {/* Known Facts */}
              {workflow.known_facts?.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ color: "#888", marginBottom: "6px" }}>─── Known Facts ────────────────────────────────</div>
                  {workflow.known_facts.map((fact, i) => (
                    <div key={i} style={{ paddingLeft: "4px", marginBottom: "4px" }}>• {fact}</div>
                  ))}
                </div>
              )}

              {/* Unknown Facts */}
              {workflow.unknown_facts?.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ color: "#888", marginBottom: "6px" }}>─── Unknown Facts ──────────────────────────────</div>
                  {workflow.unknown_facts.map((fact, i) => (
                    <div key={i} style={{ paddingLeft: "4px", marginBottom: "4px" }}>• {fact}</div>
                  ))}
                </div>
              )}

              {/* Validation Checks */}
              {workflow.validation_steps?.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ color: "#888", marginBottom: "6px" }}>─── Validation Checks ──────────────────────────</div>
                  {workflow.validation_steps.map((vs, i) => (
                    <div key={i} style={{ paddingLeft: "4px", marginBottom: "4px" }}>• {vs.check}</div>
                  ))}
                </div>
              )}

              {/* Workflow Steps (capped at 5) */}
              {workflow.workflow_steps?.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ color: "#888", marginBottom: "6px" }}>─── Workflow Steps ─────────────────────────────</div>
                  {workflow.workflow_steps.slice(0, 5).map((step, i) => (
                    <div key={i} style={{ marginBottom: "10px", paddingLeft: "4px" }}>
                      <div>{step.step_number ?? i + 1}. {step.action}</div>
                      {step.expected_outcome && (
                        <div style={{ paddingLeft: "16px", color: "#555" }}>→ {step.expected_outcome}</div>
                      )}
                    </div>
                  ))}
                  {workflow.workflow_steps.length > 5 && (
                    <div style={{ paddingLeft: "4px", color: "#888", fontStyle: "italic" }}>
                      …and {workflow.workflow_steps.length - 5} more
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === "Timeline"          && <Timeline spans={spans} />}
      {activeTab === "Model Calls"       && <ModelCallsTab spans={modelCalls} />}
      {activeTab === "Tool Calls"        && <ToolCallsTab spans={toolCalls} />}
      {activeTab === "Policy & Fallbacks" && (
        <PolicyTab
          fallbacks={fallbacks}
          policyViolations={policyViolations}
          approvalRequests={approvalRequests}
        />
      )}
    </div>
  );
}
