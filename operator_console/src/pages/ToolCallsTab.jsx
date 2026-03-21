import { durationLevel, durationColor, formatDuration, rowBackground } from "../utils/spans";

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

function DurationCell({ ms, maxMs }) {
  const level = durationLevel(ms, "tool_call");
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

export default function ToolCallsTab({ spans }) {
  const slowCount  = spans.filter(s => durationLevel(s.duration_ms, "tool_call") === "slow").length;
  const errorCount = spans.filter(s => s.error).length;
  const maxMs      = Math.max(...spans.map(s => s.duration_ms ?? 0), 1);

  return (
    <div>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
        <StatPill label="Total"  value={spans.length} color="#555" />
        {slowCount  > 0 && <StatPill label="Slow"   value={slowCount}  color="#b71c1c" />}
        {errorCount > 0 && <StatPill label="Errors" value={errorCount} color="#c62828" />}
      </div>

      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "13px" }}>
        <thead>
          <tr style={{ background: "#f5f5f5" }}>
            <th style={thStyle}>Tool</th>
            <th style={thStyle}>Backend</th>
            <th style={thStyle}>Started</th>
            <th style={thStyle}>Duration</th>
            <th style={thStyle}>Error</th>
          </tr>
        </thead>
        <tbody>
          {spans.length === 0 && (
            <tr><td colSpan={5} style={{ ...tdStyle, color: "#888" }}>No tool calls recorded</td></tr>
          )}
          {spans.map((s, i) => (
            <tr key={s.span_id ?? i} style={{ background: rowBackground(s) }}>
              <td style={{ ...tdStyle, fontWeight: "500" }}>{s.tool_name}</td>
              <td style={tdStyle}>{s.backend}</td>
              <td style={{ ...tdStyle, color: "#555", fontSize: "12px" }}>{s.started_at}</td>
              <td style={tdStyle}>
                <DurationCell ms={s.duration_ms} maxMs={maxMs} />
              </td>
              <td style={{ ...tdStyle, color: "#c62828" }}>{s.error || ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
