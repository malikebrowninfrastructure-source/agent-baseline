// Duration thresholds in ms per span type
const THRESHOLDS = {
  model_call: { slow: 10000, medium: 5000 },
  tool_call:  { slow: 500,   medium: 100  },
  _default:   { slow: 5000,  medium: 1000 },
};

export function durationLevel(ms, type) {
  if (ms == null) return null;
  const t = THRESHOLDS[type] ?? THRESHOLDS._default;
  if (ms >= t.slow)   return "slow";
  if (ms >= t.medium) return "medium";
  return "fast";
}

export function formatDuration(ms) {
  if (ms == null) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

export const DURATION_COLORS = {
  slow:   { color: "#b71c1c", background: "#fff5f5" },
  medium: { color: "#e65100", background: "#fff8f0" },
  fast:   { color: "#2e7d32", background: "transparent" },
};

export function durationColor(level) {
  return DURATION_COLORS[level] ?? { color: "#888", background: "transparent" };
}

export function hasDrift(span) {
  return span.span_type === "model_call" && span.fallback_occurred === true;
}

export function driftLabel(span) {
  return `${span.requested_backend} → ${span.actual_backend}`;
}

export function rowBackground(span) {
  if (span.error)   return "#fff0f0";
  const level = durationLevel(span.duration_ms, span.span_type);
  if (level === "slow")   return "#fff5f5";
  if (hasDrift(span))     return "#fffbf0";
  if (level === "medium") return "#fffdf5";
  return "white";
}

export function spanLabel(s) {
  if (s.span_type === "model_call")      return `${s.agent_role} → ${s.model_name}`;
  if (s.span_type === "tool_call")       return s.tool_name;
  if (s.span_type === "policy_violation") return `${s.violation_type} [${s.context}]`;
  if (s.span_type === "approval_request") return `checkpoint: ${s.checkpoint}`;
  return s.span_type;
}

const BADGE_COLORS = {
  model_call:       { background: "#e3f2fd", color: "#1565c0" },
  tool_call:        { background: "#e8f5e9", color: "#2e7d32" },
  policy_violation: { background: "#ffebee", color: "#c62828" },
  approval_request: { background: "#fff8e1", color: "#f57f17" },
};

export function typeBadgeStyle(type) {
  const c = BADGE_COLORS[type] ?? { background: "#f5f5f5", color: "#555" };
  return {
    padding: "2px 8px",
    borderRadius: "12px",
    fontSize: "11px",
    fontWeight: "bold",
    whiteSpace: "nowrap",
    ...c,
  };
}
