import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const RISK_STYLE = {
    HIGH:     { background: "#fce4ec", color: "#c62828", border: "1px solid #c6282844" },
    CRITICAL: { background: "#fce4ec", color: "#c62828", border: "1px solid #c6282844" },
    MEDIUM:   { background: "#fff8e1", color: "#f57f17", border: "1px solid #f57f1744" },
    LOW:      { background: "#e8f5e9", color: "#2e7d32", border: "1px solid #2e7d3244" },
};

function riskStyle(risk) {
    return RISK_STYLE[(risk || "").toUpperCase()] || RISK_STYLE.MEDIUM;
}

export default function ApprovalsPage() {
    const [approvals, setApprovals] = useState([]);
    const [loading, setLoading]     = useState(true);
    const [deciding, setDeciding]   = useState({}); // run_id → "approved" | "rejected"
    const [notes, setNotes]         = useState({}); // run_id → string
    const [submitting, setSubmitting] = useState({}); // run_id → bool

    useEffect(() => {
        function fetchApprovals() {
            api.get("/approvals")
                .then(r => { setApprovals(r.data.approvals || []); setLoading(false); })
                .catch(() => setLoading(false));
        }
        fetchApprovals();
        const id = setInterval(fetchApprovals, 3000);
        return () => clearInterval(id);
    }, []);

    function startDecision(run_id, decision) {
        setDeciding(prev => ({ ...prev, [run_id]: decision }));
    }

    function cancelDecision(run_id) {
        setDeciding(prev => { const n = { ...prev }; delete n[run_id]; return n; });
        setNotes(prev => { const n = { ...prev }; delete n[run_id]; return n; });
    }

    async function handleConfirm(run_id) {
        const decision = deciding[run_id];
        setSubmitting(prev => ({ ...prev, [run_id]: true }));
        try {
            await api.post(`/approvals/${run_id}/decide`, {
                decision,
                operator_note: notes[run_id] || "",
            });
            setApprovals(prev => prev.filter(a => a.run_id !== run_id));
            setDeciding(prev => { const n = { ...prev }; delete n[run_id]; return n; });
            setNotes(prev => { const n = { ...prev }; delete n[run_id]; return n; });
        } catch (err) {
            alert(`Failed: ${err.response?.data?.detail || err.message}`);
        } finally {
            setSubmitting(prev => { const n = { ...prev }; delete n[run_id]; return n; });
        }
    }

    if (loading) return <div style={{ padding: "24px" }}>Loading approvals...</div>;

    return (
        <div style={{ padding: "24px", maxWidth: "860px" }}>
            <h1 style={{ marginBottom: "4px" }}>Approval Queue</h1>
            <p style={{ color: "#666", marginTop: 0, marginBottom: "24px" }}>
                {approvals.length === 0
                    ? "No pending approvals."
                    : `${approvals.length} pending approval${approvals.length > 1 ? "s" : ""}`}
            </p>

            {approvals.map(a => {
                const isPending = !deciding[a.run_id];
                const chosen    = deciding[a.run_id];
                const isBusy    = submitting[a.run_id];

                return (
                    <div key={a.run_id} style={{
                        border: "1px solid #e0e0e0", borderRadius: "8px",
                        padding: "16px 20px", marginBottom: "16px",
                        background: "#fafafa",
                    }}>
                        {/* Header row */}
                        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginBottom: "8px" }}>
                            <Link to={`/runs/${a.run_id}`} style={{ fontFamily: "monospace", fontSize: "13px" }}>
                                {a.run_id}
                            </Link>
                            <span style={{
                                padding: "1px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "bold",
                                background: "#ede7f6", color: "#4527a0",
                            }}>{a.checkpoint}</span>
                            {a.task_risk && (
                                <span style={{
                                    padding: "1px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "bold",
                                    ...riskStyle(a.task_risk),
                                }}>{a.task_risk.toUpperCase()} RISK</span>
                            )}
                        </div>

                        {/* Task info */}
                        {a.task_title && (
                            <div style={{ fontWeight: "600", marginBottom: "4px" }}>{a.task_title}</div>
                        )}
                        {a.task_objective && (
                            <div style={{ color: "#444", fontSize: "13px", marginBottom: "6px" }}>{a.task_objective}</div>
                        )}

                        {/* Reason */}
                        <div style={{
                            fontSize: "12px", color: "#666", background: "#f5f5f5",
                            border: "1px solid #e0e0e0", borderRadius: "4px",
                            padding: "8px 10px", marginBottom: "10px",
                        }}>{a.reason}</div>

                        {/* Timestamp */}
                        <div style={{ fontSize: "11px", color: "#999", marginBottom: "12px" }}>
                            Requested: {a.requested_at ? new Date(a.requested_at).toLocaleString() : "—"}
                        </div>

                        {/* Action buttons */}
                        {isPending && (
                            <div style={{ display: "flex", gap: "8px" }}>
                                <button onClick={() => startDecision(a.run_id, "approved")} style={{
                                    padding: "6px 16px", borderRadius: "6px", border: "none",
                                    background: "#2e7d32", color: "#fff", cursor: "pointer", fontWeight: "bold",
                                }}>Approve</button>
                                <button onClick={() => startDecision(a.run_id, "rejected")} style={{
                                    padding: "6px 16px", borderRadius: "6px", border: "none",
                                    background: "#c62828", color: "#fff", cursor: "pointer", fontWeight: "bold",
                                }}>Deny</button>
                            </div>
                        )}

                        {/* Confirmation form */}
                        {!isPending && (
                            <div style={{
                                marginTop: "4px", padding: "12px", borderRadius: "6px",
                                background: chosen === "approved" ? "#e8f5e9" : "#fce4ec",
                                border: `1px solid ${chosen === "approved" ? "#2e7d3244" : "#c6282844"}`,
                            }}>
                                <div style={{ marginBottom: "8px", fontWeight: "600", color: chosen === "approved" ? "#2e7d32" : "#c62828" }}>
                                    Confirm {chosen === "approved" ? "Approval" : "Denial"}
                                </div>
                                <textarea
                                    placeholder="Operator note (optional)"
                                    value={notes[a.run_id] || ""}
                                    onChange={e => setNotes(prev => ({ ...prev, [a.run_id]: e.target.value }))}
                                    rows={2}
                                    style={{
                                        width: "100%", boxSizing: "border-box",
                                        padding: "6px 8px", borderRadius: "4px",
                                        border: "1px solid #ccc", fontSize: "13px",
                                        marginBottom: "8px", resize: "vertical",
                                    }}
                                />
                                <div style={{ display: "flex", gap: "8px" }}>
                                    <button
                                        onClick={() => handleConfirm(a.run_id)}
                                        disabled={isBusy}
                                        style={{
                                            padding: "6px 16px", borderRadius: "6px", border: "none",
                                            background: chosen === "approved" ? "#2e7d32" : "#c62828",
                                            color: "#fff", cursor: isBusy ? "not-allowed" : "pointer",
                                            fontWeight: "bold", opacity: isBusy ? 0.6 : 1,
                                        }}>
                                        {isBusy ? "Submitting…" : `Confirm ${chosen === "approved" ? "Approve" : "Deny"}`}
                                    </button>
                                    <button
                                        onClick={() => cancelDecision(a.run_id)}
                                        disabled={isBusy}
                                        style={{
                                            padding: "6px 16px", borderRadius: "6px",
                                            border: "1px solid #ccc", background: "#fff",
                                            cursor: isBusy ? "not-allowed" : "pointer",
                                        }}>
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
