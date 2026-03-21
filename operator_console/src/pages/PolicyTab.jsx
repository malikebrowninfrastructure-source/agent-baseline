import { driftLabel } from "../utils/spans";

const thStyle = { padding: "8px 12px", textAlign: "left", borderBottom: "2px solid #ddd", fontSize: "12px" };
const tdStyle = { padding: "8px 12px", borderBottom: "1px solid #eee", fontSize: "13px", verticalAlign: "top" };

function SectionHeader({ title, count, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px", margin: "0 0 12px" }}>
      <h3 style={{ margin: 0, fontSize: "14px" }}>{title}</h3>
      <span style={{
        padding: "2px 10px",
        borderRadius: "12px",
        fontSize: "12px",
        fontWeight: "bold",
        background: count > 0 ? color + "22" : "#f5f5f5",
        color: count > 0 ? color : "#aaa",
        border: `1px solid ${count > 0 ? color + "44" : "#ddd"}`,
      }}>
        {count}
      </span>
    </div>
  );
}

function Empty({ message }) {
  return <p style={{ color: "#aaa", fontSize: "13px", margin: "0 0 32px" }}>{message}</p>;
}

export default function PolicyTab({ fallbacks, policyViolations, approvalRequests }) {
  return (
    <div>
      {/* Backend Drift / Fallbacks */}
      <div style={{ marginBottom: "36px" }}>
        <SectionHeader title="Backend Drift / Fallbacks" count={fallbacks.length} color="#e65100" />
        {fallbacks.length === 0 ? <Empty message="No fallbacks — all agents ran on their requested backend." /> : (
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "#fff8f0" }}>
                <th style={thStyle}>Agent</th>
                <th style={thStyle}>Drift</th>
                <th style={thStyle}>Reason</th>
                <th style={thStyle}>Duration</th>
              </tr>
            </thead>
            <tbody>
              {fallbacks.map((s, i) => (
                <tr key={s.span_id ?? i} style={{ background: "#fffbf0" }}>
                  <td style={tdStyle}>{s.agent_role}</td>
                  <td style={tdStyle}>
                    <span style={{
                      padding: "2px 8px",
                      borderRadius: "10px",
                      fontSize: "11px",
                      fontWeight: "bold",
                      background: "#fff3e0",
                      color: "#e65100",
                      border: "1px solid #ffcc8044",
                    }}>
                      {driftLabel(s)}
                    </span>
                  </td>
                  <td style={tdStyle}>{s.fallback_reason || "—"}</td>
                  <td style={tdStyle}>{s.duration_ms != null ? `${s.duration_ms}ms` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Policy Violations */}
      <div style={{ marginBottom: "36px" }}>
        <SectionHeader title="Policy Violations" count={policyViolations.length} color="#c62828" />
        {policyViolations.length === 0 ? <Empty message="No policy violations recorded." /> : (
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "#fff0f0" }}>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Context</th>
                <th style={thStyle}>Detail</th>
                <th style={thStyle}>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {policyViolations.map((s, i) => (
                <tr key={s.span_id ?? i} style={{ background: "#fff5f5" }}>
                  <td style={tdStyle}>
                    <span style={{
                      padding: "2px 8px",
                      borderRadius: "10px",
                      fontSize: "11px",
                      fontWeight: "bold",
                      background: "#ffebee",
                      color: "#c62828",
                    }}>
                      {s.violation_type}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, color: "#555" }}>{s.context}</td>
                  <td style={tdStyle}>{s.detail}</td>
                  <td style={{ ...tdStyle, color: "#888", fontSize: "12px" }}>{s.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Approval Requests */}
      <div>
        <SectionHeader title="Approval Requests" count={approvalRequests.length} color="#2e7d32" />
        {approvalRequests.length === 0 ? <Empty message="No approval checkpoints triggered." /> : (
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "#f1f8e9" }}>
                <th style={thStyle}>Checkpoint</th>
                <th style={thStyle}>Reason</th>
                <th style={thStyle}>Artifact</th>
                <th style={thStyle}>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {approvalRequests.map((s, i) => (
                <tr key={s.span_id ?? i} style={{ background: "#f9fbe7" }}>
                  <td style={tdStyle}>
                    <span style={{
                      padding: "2px 8px",
                      borderRadius: "10px",
                      fontSize: "11px",
                      fontWeight: "bold",
                      background: "#e8f5e9",
                      color: "#2e7d32",
                    }}>
                      {s.checkpoint}
                    </span>
                  </td>
                  <td style={tdStyle}>{s.reason}</td>
                  <td style={{ ...tdStyle, color: "#555", fontSize: "12px", wordBreak: "break-all" }}>{s.artifact_path}</td>
                  <td style={{ ...tdStyle, color: "#888", fontSize: "12px" }}>{s.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
