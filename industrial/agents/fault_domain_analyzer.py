"""Deterministic fault domain classification from pre-computed incident context."""

_SIGNAL_KEYS: tuple[str, ...] = (
    "disconnect_detected",
    "ingestion_silence",
    "wall_clock_silence",
    "sequence_gap_detected",
    "latency_spike_detected",
    "transport_degradation",
    "hard_disconnect",
    "silent_machine",
    "ingestion_issue",
)

_CONF_HARD_DISCONNECT = 0.9
_CONF_TRANSPORT_DEGRADATION = 0.8
_CONF_INGESTION_SILENCE = 0.7
_CONF_WALL_CLOCK_SILENCE = 0.7
_CONF_UNKNOWN = 0.2

_REASON_HARD_DISCONNECT = (
    "Machine sent an explicit disconnect event with no subsequent reconnect, "
    "indicating hard connectivity loss."
)
_REASON_TRANSPORT_DEGRADATION = (
    "Sequence gaps combined with latency spikes indicate in-transit packet loss "
    "or network instability."
)
_REASON_INGESTION_SILENCE = (
    "Ingestion pipeline has gone silent with no evidence of machine-side issues, "
    "pointing to MES or broker fault."
)
_REASON_WALL_CLOCK_SILENCE = (
    "Machine state is silent with no transport anomalies detected, "
    "indicating a machine-side failure."
)
_REASON_UNKNOWN = (
    "Insufficient signals to determine fault domain with confidence."
)


def analyze_fault_domain(context: dict) -> dict:
    if context["hard_disconnect"]:
        return {
            "primary_domain": "network",
            "confidence": _CONF_HARD_DISCONNECT,
            "supporting_signals": ["hard_disconnect"],
            "reasoning": _REASON_HARD_DISCONNECT,
        }
    elif context["transport_degradation"]:
        return {
            "primary_domain": "network",
            "confidence": _CONF_TRANSPORT_DEGRADATION,
            "supporting_signals": ["transport_degradation", "sequence_gap_detected", "latency_spike_detected"],
            "reasoning": _REASON_TRANSPORT_DEGRADATION,
        }
    elif context["ingestion_silence"] is True and not context["sequence_gap_detected"]:  # `is True` excludes non-bool truthy values
        return {
            "primary_domain": "mes",
            "confidence": _CONF_INGESTION_SILENCE,
            "supporting_signals": ["ingestion_silence", "sequence_gap_detected"],
            "reasoning": _REASON_INGESTION_SILENCE,
        }
    elif context["wall_clock_silence"] and not context["transport_degradation"] and not context["sequence_gap_detected"]:
        return {
            "primary_domain": "machine",
            "confidence": _CONF_WALL_CLOCK_SILENCE,
            "supporting_signals": ["wall_clock_silence"],
            "reasoning": _REASON_WALL_CLOCK_SILENCE,
        }
    else:
        return {
            "primary_domain": "unknown",
            "confidence": _CONF_UNKNOWN,
            "supporting_signals": [k for k in _SIGNAL_KEYS if context[k] is True],
            "reasoning": _REASON_UNKNOWN,
        }
