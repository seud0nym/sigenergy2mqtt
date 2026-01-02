from __future__ import annotations

__all__ = ["get_influx_services"]

from .service import InfluxService
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from sigenergy2mqtt.main.thread_config import ThreadConfig


def get_influx_services(configs: list[ThreadConfig]):
    logger = logging.getLogger("influxdb")
    logger.setLevel(__import__("sigenergy2mqtt").config.Config.influxdb.log_level)
    svc = InfluxService(logger)
    return [svc]
