import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export default function RunsPage() {
const [runs, setRuns] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

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

if (loading) return <div style={{ padding: "24px" }}>Loading runs...</div>;
if (error) return <div style={{ padding: "24px", color: "red" }}>Error: {error}</div>;

return (
<div style={{ padding: "24px" }}>
<h1>Operator Console</h1>
<h2>Runs</h2>
<ul>
{runs.map((run) => (
<li key={run.run_id}>
<Link to={`/runs/${run.run_id}`}><strong>{run.run_id}</strong></Link> | spans: {run.total_spans} | model calls: {run.model_calls} | tool calls: {run.tool_calls} | fallbacks: {run.fallbacks}
</li>
))}
</ul>
</div>
);
}