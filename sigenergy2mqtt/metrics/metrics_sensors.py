"""
Home Assistant sensor entities that expose :class:`~sigenergy2mqtt.metrics.Metrics`
values over MQTT.

Each sensor reads one or more class-level attributes from :class:`Metrics` on
every scan interval and publishes the result to its configured state topic
under ``sigenergy2mqtt/metrics/``.
"""

import logging
import time
from typing import Any, cast

from sigenergy2mqtt.common import PERCENTAGE, DeviceClass, Protocol, ProtocolApplies
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusLockFactory
from sigenergy2mqtt.sensors.base import ReadableSensorMixin

from .metrics import Metrics


class MetricsSensor(ReadableSensorMixin):
    """
    Base class for all metrics sensors.

    Subclasses implement :meth:`_update_internal_state` to pull the relevant
    value from :class:`Metrics` and call :meth:`set_latest_state`. The default
    scan interval is 1 second.

    MQTT topics are structured as ``sigenergy2mqtt/metrics/<suffix>`` where
    *suffix* is the ``object_id`` with the ``sigenergy2mqtt_`` prefix stripped,
    and availability is tied to ``sigenergy2mqtt/status``.
    """

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        unit: str | None = None,
        device_class: DeviceClass | None = None,
        icon: str | None = None,
        precision: int | None = None,
        **kwargs,
    ):
        scan_interval = kwargs.pop("scan_interval", 1)
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            unit=unit,
            device_class=device_class,
            state_class=None,
            icon=icon,
            gain=None,
            precision=precision,
            scan_interval=scan_interval,
            **kwargs,
        )
        self["enabled_by_default"] = True

    async def _update_internal_state(self, **kwargs) -> bool:
        raise NotImplementedError

    def configure_mqtt_topics(self, device_id: str) -> str:
        """
        Override topic configuration to use the ``sigenergy2mqtt/metrics/`` namespace.

        The state topic is derived from ``object_id`` by stripping the
        ``sigenergy2mqtt_`` prefix: e.g. ``sigenergy2mqtt_modbus_locks``
        becomes ``sigenergy2mqtt/metrics/modbus_locks``.
        """
        # Override to match existing topic structure: sigenergy2mqtt/metrics/{id}
        base = "sigenergy2mqtt/metrics"
        object_id = cast(str, self["object_id"])
        suffix = object_id.replace("sigenergy2mqtt_", "")
        self["state_topic"] = f"{base}/{suffix}"
        self["availability_topic"] = "sigenergy2mqtt/status"
        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Configured MQTT topics >>> state_topic={self['state_topic']})")
        return base

    def publish_attributes(self, mqtt_client: Any, clean: bool = False, **kwargs) -> None:
        """Metrics sensors do not publish extra MQTT attributes."""
        pass


