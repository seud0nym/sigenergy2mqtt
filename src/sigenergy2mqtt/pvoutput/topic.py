"""Topic state containers used by the PVOutput integration.

The :class:`Topic` dataclass tracks the current and previous value observed for
an MQTT topic so PVOutput services can compute deltas and recover state across
restarts.
"""

import time
from dataclasses import asdict, dataclass, is_dataclass


@dataclass
class Topic:
    """Runtime snapshot for one MQTT topic mapped to a PVOutput field."""

    topic: str
    scan_interval: int | None = None
    gain: float = 1.0
    precision: int | None = None
    state: float | None = 0.0
    timestamp: time.struct_time | None = None
    previous_state: float | None = None
    previous_timestamp: time.struct_time | None = None
    restore_timestamp: time.struct_time | None = None

    @staticmethod
    def json_decoder(obj):
        """Deserialize a persisted topic dictionary back into :class:`Topic`.

        Args:
            obj: Decoded JSON object candidate.
        """
        if "topic" in obj and "gain" in obj and "state" in obj and "timestamp" in obj:
            topic = Topic(**obj)
            topic.restore_timestamp = time.localtime()
            if isinstance(topic.timestamp, list):
                topic.timestamp = time.struct_time(topic.timestamp)
            if isinstance(topic.previous_timestamp, list):
                topic.previous_timestamp = time.struct_time(topic.previous_timestamp)
            return topic
        return obj

    @staticmethod
    def json_encoder(obj):
        """Serialize dataclass instances for JSON persistence.

        Args:
            obj: Object to serialize.
        """
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
