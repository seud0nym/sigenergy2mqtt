"""PID (Power Inverter Device) device."""

from __future__ import annotations

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
        sequence_number: int | None = None,
        total_count: int | None = None,
    ):
        multi_pid = (total_count or 0) > 1 and sequence_number is not None
        name = "Sigenergy Potential Induced Degradation Device"
        sequence_suffix = str(sequence_number) if multi_pid else ""
        super().__init__(
            NonInverter(),
            name,
            plant_index,
            device_address,
            "PID",
            protocol_version,
            sequence_number=sequence_number,
            sequence_suffix=sequence_suffix,
        )

    @classmethod
    async def create(
        cls,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
        modbus_client: ModbusClient,
        sequence_number: int | None = None,
        total_count: int | None = None,
    ) -> "PID":
        pid = cls(plant_index, device_address, protocol_version, sequence_number=sequence_number, total_count=total_count)
        await pid._register_sensors(plant_index, device_address, modbus_client)
        return pid

    async def _register_sensors(self, plant_index: int, device_address: int, modbus_client: ModbusClient) -> None:
        self._add_sensor(ro.PIDModelType(plant_index, device_address))
        self._add_sensor(ro.PIDSerialNumber(plant_index, device_address))
        self._add_sensor(ro.PIDMachineFirmwareVersion(plant_index, device_address))
        self._add_sensor(ro.PIDCommunicationStatus(plant_index, device_address))
        self._add_sensor(ro.PIDRunningStatus(plant_index, device_address))
        self._add_sensor(ro.PID_ABLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_BCLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_CALineVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_PhaseAVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_PhaseBVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_PhaseCVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_GridFrequency(plant_index, device_address))
        self._add_sensor(ro.PID_OutputVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_BusVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_InverterVoltage(plant_index, device_address))
        self._add_sensor(ro.PID_InverterCurrent(plant_index, device_address))
        self._add_sensor(ro.PID_OutputCurrent(plant_index, device_address))
        self._add_sensor(ro.PID_InternalTemperature1(plant_index, device_address))
        self._add_sensor(ro.PID_InternalTemperature2(plant_index, device_address))
        self._add_sensor(ro.PID_InternalTemperature3(plant_index, device_address))
        self._add_sensor(ro.PID_InternalTemperature4(plant_index, device_address))
        self._add_sensor(ro.PID_InternalTemperature5(plant_index, device_address))

        self._add_sensor(rw.PIDStartStop(plant_index, device_address))
