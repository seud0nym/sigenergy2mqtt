"""Alarm sensors and RunningStateSensor."""

from __future__ import annotations

import abc
import logging
import re
import sys
from typing import Any, Final, cast

from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import DeviceClass, HybridInverter, InputType, Protocol, PVInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusDataType

from .constants import DiscoveryKeys
from .readable import ReadOnlySensor

# =============================================================================


class AlarmSensor(ReadOnlySensor, metaclass=abc.ABCMeta):
    """Base class for alarm/fault sensors.

    Alarm sensors decode bit-field values into human-readable alarm descriptions.
    """

    NO_ALARM: Final = "No Alarm"

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
        alarm_type: str,
        **kwargs,
    ):
        super().__init__(
            name,
            object_id,
            InputType.INPUT,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=(active_config.modbus[plant_index].scan_interval.realtime if plant_index < len(active_config.modbus) else 5),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )
        self.alarm_type = alarm_type

    @abc.abstractmethod
    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode an alarm bit position to description.

        Args:
            bit_position: The bit position (0-15) in the alarm register

        Returns:
            Alarm description or None if bit is not used
        """
        pass

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get alarm state as human-readable string.

        Args:
            raw: If True, return raw alarm code
            republish: If True, return last known state
            **kwargs: May contain 'max_length' for truncation

        Returns:
            Alarm description or NO_ALARM
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)

        if raw:
            return value

        # Treat None as no alarm
        if value is None:
            return _t("AlarmSensor.no_alarm", self.NO_ALARM, self.debug_logging)

        # Check for no alarm conditions
        if self._is_no_alarm(value):
            return _t("AlarmSensor.no_alarm", self.NO_ALARM, self.debug_logging)

        # Decode alarm bits
        alarm_code = self._normalize_alarm_code(value)
        active_alarms = self._decode_alarm_bits(alarm_code, value)

        if not active_alarms:
            return f"Unknown Alarm {value}"

        # Join alarms and truncate if needed
        alarms = ", ".join(active_alarms)
        return self._truncate_alarms(alarms, kwargs.get("max_length"))

    def _is_no_alarm(self, value: float | int | str | list | None) -> bool:
        """Check if value represents no alarm condition.

        Args:
            value: Alarm value to check

        Returns:
            True if no alarm
        """
        if value is None or value == 0 or value == 65535:
            return True

        if isinstance(value, list):
            return sum(cast(list[int], value)) == 0

        return False

    def _normalize_alarm_code(self, value: float | int | str) -> int:
        """Normalize alarm value to integer code.

        Args:
            value: Raw alarm value

        Returns:
            Normalized alarm code
        """
        if isinstance(value, list) and len(value) == 2 and value[0] == 0 and value[1] != 0:
            logging.warning(f"{self.log_identity} Converting '{value}' to {value[1]} for {self.alarm_type} alarm bit decoding")
            return int(value[1])

        return int(value)

    def _decode_alarm_bits(self, alarm_code: int, original_value: Any) -> list[str]:
        """Decode individual alarm bits to descriptions.

        Args:
            alarm_code: Normalized alarm code
            original_value: Original value for error reporting

        Returns:
            List of active alarm descriptions
        """
        active_alarms = []

        try:
            for bit_position in range(16):
                if alarm_code & (1 << bit_position):
                    description = self.decode_alarm_bit(bit_position)

                    if description:
                        translated = _t(f"{self.__class__.__name__}.alarm.{bit_position}", description, self.debug_logging)
                        active_alarms.append(translated)
                    else:
                        unknown = _t("AlarmSensor.unknown_alarm", "Unknown (bit{bit}∈{value})", self.debug_logging).format(bit=bit_position, value=original_value)
                        active_alarms.append(unknown)
                        logging.warning(f"{self.log_identity} Unknown {self.alarm_type} alarm bit {bit_position} set in value {original_value}")
        except TypeError as e:
            logging.warning(f"{self.log_identity} Failed to decode {self.alarm_type} alarm bits from '{original_value}': {e}")

        return active_alarms

    def _truncate_alarms(self, alarms: str, max_length: int | None) -> str:
        """Truncate alarm string if needed for Home Assistant.

        Args:
            alarms: Joined alarm descriptions
            max_length: Maximum length (default 255)

        Returns:
            Possibly truncated alarm string
        """
        if not active_config.home_assistant.enabled:
            return alarms

        max_len = 255 if not max_length or max_length <= 0 else max_length

        if len(alarms) <= max_len:
            return alarms

        # Remove numbers, colons, underscores and collapse whitespace
        compressed = re.sub(r"\s+", " ", re.sub(r"[0-9:_]", "", alarms)).strip()

        if len(compressed) <= max_len:
            return compressed

        return compressed[: (max_len - 3)] + "..."

    def state2raw(self, state: float | int | str) -> float | int | str | None:
        """Convert alarm description back to code.

        Args:
            state: Alarm description string

        Returns:
            Alarm code (0 for NO_ALARM)
        """
        if state == AlarmSensor.NO_ALARM:
            return 0
        return super().state2raw(state)


# =============================================================================
# Specific Alarm Sensor Implementations
# =============================================================================


class Alarm1Sensor(AlarmSensor):
    """PCS (Power Conversion System) alarms - Register 1."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "PCS")

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode PCS alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Low insulation resistance",
            2: "Over-temperature",
            3: "Equipment fault",
            4: "System grounding fault",
            5: "PV string over-voltage",
            6: "PV string reversely connected",
            7: "PV string back-filling",
            8: "AFCI fault",
            9: "Grid power outage",
            10: "Grid over-voltage",
            11: "Grid under-voltage",
            12: "Grid over-frequency",
            13: "Grid under-frequency",
            14: "Grid voltage imbalance",
            15: "DC component of output current out of limit",
        }
        return alarm_descriptions.get(bit_position)


