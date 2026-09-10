from __future__ import annotations

from sigenergy2mqtt.config import active_config

from .base import InfluxBase
from .hass_history_sync import HassHistorySync
from .service import InfluxService

__all__ = ["HassHistorySync", "InfluxBase", "InfluxService", "get_influxdb_services"]


def get_influxdb_services() -> list[InfluxService]:
    """Create and return one InfluxDB service instance per configured Modbus plant.

    Returns:
        list[InfluxService]: Ordered list of :class:`InfluxService` instances,
        one per entry in ``active_config.modbus``.
    """
    return [InfluxService(i) for i in range(len(active_config.modbus))]
