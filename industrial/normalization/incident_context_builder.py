"""Pure transformation: builds incident context from MachineState and MESEvent list."""

import statistics

from industrial.schemas.machine import MachineState, ReportingStatus
from industrial.schemas.mes_event import MESEvent, MESEventType


def build_incident_context(
    machine_state: MachineState,
    mes_events: list[MESEvent],
) -> dict:
    if not mes_events:
        return {
            # raw inputs
            "machine_id": machine_state.machine_id,
            "ordered_timeline": [],
            "sequence_gaps": [],
            "latency_by_event": {},
            "disconnect_detected": False,
            # derived signals
            "ingestion_silence": None,
            "wall_clock_silence": machine_state.reporting_status == ReportingStatus.silent,
            "sequence_gap_detected": False,
            "latency_spike_detected": False,
            # derived patterns
            "transport_degradation": False,
            "hard_disconnect": False,
            "silent_machine": machine_state.reporting_status == ReportingStatus.silent,
            "ingestion_issue": False,
        }

    mismatched = [e.event_id for e in mes_events if e.machine_id != machine_state.machine_id]
    if mismatched:
        raise ValueError(
            f"MESEvents with mismatched machine_id found: {mismatched}. "
            f"Expected machine_id={machine_state.machine_id!r}."
        )

    ordered_timeline = sorted(mes_events, key=lambda e: e.occurred_at)
    timeline_by_received = sorted(mes_events, key=lambda e: e.received_at)

    # --- ingestion_silence ---
    # Uses received_at only; compares gap between last two events against median heartbeat interval
    heartbeat_events = [e for e in timeline_by_received if e.event_type == MESEventType.heartbeat]
    heartbeat_gaps = [
        (heartbeat_events[i + 1].received_at - heartbeat_events[i].received_at).total_seconds()
        for i in range(len(heartbeat_events) - 1)
    ]

    if len(heartbeat_events) < 2:
        # Insufficient heartbeat data to determine ingestion silence
        ingestion_silence = None
    else:
        median_interval = statistics.median(heartbeat_gaps)
        last_gap = (heartbeat_events[-1].received_at - heartbeat_events[-2].received_at).total_seconds()
        ingestion_silence = last_gap > 2 * median_interval

    # --- wall_clock_silence ---
    wall_clock_silence = machine_state.reporting_status == ReportingStatus.silent

    # --- sequence_gaps ---
    sorted_seq = sorted(set(e.sequence_number for e in mes_events))
    sequence_gaps = [
        (sorted_seq[i], sorted_seq[i + 1])
        for i in range(len(sorted_seq) - 1)
        if sorted_seq[i + 1] != sorted_seq[i] + 1
    ]

    # --- latency_by_event ---
    latency_by_event = {
        e.event_id: (e.received_at - e.occurred_at).total_seconds()
        for e in mes_events
    }

    # --- disconnect_detected ---
    disconnect_detected = any(
        e.event_type == MESEventType.disconnect for e in mes_events
    )

    # --- derived signals ---
    sequence_gap_detected = len(sequence_gaps) > 0

    latency_values = list(latency_by_event.values())
    if len(latency_values) <= 1:
        latency_spike_detected = False
    else:
        median_latency = statistics.median(latency_values)
        latency_spike_detected = any(v > 3 * median_latency for v in latency_values)

    # --- derived patterns ---
    transport_degradation = sequence_gap_detected and latency_spike_detected
    connectivity_events = [
        e for e in ordered_timeline
        if e.event_type in (MESEventType.disconnect, MESEventType.reconnect)
    ]
    hard_disconnect = bool(connectivity_events) and connectivity_events[-1].event_type == MESEventType.disconnect
    silent_machine = wall_clock_silence and not disconnect_detected
    ingestion_issue = ingestion_silence is True and not sequence_gap_detected and not disconnect_detected

    return {
        # raw inputs
        "machine_id": machine_state.machine_id,
        "ordered_timeline": ordered_timeline,
        "sequence_gaps": sequence_gaps,
        "latency_by_event": latency_by_event,
        "disconnect_detected": disconnect_detected,
        # derived signals
        "ingestion_silence": ingestion_silence,
        "wall_clock_silence": wall_clock_silence,
        "sequence_gap_detected": sequence_gap_detected,
        "latency_spike_detected": latency_spike_detected,
        # derived patterns
        "transport_degradation": transport_degradation,
        "hard_disconnect": hard_disconnect,
        "silent_machine": silent_machine,
        "ingestion_issue": ingestion_issue,
    }
