"""PSS (Power Storage System) device."""

from __future__ import annotations

import sigenergy2mqtt.sensors.pss_read_only as ro
import sigenergy2mqtt.sensors.pss_read_write as rw
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient


class PSS(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
        sequence_number: int | None = None,
        total_count: int | None = None,
    ):
        multi_pss = (total_count or 0) > 1 and sequence_number is not None
        name = "Sigenergy Packaged Substation System"
        sequence_suffix = str(sequence_number) if multi_pss else ""
        super().__init__(
            NonInverter(),
            name,
            plant_index,
            device_address,
            "PSS",
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
    ) -> "PSS":
        pss = cls(plant_index, device_address, protocol_version, sequence_number=sequence_number, total_count=total_count)
        await pss._register_sensors(plant_index, device_address, modbus_client)
        return pss

    async def _register_sensors(self, plant_index: int, device_address: int, modbus_client: ModbusClient) -> None:
        self._add_sensor(ro.PSSModelType(plant_index, device_address))
        self._add_sensor(ro.PSSSerialNumber(plant_index, device_address))
        self._add_sensor(ro.PSS_MVPhaseACurrent(plant_index, device_address))
        self._add_sensor(ro.PSS_MVPhaseBCurrent(plant_index, device_address))
        self._add_sensor(ro.PSS_MVPhaseCCurrent(plant_index, device_address))
        self._add_sensor(ro.PSS_MVFrequency(plant_index, device_address))
        self._add_sensor(ro.PSS_MVTemperature(plant_index, device_address))
        self._add_sensor(ro.PSS_LAPhaseAVoltage(plant_index, device_address))
        self._add_sensor(ro.PSS_LAPhaseAActivePower(plant_index, device_address))
        self._add_sensor(ro.PSS_LATotalActivePower(plant_index, device_address))
        self._add_sensor(ro.PSS_LATotalReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSS_LAFrequency(plant_index, device_address))

        self._add_sensor(rw.PSSMVCabinetG3CircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSMVCabinetG3CircuitBreakerSwitchOff(plant_index, device_address))
        self._add_sensor(rw.PSSLALowVoltageCabinetCircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSLALowVoltageCabinetCircuitBreakerSwitchOff(plant_index, device_address))
        self._add_sensor(rw.PSSLBLowVoltageCabinetCircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSLBLowVoltageCabinetCircuitBreakerSwitchOff(plant_index, device_address))
