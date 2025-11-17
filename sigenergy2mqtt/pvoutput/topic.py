from dataclasses import asdict, dataclass, is_dataclass
import time


@dataclass
class Topic:
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
        if is_dataclass(obj):
            return asdict(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
