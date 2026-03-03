from __future__ import annotations

import logging

from sigenergy2mqtt.config import active_config

from .hass_history_sync import HassHistorySync
from .influx_base import InfluxBase
from .influx_service import InfluxService

__all__ = ["get_influxdb_services", "InfluxBase", "InfluxService", "HassHistorySync"]


def get_influxdb_services() -> list[InfluxService]:
    """Create and return one InfluxDB service instance per configured Modbus plant.

    Initialises a parent ``influxdb`` logger and a child logger per plant
    (``influxdb.plant<index>``), both set to the log level defined in the
    active InfluxDB configuration.

    Returns:
        list[InfluxService]: Ordered list of :class:`InfluxService` instances,
        one per entry in ``active_config.modbus``.
    """
    logging.getLogger("influxdb").setLevel(active_config.influxdb.log_level)

    return [InfluxService(logging.getLogger(f"influxdb.plant{i}"), i) for i in range(len(active_config.modbus))]
