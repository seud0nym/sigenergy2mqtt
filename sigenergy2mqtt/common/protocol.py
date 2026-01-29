from datetime import datetime
from enum import Enum


class Protocol(float, Enum):
    N_A = 0.0
    V1_8 = 1.8
    V2_0 = 2.0
    V2_4 = 2.4
    V2_5 = 2.5
    V2_6 = 2.6
    V2_7 = 2.7
    V2_8 = 2.8


def ProtocolApplies(version: Protocol) -> str:
    match version:
        case Protocol.V1_8:
            return "2024-08-05"
        case Protocol.V2_0:
            return "2024-10-14"
        case Protocol.V2_4:
            return "2025-02-05"
        case Protocol.V2_5:
            return "2025-02-19"
        case Protocol.V2_6:
            return "2025-03-31"
        case Protocol.V2_7:
            return "2025-05-23"
        case Protocol.V2_8:
            return "2025-11-28"
        case _:
            return datetime.today().strftime("%Y-%m-%d")