class Alarm2Sensor(AlarmSensor):
    """PCS (Power Conversion System) alarms - Register 2."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "PCS")

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode PCS alarm bits - second register."""
        alarm_descriptions = {
            0: "Leak current out of limit",
            1: "Communication abnormal",
            2: "System internal protection",
            3: "AFCI self-checking circuit fault",
            4: "Off-grid protection",
            5: "Manual operation protection",
            7: "Abnormal phase sequence",
            8: "Short circuit to PE",
            9: "Soft start failure",
        }
        return alarm_descriptions.get(bit_position)


class Alarm3Sensor(AlarmSensor):
    """ESS (Energy Storage System) alarms."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "ESS")
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode ESS alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Low insulation resistance to ground",
            2: "Temperature too high",
            3: "Equipment fault",
            4: "Under-temperature",
            5: "Internal protection",
            6: "Thermal runaway",
        }
        return alarm_descriptions.get(bit_position)


class Alarm4Sensor(AlarmSensor):
    """Gateway alarms."""

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
    ):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "GW")
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode Gateway alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Temperature too high",
            2: "Equipment fault",
            3: "Excessive leakage current in off-grid output",
            4: "N line grounding fault",
            5: "Abnormal phase sequence of grid wiring",
            6: "Abnormal phase sequence of inverter wiring",
            7: "Grid phase loss",
        }
        return alarm_descriptions.get(bit_position)


class Alarm5Sensor(AlarmSensor):
    """EV DC Charger alarms."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "EVDC")
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode DC Charger alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Low insulation resistance to ground",
            2: "Over-temperature",
            3: "Equipment fault",
            4: "Charging fault",
            5: "Equipment protection",
        }
        return alarm_descriptions.get(bit_position)


# =============================================================================
# Combined Alarm Sensor
# =============================================================================


