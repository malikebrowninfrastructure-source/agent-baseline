import { durationLevel, durationColor, formatDuration, hasDrift, driftLabel, rowBackground, spanLabel, typeBadgeStyle } from "../utils/spans";

const thStyle = { padding: "8px 12px", textAlign: "left", borderBottom: "2px solid #ddd", fontSize: "12px" };
const tdStyle = { padding: "8px 12px", borderBottom: "1px solid #eee", verticalAlign: "top" };

function buildTree(spans) {
  const byId = new Map();
  const roots = [];
  spans.forEach((s, i) => {
    const key = s.span_id ?? String(i);
    byId.set(key, { ...s, _key: key, children: [] });
  });
  spans.forEach((s, i) => {
    const key = s.span_id ?? String(i);
    const node = byId.get(key);
    if (s.parent_span_id && byId.has(s.parent_span_id)) {
      byId.get(s.parent_span_id).children.push(node);
    } else {
      roots.push(node);
    }
  });
  return roots;
}

function flattenTree(nodes, depth = 0, parentLast = []) {
  const result = [];
  nodes.forEach((node, idx) => {
    const isLast = idx === nodes.length - 1;
    result.push({ span: node, depth, isLast, parentLast });
    result.push(...flattenTree(node.children, depth + 1, [...parentLast, isLast]));
  });
  return result;
}

function CausalityPrefix({ depth, isLast, parentLast }) {
  if (depth === 0) return null;
  const parts = [];
  for (let i = 1; i < depth; i++) {
    parts.push(
      <span key={i} style={{ display: "inline-block", width: "20px", color: "#ccc", fontFamily: "monospace" }}>
        {parentLast[i] ? " " : "│"}
      </span>
    );
  }
  parts.push(
    <span key="c" style={{ display: "inline-block", width: "20px", color: "#aaa", fontFamily: "monospace" }}>
      {isLast ? "└─" : "├─"}
    </span>
  );
  return <>{parts}</>;
}

export default function Timeline({ spans = [] }) {
  const roots = buildTree(spans);
  const rows  = flattenTree(roots);

  return (
    <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "13px" }}>
      <thead>
        <tr style={{ background: "#f5f5f5" }}>
          <th style={{ ...thStyle, width: "32px" }}>#</th>
          <th style={thStyle}>Type</th>
          <th style={thStyle}>Label</th>
          <th style={thStyle}>Started / Timestamp</th>
          <th style={thStyle}>Duration</th>
          <th style={thStyle}>Error</th>
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 && (
          <tr><td colSpan={6} style={{ ...tdStyle, color: "#888" }}>No spans recorded</td></tr>
        )}
        {rows.map(({ span, depth, isLast, parentLast }, i) => {
          const level = durationLevel(span.duration_ms, span.span_type);
          const { color: durColor } = durationColor(level);
          return (
            <tr key={span._key ?? i} style={{ background: rowBackground(span) }}>
              <td style={{ ...tdStyle, color: "#bbb", fontSize: "11px", width: "32px" }}>{i + 1}</td>
              <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>
                <span style={typeBadgeStyle(span.span_type)}>{span.span_type}</span>
              </td>
              <td style={tdStyle}>
                <CausalityPrefix depth={depth} isLast={isLast} parentLast={parentLast} />
                {spanLabel(span)}
                {hasDrift(span) && (
                  <span style={{
                    marginLeft: "8px",
                    padding: "1px 6px",
                    borderRadius: "10px",
                    fontSize: "11px",
                    fontWeight: "bold",
                    background: "#fff3e0",
                    color: "#e65100",
                  }}>
                    {driftLabel(span)}
                  </span>
                )}
                {span.children?.length > 0 && (
                  <span style={{ marginLeft: "6px", color: "#aaa", fontSize: "11px" }}>
                    ({span.children.length} child{span.children.length > 1 ? "ren" : ""})
                  </span>
                )}
              </td>
              <td style={{ ...tdStyle, fontSize: "12px", color: "#555" }}>
                {span.started_at || span.timestamp || "—"}
              </td>
              <td style={{ ...tdStyle, whiteSpace: "nowrap", color: durColor, fontWeight: level === "slow" ? "bold" : "normal" }}>
                {formatDuration(span.duration_ms)}
              </td>
              <td style={{ ...tdStyle, color: "#c62828" }}>{span.error || ""}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
