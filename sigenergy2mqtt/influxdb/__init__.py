from __future__ import annotations

__all__ = ["get_influx_services"]

from .influx_service import InfluxService
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sigenergy2mqtt.main.thread_config import ThreadConfig


def get_influx_services(configs: list[ThreadConfig]):
    logger = logging.getLogger("influxdb")
    logger.setLevel(__import__("sigenergy2mqtt").config.Config.influxdb.log_level)
    services = []
    # Create one service instance per plant index
    for plant_index in range(len(__import__("sigenergy2mqtt").config.Config.devices)):
        svc_logger = logging.getLogger(f"influxdb.plant{plant_index}")
        svc_logger.setLevel(__import__("sigenergy2mqtt").config.Config.influxdb.log_level)
        svc = InfluxService(svc_logger, plant_index)
        services.append(svc)
    return services
