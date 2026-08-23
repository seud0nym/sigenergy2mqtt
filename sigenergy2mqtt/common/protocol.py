import time
from enum import Enum


class ProtocolVersion(float, Enum):
    N_A = 0.0
    V1_8 = 1.8
    V2_0 = 2.0
    V2_4 = 2.4
    V2_5 = 2.5
    V2_6 = 2.6
    V2_7 = 2.7
    V2_8 = 2.8
    V2_9 = 2.9


def ProtocolApplies(version: ProtocolVersion) -> str:
    match version:
        case ProtocolVersion.V1_8:
            return "2024-08-05"
        case ProtocolVersion.V2_0:
            return "2024-10-14"
        case ProtocolVersion.V2_4:
            return "2025-02-05"
        case ProtocolVersion.V2_5:
            return "2025-02-19"
        case ProtocolVersion.V2_6:
            return "2025-03-31"
        case ProtocolVersion.V2_7:
            return "2025-05-23"
        case ProtocolVersion.V2_8:
            return "2025-11-28"
        case ProtocolVersion.V2_9:
            return "2026-05-13"
        case _:
            return time.strftime("%Y-%m-%d", time.localtime())
