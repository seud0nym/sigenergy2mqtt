"""
Sensor entities that expose :class:`~sigenergy2mqtt.config.Settings`
values over MQTT.
"""

import logging
from typing import Any, cast

from sigenergy2mqtt.common import DeviceClass, ProtocolVersion, ScanIntervalDefault, UnitOfTime
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import DiscoveryKeys, NumericSensorMixin, ReadableSensorMixin, SelectSensorMixin, SwitchSensorMixin, WriteableSensorMixin

logger = logging.getLogger(__name__)


# =============================================================================
# Base Settings Mixin for all sensors
# =============================================================================


class SettingsSensor(ReadableSensorMixin, WriteableSensorMixin):
    """Base class for all configuration sensors."""

    def __init__(
        self,
        **kwargs,
    ):
        self._setting = kwargs.pop("setting", 1)

        if not self._setting or self._setting.strip() == "":
            raise ValueError("No setting name provided")
        elif not self._setting.startswith("active_config.") or self._setting == "active_config.":
            raise ValueError(f"Invalid setting name: '{self._setting}' - must start with 'active_config.' and be followed by the name of a nested attribute of 'active_config'")

        hierarchy = self._setting.split(".")
        if len(hierarchy) < 2:
            raise ValueError(f"Invalid setting name: '{self._setting}' - must be a nested attribute of 'active_config'")
        elif len(hierarchy) > 3:
            raise ValueError(f"Invalid setting name: '{self._setting}' - must be a nested attribute of 'active_config' with at most 2 levels")
        elif len(hierarchy) == 2:
            self._parent = active_config
            self._attribute = hierarchy[1]
            object_id = f"sigenergy2mqtt_config_{hierarchy[1].lower()}"
            self._base_mqtt_topic = f"sigenergy2mqtt/config/{hierarchy[1].lower()}"
        else:
            self._parent = getattr(active_config, hierarchy[1])
            self._attribute = hierarchy[2]
            object_id = f"sigenergy2mqtt_config_{hierarchy[1].lower()}_{hierarchy[2].lower()}"
            self._base_mqtt_topic = f"sigenergy2mqtt/config/{hierarchy[1].lower()}/{hierarchy[2].lower()}"  # Classes below that set availability assume this is the MQTT topic format
        if not hasattr(self._parent, self._attribute):
            raise ValueError(f"Invalid setting name: '{self._setting}' - attribute '{self._attribute}' not found in '{self._parent}'")

        super().__init__(
            object_id=object_id,
            unique_id=object_id,
            scan_interval=ScanIntervalDefault.MEDIUM,
            protocol_version=ProtocolVersion.N_A,
            **kwargs,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def get_value(self) -> Any:
        """Get the current display value for this configuration setting."""
        val = getattr(self._parent, self._attribute)
        if callable(val):
            val = val()
        if isinstance(self, SwitchSensorMixin):
            return bool(val)
        return self._raw2state(cast(float | str, val))

    async def _update_internal_state(self, **kwargs) -> bool:
        state = getattr(self._parent, self._attribute)
        if callable(state):
            state = state()
        return self.set_latest_state(cast(float | str, state) if not isinstance(self, SwitchSensorMixin) else (1 if state else 0))

    async def _write_value(self, modbus_client, mqtt_client, value, source, handler) -> bool:
        logger.info(f"{self.log_identity} Updated '{self._setting}' to '{self._raw2state(value)}'")
        setattr(self._parent, self._attribute, value if not isinstance(self, SwitchSensorMixin) else bool(value))
        return True

    def _get_base_topic(self, device_id: str) -> str:
        """Use the configuration namespace for all sensor topics."""
        return self._base_mqtt_topic

    def publish_attributes(self, mqtt_client: Any, clean: bool = False, **kwargs) -> None:
        """Configuration sensors do not publish extra MQTT attributes."""


# =============================================================================
# Base Log Level Sensor
# =============================================================================


class LogLevelSensor(SettingsSensor, SelectSensorMixin):
    """Base class for all log level configuration sensors."""

    def __init__(
        self,
        setting: str,
        name: str,
        logger: str,
        unit: str | None = None,
        icon: str | None = "mdi:playlist-edit",
        precision: int | None = None,
        **kwargs,
    ):
        mapping = logging.getLevelNamesMapping()
        max_level = max(val for name, val in mapping.items() if name not in ("NOTSET", "WARN"))
        options = [next((name for name, val in mapping.items() if val == i and name not in ("NOTSET", "WARN")), "") for i in range(max_level + 1)]
        super().__init__(
            setting=setting,
            name=name,
            unit=unit,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon=icon,
            gain=None,
            precision=precision,
            options=options,
            **kwargs,
        )
        self._logger = logger
        self.publish_raw = True

    def apply_log_level(self, log_level: int) -> None:
        logging.getLogger(self._logger).setLevel(log_level)

    async def _write_value(self, modbus_client, mqtt_client, value, source, handler) -> bool:
        result = await super()._write_value(modbus_client, mqtt_client, value, source, handler)
        if result:
            self.apply_log_level(value)
        return result


# =============================================================================
# Concrete Log Level sensors
# =============================================================================


class ApplicationLogLevel(LogLevelSensor):
    def __init__(self):
        super().__init__(setting="active_config.log_level", name="Application Log Level", logger="sigenergy2mqtt")

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "The sigenergy2mqtt application logging level"
        return attributes


class DiagnosticsLogLevel(LogLevelSensor):
    def __init__(self):
        super().__init__(setting="active_config.diagnostics.log_level", name="Diagnostics Log Level", logger="sigenergy2mqtt.diagnostics")

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "The sigenergy2mqtt diagnostics module logging level"
        return attributes


class InfluxDBLogLevel(LogLevelSensor):
    def __init__(self):
        super().__init__(setting="active_config.influxdb.log_level", name="InfluxDB Log Level", logger="sigenergy2mqtt.influxdb")

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "The InfluxDB interface logging level"
        return attributes


class PVOutputLogLevel(LogLevelSensor):
    def __init__(self):
        super().__init__(setting="active_config.pvoutput.log_level", name="PVOutput Log Level", logger="sigenergy2mqtt.pvoutput")

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "The PVOutput interface logging level"
        return attributes


class PVOutputUploadLogLevel(LogLevelSensor):
    def __init__(self):
        super().__init__(setting="active_config.pvoutput.upload_log_level", name="PVOutput Upload Log Level", logger="sigenergy2mqtt.pvoutput")

    def apply_log_level(self, log_level: int) -> None:
        logging.getLogger(self._logger).debug(f"{self.log_identity} active_config.pvoutput.upload_log_level set to '{logging.getLevelName(log_level)}' - logger level has NOT been updated as per documentation")

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = (
            "The PVOutput upload payload logging level. If the overall PVOutput Log Level is set to a level higher than the level specified for this option (e.g. this option is set to INFO and PVOutput Log Level is set to WARNING), then the upload log messages will be suppressed."
        )
        return attributes


class ModbusLogLevel(LogLevelSensor):
    def __init__(self):
        super().__init__(setting="active_config.modbus_log_level", name="Modbus Log Level", logger="pymodbus.logging")
        self._base_mqtt_topic = "sigenergy2mqtt/config/modbus/log_level"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "The Modbus interface logging level"
        return attributes


class MQTTLogLevel(LogLevelSensor):
    def __init__(self):
        super().__init__(setting="active_config.mqtt.log_level", name="MQTT Log Level", logger="paho.mqtt")

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "The MQTT interface logging level"
        return attributes


# =============================================================================
# Numeric sensors
# =============================================================================


class RepeatedStatePublishInterval(SettingsSensor, NumericSensorMixin):
    def __init__(self):
        super().__init__(
            setting="active_config.repeated_state_publish_interval",
            name="Repeated State Publish Interval",
            unit=UnitOfTime.SECONDS,
            device_class=DeviceClass.DURATION,
            state_class=None,
            icon="mdi:publish",
            precision=0,
            gain=None,
            minimum=-1,
            maximum=600,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = (
            "The interval in seconds at which repeated states are published. (Repeated states occur when the state that is acquired is identical to the previous read.) <0=Never 0=Always >0=Interval"
        )
        return attributes


# =============================================================================
# Switch sensors
# =============================================================================


class PersistenceDebugging(SettingsSensor, SwitchSensorMixin):
    def __init__(self):
        super().__init__(
            setting="active_config.persistence.debug",
            name="Persistence Debugging",
            icon="mdi:toggle-switch",
            unit=None,
            device_class=None,
            state_class=None,
            precision=None,
            gain=None,
        )

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if active_config.home_assistant.enabled:
            cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY]).append({
                "topic": "sigenergy2mqtt/config/log_level/state",
                "value_template": "{{ 'online' if value == 'DEBUG' else 'offline' }}",
            })
        return base

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Enable debugging of all state store (persistence) operations"
        return attributes


