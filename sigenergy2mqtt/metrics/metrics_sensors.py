import logging
import time
from typing import Any, cast

from sigenergy2mqtt.common import Protocol, ProtocolApplies
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.modbus import ModbusLockFactory
from sigenergy2mqtt.sensors.base import ReadableSensorMixin
from sigenergy2mqtt.sensors.const import PERCENTAGE, DeviceClass

from .metrics import Metrics


class MetricsSensor(ReadableSensorMixin):
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
        pass


class ModbusCacheHits(MetricsSensor):
    def __init__(self):
        super().__init__(
            name="Modbus Cache Hits",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_cache_hit_percentage",
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
    def __init__(self):
        super().__init__(
            name="Modbus Physical Reads",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_physical_reads",
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
    def __init__(self):
        super().__init__(
            name="Modbus Reads/second",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_reads_sec",
            object_id="sigenergy2mqtt_modbus_reads_sec",
            icon="mdi:timer-play-outline",
            precision=2,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = Metrics.sigenergy2mqtt_modbus_register_reads / (time.monotonic() - Metrics._started)
        self.set_latest_state(value)
        return True


class ModbusReadErrors(MetricsSensor):
    def __init__(self):
        super().__init__(
            name="Modbus Read Errors",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_read_errors",
            object_id="sigenergy2mqtt_modbus_read_errors",
            icon="mdi:counter",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_modbus_read_errors
        self.set_latest_state(new_state)
        return True


class ModbusReadMax(MetricsSensor):
    def __init__(self):
        super().__init__(
            name="Modbus Read Max",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_read_max",
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
    def __init__(self):
        super().__init__(
            name="Modbus Read Mean",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_read_mean",
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
    def __init__(self):
        super().__init__(
            name="Modbus Read Min",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_read_min",
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
    def __init__(self):
        super().__init__(
            name="Modbus Write Errors",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_write_errors",
            object_id="sigenergy2mqtt_modbus_write_errors",
            icon="mdi:counter",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        new_state = Metrics.sigenergy2mqtt_modbus_write_errors
        self.set_latest_state(new_state)
        return True


class ModbusWriteMax(MetricsSensor):
    def __init__(self):
        super().__init__(
            name="Modbus Write Max",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_write_max",
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
    def __init__(self):
        super().__init__(
            name="Modbus Write Mean",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_write_mean",
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
    def __init__(self):
        super().__init__(
            name="Modbus Write Min",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_write_min",
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
    def __init__(self):
        super().__init__(
            name="Modbus Active Locks",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_locks",
            object_id="sigenergy2mqtt_modbus_locks",
            icon="mdi:eye-lock",
            precision=0,
        )

    async def _update_internal_state(self, **kwargs) -> bool:
        value = ModbusLockFactory.get_waiter_count()
        self.set_latest_state(value)
        return True


class Started(MetricsSensor):
    def __init__(self):
        super().__init__(
            name="Started",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_started",
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
    def __init__(self, protocol_version: Protocol):
        super().__init__(
            name="Protocol Version",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_protocol",
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
    def __init__(self):
        super().__init__(
            name="Protocol Published",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_modbus_protocol_published",
            object_id="sigenergy2mqtt_modbus_protocol_published",
            icon="mdi:book-clock",
        )
        self["entity_category"] = "diagnostic"

    async def _update_internal_state(self, **kwargs) -> bool:
        value = ProtocolApplies(self.protocol_version)
        self.set_latest_state(str(value))
        return True
