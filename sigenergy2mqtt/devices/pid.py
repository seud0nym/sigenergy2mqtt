from __future__ import annotations

import asyncio
from typing import cast

import sigenergy2mqtt.sensors.pid_read_only as ro
import sigenergy2mqtt.sensors.pid_read_write as rw
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient


class PID(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
        model_id: str,
        serial: str,
        firmware: str,
    ):
        super().__init__(
            NonInverter(),
            name=f"{model_id} {serial}",
            plant_index=plant_index,
            device_address=device_address,
            model=model_id,
            protocol_version=protocol_version,
            # HA device registry attributes
            sn=serial,
            hw=firmware,  # MUST use hw abbreviation - see InverterFirmwareVersion
            model_id=model_id,
            serial=serial,
        )

    @classmethod
    async def create(cls, plant_index: int, device_address: int, protocol_version: Protocol, modbus_client: ModbusClient) -> "PID":
        model = ro.PIDModelType(plant_index, device_address)
        firmware_version = ro.PIDMachineFirmwareVersion(plant_index, device_address)
        serial_number = ro.PIDSerialNumber(plant_index, device_address)

        # Fetch async values in parallel for common inverter sensors
        firmware, model_id, serial = await asyncio.gather(
            firmware_version.get_state(modbus_client=modbus_client),
            model.get_state(modbus_client=modbus_client),
            serial_number.get_state(modbus_client=modbus_client),
        )

        pid = cls(plant_index, device_address, protocol_version, cast(str, model_id), cast(str, serial), cast(str, firmware))
        await pid._register_sensors(plant_index, device_address, model, firmware_version, serial_number)
        return pid

    async def _register_sensors(self, plant_index: int, device_address: int, model: ro.PIDModelType, firmware_version: ro.PIDMachineFirmwareVersion, serial_number: ro.PIDSerialNumber) -> None:
        self._add_sensor(model)
        self._add_sensor(serial_number)
        self._add_sensor(firmware_version)
        self._add_sensor(ro.PIDCommunicationStatus(plant_index, device_address))
        self._add_sensor(ro.PIDRunningStatus(plant_index, device_address))
        self._add_sensor(ro.PIDABLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDBCLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDCALineVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDPhaseAVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDPhaseBVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDPhaseCVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDGridFrequency(plant_index, device_address))
        self._add_sensor(ro.PIDOutputVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDBusVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDInverterVoltage(plant_index, device_address))
        self._add_sensor(ro.PIDInverterCurrent(plant_index, device_address))
        self._add_sensor(ro.PIDOutputCurrent(plant_index, device_address))
        self._add_sensor(ro.PIDInternalTemperature1(plant_index, device_address))
        self._add_sensor(ro.PIDInternalTemperature2(plant_index, device_address))
        self._add_sensor(ro.PIDInternalTemperature3(plant_index, device_address))
        self._add_sensor(ro.PIDInternalTemperature4(plant_index, device_address))
        self._add_sensor(ro.PIDInternalTemperature5(plant_index, device_address))

        a1 = ro.PIDAlarm1(plant_index, device_address)
        a2 = ro.PIDAlarm2(plant_index, device_address)
        self._add_sensor(a1)
        self._add_sensor(a2)
        self._add_sensor(ro.PIDAlarms(plant_index, device_address, a1, a2))

        self._add_sensor(rw.PIDStartStop(plant_index, device_address))
