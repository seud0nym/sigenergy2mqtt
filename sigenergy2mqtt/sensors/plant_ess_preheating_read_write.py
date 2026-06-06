from __future__ import annotations

import logging
from abc import ABC
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import Constants, Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

from sigenergy2mqtt.common import PERCENTAGE, DeviceClass, HybridInverter, InputType, UnitOfPower, UnitOfTime
from sigenergy2mqtt.sensors.base import AvailabilityMixin, DiscoveryKeys, NumericSensor, ScanInterval, SelectSensor, SwitchSensor


class ESSPreHeatingEnable(SwitchSensor, HybridInverter):
    ADDRESS = 50000

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Preheating",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_enable",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            protocol_version=Protocol.V2_9,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0: Disable, 1: Enable"
        return attributes


class ESSPreHeatingMode(SelectSensor, AvailabilityMixin, HybridInverter):
    ADDRESS = 50001

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Preheating Mode",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_mode",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            options=[
                "Automatic",  # 0
                "Manual",  # 1
            ],
            protocol_version=Protocol.V2_9,
        )
        self.publish_raw = True  # Always publish raw value for Advance availability control

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0: Automatic, 1: Manual"
        return attributes


class ESSPreHeatingAdvanceEnable(SwitchSensor, HybridInverter):
    ADDRESS = 50002

    def __init__(self, plant_index: int, preheating_mode: ESSPreHeatingMode):
        super().__init__(
            availability_control_sensor=preheating_mode,
            name="Preheating Advance",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_advance_enable",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            protocol_version=Protocol.V2_9,
        )
        self._use_raw_for_availability = True  # Use raw value of Preheating Mode for availability control

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0: Disable, 1: Enable. Takes effect when Preheating Mode is Manual."
        return attributes

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and self._availability_control_sensor.latest_raw_state == 0:
            logging.error(
                f"{self.log_identity} Failed to write value '{raw_value}': {self._availability_control_sensor.name} is set to Automatic mode, so cannot enable Advance. Set Preheating Mode to Manual first."
            )
            return False
        return await super().value_is_valid(modbus_client, raw_value)


class ESSPreHeatingTOUTime(NumericSensor, HybridInverter, ABC):
    """Base class for ESS Pre-Heating TOU start/end time sensors.

    Represents time in epoch seconds with timezone offset applied.

    The device will interpret the value as local time based on its timezone setting,
    so the same value may correspond to different actual times depending on the
    device's timezone configuration.
    """

    def __init__(self, plant_index: int, slot: int, name: str, icon: str, address: int):
        self.slot = slot
        super().__init__(
            availability_control_sensor=None,
            name=name,
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_{name.lower().replace(' ', '_')}",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfTime.SECONDS,
            device_class=None,
            state_class=None,
            icon=icon,
            gain=1,
            precision=0,
            protocol_version=Protocol.V2_9,
            slot=slot,
        )
        self[DiscoveryKeys.PLATFORM] = "time"

    def _raw2state(self, raw_value: float | int | str) -> float | int | str:
        if isinstance(raw_value, (float, int)):
            return datetime.strftime(datetime.fromtimestamp(raw_value, timezone.utc), "%H:%M:%S")
        return super()._raw2state(raw_value)

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Epoch seconds with timezone; local time interpretation depends on the device."
        return attributes

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get state as parseable time string.

        Args:
            raw: If True, return raw Unix timestamp
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            formatted time or raw value
        """
        value = cast(float, await super().get_state(raw=raw, republish=republish, **kwargs))

        if raw or value is None:
            return value

        dt = datetime.fromtimestamp(value, timezone.utc)  # Target data type is UINT32, so need to convert to UTC to prevent negative numbers caused by positive timezone offsets
        state = dt.strftime("%H:%M:%S")

        if self.debug_logging:
            logging.debug(f"{self.log_identity} get_state raw={value} {dt=} {state=}")

        return state

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        epoch = cast(int, self.state2raw(value))
        return await super().set_value(modbus_client, mqtt_client, epoch, source, handler)

    def state2raw(self, state: float | int | str) -> float | int | str | None:
        """Convert time string back to Unix epoch value.

        Args:
            state: Parseable time string or Unix timestamp

        Returns:
            Unix epoch value
        """
        if state is None:
            return None

        if isinstance(state, (float, int)):
            return int(state)

        dt = datetime.strptime("01-01-1970 " + state + " +0000", "%d-%m-%Y %H:%M:%S %z")  # Target data type is UINT32, so need to convert to UTC to prevent negative numbers caused by positive timezone offsets
        ts = dt.timestamp()
        value = int(ts // 60) * 60  # Remove seconds (whole minutes only)

        logging.info(f"{self.log_identity} state2raw {state=} {dt=} {ts=} raw={value=} (seconds removed)")

        return value


class ESSPreHeatingTOUTimeStart(ESSPreHeatingTOUTime):
    def __init__(self, plant_index: int, slot: int, address: int):
        super().__init__(plant_index, slot, f"TOU {slot} Start", "mdi:clock-start", address)


class ESSPreHeatingTOUTimeEnd(ESSPreHeatingTOUTime):
    def __init__(self, plant_index: int, slot: int, address: int):
        super().__init__(plant_index, slot, f"TOU {slot} End", "mdi:clock-end", address)


class ESSPreHeatingTOUTargetPower(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, slot: int, address: int, rated_charging_power: float, rated_discharging_power: float):
        self.slot = slot
        super().__init__(
            availability_control_sensor=None,
            name=f"TOU {slot} Target Charging/Discharging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_tou_{slot}_target_power",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
            min=-rated_discharging_power,
            max=rated_charging_power,
            slot=slot,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "<0: discharging, >0: charging"
        return attributes


class ESSPreHeatingReservedSOC(NumericSensor, HybridInverter):
    ADDRESS = 50183

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Preheating Reserved SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_reserved_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=100,
            precision=None,
            protocol_version=Protocol.V2_9,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes
