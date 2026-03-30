"""Schema for raw events emitted by the MES ingestion layer."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class MESEventType(str, Enum):
    heartbeat = "heartbeat"
    disconnect = "disconnect"
    reconnect = "reconnect"


class MESEvent(BaseModel):
    event_id: str
    machine_id: str
    event_type: MESEventType
    occurred_at: datetime   # machine-side timestamp
    received_at: datetime   # ingestion-layer timestamp (set by ingestion pipeline, not machine)
    sequence_number: int

    model_config = {"frozen": True}
