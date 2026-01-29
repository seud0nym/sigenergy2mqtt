from __future__ import annotations

__all__ = ["get_influxdb_services"]

import logging
from typing import TYPE_CHECKING

from sigenergy2mqtt.config import Config

from .influx_service import InfluxService

if TYPE_CHECKING:
    from sigenergy2mqtt.main.thread_config import ThreadConfig


def get_influxdb_services(configs: list[ThreadConfig]):
    logger = logging.getLogger("influxdb")
    logger.setLevel(Config.influxdb.log_level)
    services = []
    # Create one service instance per plant index
    for plant_index in range(len(Config.modbus)):
        svc_logger = logging.getLogger(f"influxdb.plant{plant_index}")
        svc_logger.setLevel(Config.influxdb.log_level)
        svc = InfluxService(svc_logger, plant_index)
        services.append(svc)
    return services
