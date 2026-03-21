import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api";
import Timeline from "./Timeline";
import ModelCallsTab from "./ModelCallsTab";
import ToolCallsTab from "./ToolCallsTab";
import PolicyTab from "./PolicyTab";

const TABS = ["Summary", "Timeline", "Model Calls", "Tool Calls", "Policy & Fallbacks"];

const tdStyle = { padding: "8px 12px", borderBottom: "1px solid #eee", fontSize: "13px" };

export default function RunDetailPage() {
  const { runId } = useParams();
  const [run, setRun]         = useState(null);
  const [summary, setSummary] = useState(null);
  const [spans, setSpans]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [activeTab, setActiveTab] = useState("Summary");
  const [connStatus, setConnStatus] = useState(null); // null | "connecting" | "connected"
  const [runLoaded, setRunLoaded]   = useState(false);
  const [byteOffset, setByteOffset] = useState(0);

  useEffect(() => {
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
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [runId]);

  useEffect(() => {
    if (!runLoaded || run?.final_status) return;

    const es = new EventSource(
      `http://127.0.0.1:8000/runs/${runId}/stream?since=${byteOffset}`
    );
    setConnStatus("connecting");

    es.onopen = () => setConnStatus("connected");

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

    // Don't close on error — let SSE auto-reconnect; show connecting state
    es.onerror = () => setConnStatus("connecting");

    return () => { es.close(); setConnStatus(null); };
  }, [runId, runLoaded, byteOffset]);

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
            background: connStatus === "connected" ? "#e8f5e9" : "#fff8e1",
            color:      connStatus === "connected" ? "#2e7d32" : "#f57f17",
            border:     `1px solid ${connStatus === "connected" ? "#2e7d3244" : "#f57f1744"}`,
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
          }}>
            <span className="live-dot">●</span>
            {connStatus === "connected" ? "connected" : "connecting…"}
          </span>
        ) : null}
      </div>

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
