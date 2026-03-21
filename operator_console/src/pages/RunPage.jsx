import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export default function RunsPage() {
const [runs, setRuns] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);
const [connStatus, setConnStatus] = useState(null); // null | "connecting" | "connected"

useEffect(() => {
  api.get("/runs")
    .then(async (res) => {
      const items = res.data.runs || [];
      const summaries = await Promise.all(
        items.map(async (item) => {
          const summary = await api.get(`/runs/${item.run_id}/summary`);
          return summary.data;
        })
      );
      setRuns(summaries);
    })
    .catch((err) => setError(err.message))
    .finally(() => setLoading(false));
}, []);

useEffect(() => {
  if (loading) return;
  const es = new EventSource("http://127.0.0.1:8000/runs/stream");
  setConnStatus("connecting");
  es.onopen = () => setConnStatus("connected");

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
        total_spans:  (x.total_spans  ?? 0) + 1,
        model_calls:  r.span_type === "model_call"  ? (x.model_calls  ?? 0) + 1 : x.model_calls,
        tool_calls:   r.span_type === "tool_call"   ? (x.tool_calls   ?? 0) + 1 : x.tool_calls,
        fallbacks:    r.fallback_occurred            ? (x.fallbacks    ?? 0) + 1 : x.fallbacks,
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

  es.onerror = () => setConnStatus("connecting");
  return () => { es.close(); setConnStatus(null); };
}, [loading]);

if (loading) return <div style={{ padding: "24px" }}>Loading runs...</div>;
if (error) return <div style={{ padding: "24px", color: "red" }}>Error: {error}</div>;

return (
<div style={{ padding: "24px" }}>
  <style>{`
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.35} }
    .live-dot { animation: blink 1.4s ease-in-out infinite; }
  `}</style>
  <h1>Operator Console</h1>
  <h2 style={{ display: "inline-flex", alignItems: "center", gap: "10px" }}>
    Runs
    {connStatus && (
      <span style={{
        padding: "2px 10px", borderRadius: "12px", fontSize: "12px",
        fontWeight: "bold", display: "inline-flex", alignItems: "center", gap: "5px",
        background: connStatus === "connected" ? "#e8f5e9" : "#fff8e1",
        color:      connStatus === "connected" ? "#2e7d32" : "#f57f17",
        border:     `1px solid ${connStatus === "connected" ? "#2e7d3244" : "#f57f1744"}`,
      }}>
        <span className="live-dot">●</span>
        {connStatus === "connected" ? "connected" : "connecting…"}
      </span>
    )}
  </h2>
  <ul>
  {runs.map((run) => (
    <li key={run.run_id} style={{ marginBottom: "6px" }}>
      <Link to={`/runs/${run.run_id}`}><strong>{run.run_id}</strong></Link>
      {run.final_status ? (
        <span style={{
          marginLeft: "8px", padding: "1px 7px", borderRadius: "8px", fontSize: "11px",
          background: run.final_status === "success" ? "#e8f5e9" : "#fce4ec",
          color:      run.final_status === "success" ? "#2e7d32" : "#c62828",
        }}>{run.final_status}</span>
      ) : run.current_stage ? (
        <span style={{
          marginLeft: "8px", padding: "1px 7px", borderRadius: "8px", fontSize: "11px",
          background: "#fff8e1", color: "#f57f17",
        }}>{run.current_stage}</span>
      ) : null}
      {" "}| spans: {run.total_spans} | model calls: {run.model_calls} | tool calls: {run.tool_calls} | fallbacks: {run.fallbacks}
    </li>
  ))}
  </ul>
</div>
);
}
