import { durationLevel, durationColor, formatDuration, hasDrift, driftLabel, rowBackground } from "../utils/spans";

const thStyle = { padding: "8px 12px", textAlign: "left", borderBottom: "2px solid #ddd", whiteSpace: "nowrap", fontSize: "12px" };
const tdStyle = { padding: "8px 12px", borderBottom: "1px solid #eee", verticalAlign: "middle", fontSize: "13px" };

function StatPill({ label, value, color }) {
  return (
    <span style={{
      padding: "3px 10px",
      borderRadius: "12px",
      fontSize: "12px",
      fontWeight: "bold",
      background: color + "22",
      color,
      border: `1px solid ${color}44`,
    }}>
      {label}: {value}
    </span>
  );
}

function DurationCell({ ms, type, maxMs }) {
  const level = durationLevel(ms, type);
  const { color } = durationColor(level);
  const pct = maxMs > 0 ? Math.round((ms / maxMs) * 80) : 0;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <span style={{ color, fontWeight: level === "slow" ? "bold" : "normal", minWidth: "52px" }}>
        {formatDuration(ms)}
      </span>
      <span style={{
        display: "inline-block",
        height: "6px",
        width: `${pct}px`,
        minWidth: "2px",
        background: color,
        borderRadius: "3px",
        opacity: 0.6,
      }} />
    </div>
  );
}

function DriftBadge({ span }) {
  if (!hasDrift(span)) return null;
  return (
    <span style={{
      marginLeft: "6px",
      padding: "1px 6px",
      borderRadius: "10px",
      fontSize: "11px",
      fontWeight: "bold",
      background: "#fff3e0",
      color: "#e65100",
      border: "1px solid #ffcc8044",
    }}>
      {driftLabel(span)}
    </span>
  );
}

export default function ModelCallsTab({ spans }) {
  const slowCount  = spans.filter(s => durationLevel(s.duration_ms, "model_call") === "slow").length;
  const driftCount = spans.filter(s => hasDrift(s)).length;
  const errorCount = spans.filter(s => s.error).length;
  const maxMs      = Math.max(...spans.map(s => s.duration_ms ?? 0), 1);

  return (
    <div>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
        <StatPill label="Total"  value={spans.length} color="#555" />
        {slowCount  > 0 && <StatPill label="Slow"   value={slowCount}  color="#b71c1c" />}
        {driftCount > 0 && <StatPill label="Drift"  value={driftCount} color="#e65100" />}
        {errorCount > 0 && <StatPill label="Errors" value={errorCount} color="#c62828" />}
      </div>

      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "13px" }}>
        <thead>
          <tr style={{ background: "#f5f5f5" }}>
            <th style={thStyle}>Agent</th>
            <th style={thStyle}>Model</th>
            <th style={thStyle}>Backend</th>
            <th style={thStyle}>Duration</th>
            <th style={thStyle}>Prompt</th>
            <th style={thStyle}>Response</th>
            <th style={thStyle}>Error</th>
          </tr>
        </thead>
        <tbody>
          {spans.length === 0 && (
            <tr><td colSpan={7} style={{ ...tdStyle, color: "#888" }}>No model calls recorded</td></tr>
          )}
          {spans.map((s, i) => (
            <tr key={s.span_id ?? i} style={{ background: rowBackground(s) }}>
              <td style={tdStyle}>{s.agent_role}</td>
              <td style={tdStyle}>{s.model_name}</td>
              <td style={tdStyle}>
                {s.actual_backend}
                <DriftBadge span={s} />
              </td>
              <td style={tdStyle}>
                <DurationCell ms={s.duration_ms} type="model_call" maxMs={maxMs} />
              </td>
              <td style={{ ...tdStyle, color: "#555" }}>{s.prompt_chars} ch</td>
              <td style={{ ...tdStyle, color: "#555" }}>{s.response_chars} ch</td>
              <td style={{ ...tdStyle, color: "#c62828" }}>{s.error || ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