class AlarmCombinedSensor(ReadOnlySensor, HybridInverter, PVInverter):
    """Combines multiple alarm sensors into a single view.

    Reads all alarm registers and combines active alarms into one string.
    """

    def __init__(self, name: str, unique_id: str, object_id: str, *alarms: AlarmSensor, **kwargs):
        # Validate alarm sensors
        if not alarms:
            raise ValueError(f"{self.log_identity}: At least one alarm sensor required")

        device_addresses = set(a.device_address for a in alarms)
        if len(device_addresses) != 1:
            raise ValueError(f"{self.log_identity}: All alarms must have same device address (found {device_addresses})")

        # Calculate address range
        first_address = min(a.address for a in alarms)
        last_address = max(a.address + a.count - 1 for a in alarms)
        count = sum(a.count for a in alarms)

        if (last_address - first_address + 1) != count:
            raise ValueError(f"{self.log_identity}: Alarms must have contiguous address ranges (addresses: {[a.address for a in alarms]})")

        self.alarms = list(alarms)
        plant_index: int = kwargs.pop("plant_index", self.alarms[0].plant_index)

        # Remove conflicting kwargs
        kwargs.pop("input_type", None)
        kwargs.pop("device_address", None)
        kwargs.pop("address", None)
        kwargs.pop("count", None)
        kwargs.pop("unique_id_override", None)

        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            scan_interval=min(a.scan_interval for a in alarms),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
            protocol_version=Protocol.N_A,
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=list(device_addresses)[0],
            data_type=ModbusDataType.STRING,
            address=first_address,
            count=count,
            unique_id_override=unique_id,
            **kwargs,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    @property
    def protocol_version(self) -> Protocol:
        """Get the highest protocol version from all alarms."""
        protocol = super().protocol_version
        for alarm in self.alarms:
            if alarm.protocol_version > protocol:
                protocol = alarm.protocol_version
        return protocol

    @protocol_version.setter
    def protocol_version(self, protocol_version: Protocol | float):
        """Protocol version is read-only for combined sensors."""
        raise NotImplementedError("protocol_version is read-only for AlarmCombinedSensor")

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        """Combined sensor doesn't update - it reads from sub-sensors."""
        return True

    def configure_mqtt_topics(self, device_id: str) -> str:
        """Configure topics for combined sensor and all alarm sensors.

        Args:
            device_id: The device identifier

        Returns:
            Base topic path
        """
        base = super().configure_mqtt_topics(device_id)

        # Configure topics for all alarm sensors
        for alarm in self.alarms:
            alarm.configure_mqtt_topics(device_id)

        return base

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get combined alarm state from all alarm sensors.

        Args:
            raw: If True, return raw value
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            Combined alarm string
        """
        if republish and len(self._states) > 0:
            state = self._states[-1][1]
            return self._apply_gain_and_precision(state, raw) if isinstance(state, (float, int)) else state

        no_alarm = _t("AlarmSensor.no_alarm", AlarmSensor.NO_ALARM, self.debug_logging)
        result: str = no_alarm

        # Collect alarms from all publishable sensors
        for alarm in (a for a in self.alarms if a.publishable):
            state = cast(str, await alarm.get_state(raw=False, republish=False, max_length=sys.maxsize, **kwargs))

            if state != no_alarm:
                result = state if result == no_alarm else f"{result}, {state}"

                # Truncate if needed for Home Assistant
                if len(result) > 255 and active_config.home_assistant.enabled:
                    result = self._compress_alarm_string(result)

        self.set_state(result)
        return result

    def _compress_alarm_string(self, alarms: str) -> str:
        """Compress alarm string to fit Home Assistant limit.

        Args:
            alarms: Combined alarm string

        Returns:
            Compressed string under 255 characters
        """
        compressed = re.sub(r"\s+", " ", re.sub(r"[0-9:_]", "", alarms)).strip()

        if len(compressed) > 255:
            compressed = compressed[:252] + "..."

        return compressed

    def state2raw(self, state: float | int | str) -> float | int | str | None:
        """Convert alarm state back to code.

        Args:
            state: Alarm description

        Returns:
            0 for NO_ALARM, otherwise pass through
        """
        if state == AlarmSensor.NO_ALARM:
            return 0
        return super().state2raw(state)


# =============================================================================
# Running State Sensor
# =============================================================================


class RunningStateSensor(ReadOnlySensor):
    """Sensor for device running state/status."""

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
        **kwargs,
    ):
        super().__init__(
            name,
            object_id,
            InputType.INPUT,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=(active_config.modbus[plant_index].scan_interval.high if plant_index < len(active_config.modbus) else 10),
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:power-settings",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )

        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True
        self[DiscoveryKeys.OPTIONS] = [
            "Standby",  # 0
            "Normal",  # 1
            "Fault",  # 2
            "Power-Off",  # 3
            "",  # 4
            "",  # 5
            "",  # 6
            "Environmental Abnormality",  # 7
        ]

        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get running state as string.

        Args:
            raw: If True, return raw state code
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            State description or "Unknown State code: X"
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)

        if raw or value is None:
            return value

        if isinstance(value, (float, int)):
            option = self._get_option(int(value))
            if option:
                return option
            return f"Unknown State code: {value}"

        return f"Unknown State code: {value}"


# =============================================================================
# Resettable Accumulation Sensor
