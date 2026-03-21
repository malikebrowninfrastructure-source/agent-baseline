import { useEffect, useRef, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const ACCENT = {
  green:  { background: "#f1f8f2", border: "1px solid #c8e6c9", color: "#2e7d32" },
  red:    { background: "#fdf3f3", border: "1px solid #ffcdd2", color: "#c62828" },
  amber:  { background: "#fffbf0", border: "1px solid #ffe082", color: "#e65100" },
  purple: { background: "#f5f0ff", border: "1px solid #d1c4e9", color: "#4527a0" },
  none:   { background: "#fafafa", border: "1px solid #e0e0e0", color: "#1a1a1a" },
};

function Stat({ label, value, accent = "none" }) {
  const s = ACCENT[accent] || ACCENT.none;
  return (
    <div style={{
      ...s, borderRadius: "8px", padding: "14px 18px",
      minWidth: "90px", textAlign: "center", flex: "1 1 90px",
    }}>
      <div style={{ fontSize: "26px", fontWeight: "700", lineHeight: 1.1, color: s.color }}>
        {value}
      </div>
      <div style={{ fontSize: "10px", color: "#777", marginTop: "5px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </div>
    </div>
  );
}

export default function RunsPage() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connStatus, setConnStatus] = useState(null);
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const wasConnected = useRef(false);

  const fetchRuns = useCallback(() => {
    api.get("/runs")
      .then(async (res) => {
        const items = res.data.runs || [];
        const summaries = await Promise.all(
          items.map(async (item) => {
            const s = await api.get(`/runs/${item.run_id}/summary`);
            return s.data;
          })
        );
        setRuns(summaries);
      })
      .catch((err) => setError(err.message));
  }, []);

  const fetchApprovals = useCallback(() => {
    api.get("/approvals")
      .then(r => setPendingApprovals((r.data.approvals || []).length))
      .catch(() => {});
  }, []);

  // Initial load
  useEffect(() => {
    api.get("/runs")
      .then(async (res) => {
        const items = res.data.runs || [];
        const summaries = await Promise.all(
          items.map(async (item) => {
            const s = await api.get(`/runs/${item.run_id}/summary`);
            return s.data;
          })
        );
        setRuns(summaries);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Pending approvals poll
  useEffect(() => {
    fetchApprovals();
    const id = setInterval(fetchApprovals, 5000);
    return () => clearInterval(id);
  }, [fetchApprovals]);

  // Global SSE stream
  useEffect(() => {
    if (loading) return;
    const es = new EventSource("http://127.0.0.1:8000/runs/stream");
    setConnStatus("connecting");

    es.onopen = () => {
      if (wasConnected.current) {
        fetchRuns();
        fetchApprovals();
      }
      wasConnected.current = true;
      setConnStatus("connected");
    };

    es.addEventListener("run_created", (e) => {
      const r = JSON.parse(e.data);
      setConnStatus("connected");
      setRuns(prev => {
        if (prev.some(x => x.run_id === r.run_id)) return prev;
        return [{ run_id: r.run_id, current_stage: r.current_stage,
                  total_spans: 0, model_calls: 0, tool_calls: 0, fallbacks: 0 }, ...prev];
      });
    });

    es.addEventListener("run_stage_changed", (e) => {
      const r = JSON.parse(e.data);
      setConnStatus("connected");
      setRuns(prev => prev.map(x =>
        x.run_id === r.run_id ? { ...x, current_stage: r.current_stage } : x
      ));
    });

    es.addEventListener("run_span", (e) => {
      const r = JSON.parse(e.data);
      setConnStatus("connected");
      setRuns(prev => prev.map(x => {
        if (x.run_id !== r.run_id) return x;
        return {
          ...x,
          total_spans: (x.total_spans  ?? 0) + 1,
          model_calls: r.span_type === "model_call" ? (x.model_calls ?? 0) + 1 : x.model_calls,
          tool_calls:  r.span_type === "tool_call"  ? (x.tool_calls  ?? 0) + 1 : x.tool_calls,
          fallbacks:   r.fallback_occurred           ? (x.fallbacks   ?? 0) + 1 : x.fallbacks,
        };
      }));
    });

    es.addEventListener("run_completed", (e) => {
      const r = JSON.parse(e.data);
      setConnStatus("connected");
      setRuns(prev => prev.map(x =>
        x.run_id === r.run_id ? { ...x, ...r } : x
      ));
    });

    es.onerror = () => setConnStatus(wasConnected.current ? "reconnecting" : "connecting");
    return () => { es.close(); setConnStatus(null); wasConnected.current = false; };
  }, [loading, fetchRuns, fetchApprovals]);

  // Derived metrics
  const totalRuns      = runs.length;
  const activeCount    = runs.filter(r => !r.final_status).length;
  const successCount   = runs.filter(r => r.final_status === "success").length;
  const failedCount    = runs.filter(r => r.final_status && r.final_status !== "success").length;
  const totalFallbacks = runs.reduce((s, r) => s + (r.fallbacks || 0), 0);
  const completed      = runs.filter(r => r.final_status);
  const avgSpans       = completed.length
    ? (completed.reduce((s, r) => s + (r.total_spans   || 0), 0) / completed.length).toFixed(1) : "—";
  const avgModelCalls  = completed.length
    ? (completed.reduce((s, r) => s + (r.model_calls   || 0), 0) / completed.length).toFixed(1) : "—";

  if (loading) return <div style={{ padding: "24px" }}>Loading runs...</div>;
  if (error)   return <div style={{ padding: "24px", color: "red" }}>Error: {error}</div>;

  return (
    <div style={{ padding: "24px", maxWidth: "1100px" }}>
      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.35} }
        .live-dot { animation: blink 1.4s ease-in-out infinite; }
        .run-row:hover td { background: #f9f9f9; }
      `}</style>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "20px" }}>Operator Console</h1>
        {connStatus && (
          <span style={{
            padding: "3px 10px", borderRadius: "12px", fontSize: "12px",
            fontWeight: "bold", display: "inline-flex", alignItems: "center", gap: "5px",
            background: connStatus === "connected" ? "#e8f5e9" : connStatus === "reconnecting" ? "#fce4ec" : "#fff8e1",
            color:      connStatus === "connected" ? "#2e7d32" : connStatus === "reconnecting" ? "#c62828" : "#f57f17",
            border:     `1px solid ${connStatus === "connected" ? "#2e7d3244" : connStatus === "reconnecting" ? "#c6282844" : "#f57f1744"}`,
          }}>
            <span className="live-dot">●</span>
            {connStatus === "connected" ? "live" : connStatus === "reconnecting" ? "reconnecting…" : "connecting…"}
          </span>
        )}
      </div>

      {/* Stale data banner */}
      {connStatus === "reconnecting" && (
        <div style={{
          padding: "8px 14px", background: "#fff3e0",
          border: "1px solid #ffe0b2", borderRadius: "6px",
          fontSize: "13px", color: "#e65100", marginBottom: "12px",
        }}>
          Connection lost — data may be stale. Reconnecting…
        </div>
      )}

      {/* Metrics strip */}
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "32px" }}>
        <Stat label="Total Runs"       value={totalRuns}        />
        <Stat label="Active"           value={activeCount}      accent={activeCount > 0 ? "purple" : "none"} />
        <Stat label="Success"          value={successCount}     accent={successCount > 0 ? "green"  : "none"} />
        <Stat label="Failed"           value={failedCount}      accent={failedCount  > 0 ? "red"    : "none"} />
        <Stat label="Pending Approval" value={pendingApprovals} accent={pendingApprovals > 0 ? "amber" : "none"} />
        <Stat label="Avg Spans"        value={avgSpans}         />
        <Stat label="Avg Model Calls"  value={avgModelCalls}    />
        <Stat label="Total Fallbacks"  value={totalFallbacks}   accent={totalFallbacks > 0 ? "amber" : "none"} />
      </div>

      {/* Runs table */}
      <div style={{ fontSize: "12px", fontWeight: "600", color: "#888", textTransform: "uppercase",
                    letterSpacing: "0.05em", marginBottom: "10px" }}>
        Runs ({totalRuns})
      </div>

      {runs.length === 0 ? (
        <p style={{ color: "#bbb", fontSize: "14px" }}>No runs recorded yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e8e8e8" }}>
              {["Run ID", "Status", "Spans", "Model Calls", "Tool Calls", "Fallbacks"].map(h => (
                <th key={h} style={{ padding: "6px 10px", color: "#999", fontWeight: "600",
                                     fontSize: "11px", textAlign: h === "Run ID" || h === "Status" ? "left" : "right",
                                     textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id} className="run-row" style={{ borderBottom: "1px solid #f0f0f0" }}>
                <td style={{ padding: "9px 10px", fontFamily: "monospace", fontSize: "12px" }}>
                  <Link to={`/runs/${run.run_id}`} style={{ color: "#1565c0", textDecoration: "none" }}>
                    {run.run_id}
                  </Link>
                </td>
                <td style={{ padding: "9px 10px" }}>
                  {run.final_status ? (
                    <span style={{
                      padding: "2px 8px", borderRadius: "8px", fontSize: "11px", fontWeight: "bold",
                      background: run.final_status === "success" ? "#e8f5e9" : "#fce4ec",
                      color:      run.final_status === "success" ? "#2e7d32" : "#c62828",
                    }}>{run.final_status}</span>
                  ) : run.current_stage ? (
                    <span style={{
                      padding: "2px 8px", borderRadius: "8px", fontSize: "11px", fontWeight: "bold",
                      background: "#f3e5f5", color: "#6a1b9a",
                    }}>{run.current_stage}</span>
                  ) : (
                    <span style={{ color: "#ccc", fontSize: "11px" }}>—</span>
                  )}
                </td>
                <td style={{ padding: "9px 10px", textAlign: "right", color: "#555" }}>{run.total_spans  ?? "—"}</td>
                <td style={{ padding: "9px 10px", textAlign: "right", color: "#555" }}>{run.model_calls  ?? "—"}</td>
                <td style={{ padding: "9px 10px", textAlign: "right", color: "#555" }}>{run.tool_calls   ?? "—"}</td>
                <td style={{ padding: "9px 10px", textAlign: "right",
                             color: run.fallbacks > 0 ? "#e65100" : "#555", fontWeight: run.fallbacks > 0 ? "600" : "400" }}>
                  {run.fallbacks ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