class PVOutputCalcDebugLogging(SettingsSensor, SwitchSensorMixin):
    def __init__(self):
        super().__init__(
            setting="active_config.pvoutput.calc_debug_logging",
            name="PVOutput Value Calculation Debugging",
            icon="mdi:calculator",
            unit=None,
            device_class=None,
            state_class=None,
            precision=None,
            gain=None,
        )

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if active_config.home_assistant.enabled:
            cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY]).append({
                "topic": "sigenergy2mqtt/config/pvoutput/log_level/state",
                "value_template": "{{ 'online' if value == 'DEBUG' else 'offline' }}",
            })
        return base

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If enabled the aggregation of values for uploading to PVOutput will be logged at the `DEBUG` level.  Only applicable if the PVOutput Log Level is set to DEBUG."
        return attributes


class PVOutputUpdateDebugLogging(SettingsSensor, SwitchSensorMixin):
    def __init__(self):
        super().__init__(
            setting="active_config.pvoutput.update_debug_logging",
            name="PVOutput Value Update Debugging",
            icon="mdi:toggle-switch",
            unit=None,
            device_class=None,
            state_class=None,
            precision=None,
            gain=None,
        )

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if active_config.home_assistant.enabled:
            cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY]).append({
                "topic": "sigenergy2mqtt/config/pvoutput/log_level/state",
                "value_template": "{{ 'online' if value == 'DEBUG' else 'offline' }}",
            })
        return base

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If enabled the updating of values for uploading to PVOutput will be logged at the DEBUG level. Only applicable if PVOutput Log Level is set to DEBUG."
        return attributes


class SanityCheckFailuresIncrement(SettingsSensor, SwitchSensorMixin):
    def __init__(self):
        super().__init__(
            setting="active_config.sanity_check_failures_increment",
            name="Sanity Check Failures Increment",
            icon="mdi:counter",
            unit=None,
            device_class=None,
            state_class=None,
            precision=None,
            gain=None,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = (
            "If enabled, the number of sensor read failures will be incremented when a sanity check fails. If sensor read failures pass the allowed threshold for errors, the sensor will be disabled until the next restart."
        )
        return attributes
