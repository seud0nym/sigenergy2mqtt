from __future__ import annotations

import logging

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
        name = "Sigenergy PID Device"
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
        model = ro.PIDModelType(plant_index, device_address)
        serial = ro.PIDSerialNumber(plant_index, device_address)

        # Need to pre-populate model and serial number for modbus_test_server
        logging.debug(f"{self.log_identity} model={await model.get_state(modbus_client=modbus_client)} serial={await serial.get_state(modbus_client=modbus_client)}")

        self._add_sensor(model)
        self._add_sensor(serial)
        self._add_sensor(ro.PIDMachineFirmwareVersion(plant_index, device_address))
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
