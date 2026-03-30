"""Schema for machine state derived from MES event stream."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ReportingStatus(str, Enum):
    # stale = last_seen_at exceeds 2x expected_reporting_interval_seconds
    reporting = "reporting"
    stale = "stale"
    silent = "silent"


class ConnectivityStatus(str, Enum):
    connected = "connected"
    disconnected = "disconnected"


class MachineState(BaseModel):
    # last_seen_at is derived from heartbeat events in MESEvent, not written independently
    machine_id: str
    last_seen_at: datetime
    reporting_status: ReportingStatus
    connectivity_status: ConnectivityStatus
    expected_reporting_interval_seconds: int

    model_config = {"frozen": True}
