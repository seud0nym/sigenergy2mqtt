import time
from enum import Enum


class ProtocolVersion(str, Enum):
    """Sigenergy Modbus Protocol versions.

    Values are the version strings as published (e.g. ``"2.10"``). Versions are
    ordered numerically by (major, minor), so ``V2_10 > V2_9`` even though
    ``"2.10" < "2.9"`` as strings and ``2.10 == 2.1`` as floats.
    """

    N_A = "0.0"
    V1_8 = "1.8"
    V2_0 = "2.0"
    V2_4 = "2.4"
    V2_5 = "2.5"
    V2_6 = "2.6"
    V2_7 = "2.7"
    V2_8 = "2.8"
    V2_9 = "2.9"
    V2_10 = "2.10"

    @property
    def key(self) -> tuple[int, int]:
        """The (major, minor) version tuple used for ordering."""
        major, minor = self.value.split(".")
        return int(major), int(minor)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ProtocolVersion):
            return NotImplemented
        return self.key < other.key

    def __le__(self, other: object) -> bool:
        if not isinstance(other, ProtocolVersion):
            return NotImplemented
        return self.key <= other.key

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, ProtocolVersion):
            return NotImplemented
        return self.key > other.key

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, ProtocolVersion):
            return NotImplemented
        return self.key >= other.key

    def __hash__(self) -> int:
        return str.__hash__(self)


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
        case ProtocolVersion.V2_10:
            return "2026-11-03"
        case _:
            return time.strftime("%Y-%m-%d", time.localtime())