class MQTTPublishFailures(MetricsSensor):
    """Cumulative count of MQTT state publish failures."""

    def __init__(self):
        super().__init__(
            name="MQTT Publish Failures",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_mqtt_publish_failures",
            object_id="sigenergy2mqtt_mqtt_publish_failures",
            icon="mdi:counter",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        self.set_latest_state(Metrics.sigenergy2mqtt_mqtt_publish_failures)
        return True


class MQTTPhysicalPublishes(MetricsSensor):
    """Percentage of MQTT publish attempts that were physically published."""

    def __init__(self):
        super().__init__(
            name="MQTT Physical Publishes",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_mqtt_physical_publish_percentage",
            object_id="sigenergy2mqtt_mqtt_physical_publish_percentage",
            unit=PERCENTAGE,
            icon="mdi:percent",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        self.set_latest_state(Metrics.sigenergy2mqtt_mqtt_physical_publish_percentage)
        return True


class ModbusCacheHits(MetricsSensor):
    """Percentage of modbus reads satisfied from cache."""

    def __init__(self):
        super().__init__(
            name="Modbus Cache Hits",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_cache_hit_percentage",
            object_id="sigenergy2mqtt_modbus_cache_hit_percentage",
            unit=PERCENTAGE,
            icon="mdi:percent",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_modbus_cache_hit_percentage
        self.set_latest_state(new_state)
        return True


class ModbusPhysicalReads(MetricsSensor):
    """Percentage of modbus reads that resulted in a physical bus read (i.e. cache misses)."""

    def __init__(self):
        super().__init__(
            name="Modbus Physical Reads",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_physical_reads",
            object_id="sigenergy2mqtt_modbus_physical_reads",
            unit=PERCENTAGE,
            icon="mdi:percent",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_modbus_physical_read_percentage
        self.set_latest_state(new_state)
        return True


class ModbusReadsPerSecond(MetricsSensor):
    """Modbus register reads per second since service start."""

    def __init__(self):
        super().__init__(
            name="Modbus Reads/second",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_reads_sec",
            object_id="sigenergy2mqtt_modbus_reads_sec",
            icon="mdi:timer-play-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        elapsed = time.monotonic() - Metrics._started
        if elapsed > 0:
            value = Metrics.sigenergy2mqtt_modbus_register_reads / elapsed
        else:
            value = 0.0
        self.set_latest_state(value)
        return True


class ModbusReadErrors(MetricsSensor):
    """Cumulative count of modbus read errors."""

    def __init__(self):
        super().__init__(
            name="Modbus Read Errors",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_read_errors",
            object_id="sigenergy2mqtt_modbus_read_errors",
            icon="mdi:counter",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_modbus_read_errors
        self.set_latest_state(new_state)
        return True


class ModbusReadMax(MetricsSensor):
    """Maximum single modbus read duration in milliseconds."""

    def __init__(self):
        super().__init__(
            name="Modbus Read Max",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_read_max",
            object_id="sigenergy2mqtt_modbus_read_max",
            unit="ms",
            icon="mdi:timer-plus-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_modbus_read_max
        if value == float("inf"):
            value = 0.0
        self.set_latest_state(value)
        return True


class ModbusReadMean(MetricsSensor):
    """Mean modbus read duration per register read, in milliseconds."""

    def __init__(self):
        super().__init__(
            name="Modbus Read Mean",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_read_mean",
            object_id="sigenergy2mqtt_modbus_read_mean",
            unit="ms",
            icon="mdi:timer-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_modbus_read_mean
        self.set_latest_state(value)
        return True


class ModbusReadMin(MetricsSensor):
    """Minimum single modbus read duration in milliseconds."""

    def __init__(self):
        super().__init__(
            name="Modbus Read Min",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_read_min",
            object_id="sigenergy2mqtt_modbus_read_min",
            unit="ms",
            icon="mdi:timer-minus-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_modbus_read_min
        if value == float("inf"):
            value = 0.0
        self.set_latest_state(value)
        return True


class ModbusWriteErrors(MetricsSensor):
    """Cumulative count of modbus write errors."""

    def __init__(self):
        super().__init__(
            name="Modbus Write Errors",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_write_errors",
            object_id="sigenergy2mqtt_modbus_write_errors",
            icon="mdi:counter",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_modbus_write_errors
        self.set_latest_state(new_state)
        return True


class ModbusWriteMax(MetricsSensor):
    """Maximum single modbus write duration in milliseconds."""

    def __init__(self):
        super().__init__(
            name="Modbus Write Max",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_write_max",
            object_id="sigenergy2mqtt_modbus_write_max",
            unit="ms",
            icon="mdi:timer-plus-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_modbus_write_max
        if value == float("inf"):
            value = 0.0
        self.set_latest_state(value)
        return True


class ModbusWriteMean(MetricsSensor):
    """Mean modbus write duration per write call, in milliseconds."""

    def __init__(self):
        super().__init__(
            name="Modbus Write Mean",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_write_mean",
            object_id="sigenergy2mqtt_modbus_write_mean",
            unit="ms",
            icon="mdi:timer-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_modbus_write_mean
        self.set_latest_state(value)
        return True


class ModbusWriteMin(MetricsSensor):
    """Minimum single modbus write duration in milliseconds."""

    def __init__(self):
        super().__init__(
            name="Modbus Write Min",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_write_min",
            object_id="sigenergy2mqtt_modbus_write_min",
            unit="ms",
            icon="mdi:timer-minus-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_modbus_write_min
        if value == float("inf"):
            value = 0.0
        self.set_latest_state(value)
        return True


class ModbusActiveLocks(MetricsSensor):
    """Number of coroutines currently waiting to acquire a modbus lock."""

    def __init__(self):
        super().__init__(
            name="Modbus Active Locks",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_locks",
            object_id="sigenergy2mqtt_modbus_locks",
            icon="mdi:eye-lock",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = ModbusLockFactory.get_waiter_count()
        self.set_latest_state(value)
        return True


class Started(MetricsSensor):
    """ISO-8601 timestamp of when the service commenced, set at actual start time."""

    def __init__(self):
        super().__init__(
            name="Started",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_started",
            object_id="sigenergy2mqtt_started",
            device_class=DeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
        )
        self["entity_category"] = "diagnostic"

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_started
        self.set_latest_state(str(value) if value else "")
        return True


class ProtocolVersion(MetricsSensor):
    """The Sigenergy modbus protocol version in use."""

    def __init__(self, protocol_version: Protocol):
        super().__init__(
            name="Protocol Version",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_protocol",
            object_id="sigenergy2mqtt_modbus_protocol",
            icon="mdi:book-information-variant",
        )
        self["entity_category"] = "diagnostic"
        self.protocol_version = protocol_version

    async def _update_internal_state(self, **kwargs) -> bool:
        value = self.protocol_version.value
        self.set_latest_state(str(value))
        return True


class ProtocolPublished(MetricsSensor):
    """The date from which the active Sigenergy modbus protocol applies."""

    def __init__(self, protocol_version: Protocol):
        super().__init__(
            name="Protocol Published",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_modbus_protocol_published",
            object_id="sigenergy2mqtt_modbus_protocol_published",
            icon="mdi:book-clock",
        )
        self["entity_category"] = "diagnostic"
        self.protocol_version = protocol_version

    async def _update_internal_state(self, **kwargs) -> bool:
        value = ProtocolApplies(self.protocol_version)
        self.set_latest_state(str(value))
        return True


# InfluxDB Metrics Sensors


class InfluxDBWrites(MetricsSensor):
    """Cumulative count of InfluxDB write operations."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Writes",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_writes",
            object_id="sigenergy2mqtt_influxdb_writes",
            icon="mdi:database-arrow-up",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_influxdb_writes
        self.set_latest_state(new_state)
        return True


class InfluxDBWriteErrors(MetricsSensor):
    """Cumulative count of InfluxDB write errors."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Write Errors",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_write_errors",
            object_id="sigenergy2mqtt_influxdb_write_errors",
            icon="mdi:database-alert",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_influxdb_write_errors
        self.set_latest_state(new_state)
        return True


class InfluxDBWriteMax(MetricsSensor):
    """Maximum single InfluxDB write duration in milliseconds."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Write Max",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_write_max",
            object_id="sigenergy2mqtt_influxdb_write_max",
            unit="ms",
            icon="mdi:timer-plus-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_influxdb_write_max
        self.set_latest_state(value)
        return True


class InfluxDBWriteMean(MetricsSensor):
    """Mean InfluxDB write duration per write call, in milliseconds."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Write Mean",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_write_mean",
            object_id="sigenergy2mqtt_influxdb_write_mean",
            unit="ms",
            icon="mdi:timer-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_influxdb_write_mean
        self.set_latest_state(value)
        return True


class InfluxDBQueries(MetricsSensor):
    """Cumulative count of InfluxDB query operations."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Queries",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_queries",
            object_id="sigenergy2mqtt_influxdb_queries",
            icon="mdi:database-search",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_influxdb_queries
        self.set_latest_state(new_state)
        return True


class InfluxDBQueryErrors(MetricsSensor):
    """Cumulative count of InfluxDB query errors."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Query Errors",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_query_errors",
            object_id="sigenergy2mqtt_influxdb_query_errors",
            icon="mdi:database-alert-outline",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_influxdb_query_errors
        self.set_latest_state(new_state)
        return True


class InfluxDBRetries(MetricsSensor):
    """Cumulative count of InfluxDB retry attempts."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Retries",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_retries",
            object_id="sigenergy2mqtt_influxdb_retries",
            icon="mdi:reload",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_influxdb_retries
        self.set_latest_state(new_state)
        return True


class InfluxDBThroughput(MetricsSensor):
    """InfluxDB data points written per second since service start."""

    def __init__(self):
        super().__init__(
            name="InfluxDB Throughput",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_influxdb_throughput",
            object_id="sigenergy2mqtt_influxdb_throughput",
            icon="mdi:speedometer",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        elapsed = time.monotonic() - Metrics._started
        if elapsed > 0:
            value = Metrics.sigenergy2mqtt_influxdb_batch_total / elapsed
        else:
            value = 0.0
        self.set_latest_state(value)
        return True
