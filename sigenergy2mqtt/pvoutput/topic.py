from dataclasses import asdict, dataclass, is_dataclass
import time


@dataclass
class Topic:
    topic: str
    gain: float
    state: float = 0.0
    timestamp: time.struct_time = None

    @staticmethod
    def json_decoder(obj):
        if "topic" in obj and "gain" in obj and "state" in obj and "timestamp" in obj:
            topic = Topic(**obj)
            if isinstance(topic.timestamp, list):
                topic.timestamp = time.struct_time(topic.timestamp)
            return topic
        return obj

    @staticmethod
    def json_encoder(obj):
        if is_dataclass(obj):
            return asdict(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
