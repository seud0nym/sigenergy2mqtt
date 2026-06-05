from __future__ import annotations

import asyncio
from typing import cast

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
        model_id: str,
        serial: str,
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
            model_id=model_id,
            serial=serial,
        )

    @classmethod
    async def create(cls, plant_index: int, device_address: int, protocol_version: Protocol, modbus_client: ModbusClient) -> "PSS":
        model = ro.PSSModelType(plant_index, device_address)
        serial_number = ro.PSSSerialNumber(plant_index, device_address)

        # Fetch async values in parallel for common inverter sensors
        model_id, serial = await asyncio.gather(
            model.get_state(modbus_client=modbus_client),
            serial_number.get_state(modbus_client=modbus_client),
        )

        pss = cls(plant_index, device_address, protocol_version, cast(str, model_id), cast(str, serial))
        await pss._register_sensors(plant_index, device_address, model, serial_number)
        return pss

    async def _register_sensors(self, plant_index: int, device_address: int, model: ro.PSSModelType, serial_number: ro.PSSSerialNumber) -> None:
        self._add_sensor(model)
        self._add_sensor(serial_number)
        self._add_sensor(ro.PSSCommunicationStatus(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication1(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication2(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication3(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication4(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication5(plant_index, device_address))
        self._add_sensor(ro.PSSMVPhaseACurrent(plant_index, device_address))
        self._add_sensor(ro.PSSMVPhaseBCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSMVPhaseCCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSMVZeroSequenceCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSMVFrequency(plant_index, device_address))
        self._add_sensor(ro.PSSMVTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVHumidity(plant_index, device_address))
        self._add_sensor(ro.PSSMVG1CableL1PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG1CableL2PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG1CableL3PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG2CableL1PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG2CableL2PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG2CableL3PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG3CableL1PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG3CableL2PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSMVG3CableL3PhaseTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSLATemperature(plant_index, device_address))
        self._add_sensor(ro.PSSLAHumidity(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseAVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseBVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseCVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLAABLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLABCLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLACALineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseACurrent(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseBCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseCCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseAActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseBActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseCActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLATotalActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseAReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseBReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseCReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLATotalReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseAApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseBApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseCApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLATotalApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseAPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseBPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLAPhaseCPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLATotalPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLAFrequency(plant_index, device_address))
        self._add_sensor(ro.PSSLAForwardActiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSLAReverseActiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSLAForwardReactiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSLAReverseReactiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSLBTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSLBHumidity(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseAVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseBVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseCVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLBABLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLBBCLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLBCALineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseACurrent(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseBCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseCCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseAActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseBActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseCActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBTotalActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseAReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseBReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseCReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBTotalReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseAApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseBApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseCApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLBTotalApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseAPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseBPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLBPhaseCPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLBTotalPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSLBFrequency(plant_index, device_address))
        self._add_sensor(ro.PSSLBForwardActiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSLBReverseActiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSLBForwardReactiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSLBReverseReactiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSTransformerOilSurfaceTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSTransformerWindingTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetHumidity(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseAVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseBVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseCVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetABLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetBCLineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetCALineVoltage(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseACurrent(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseBCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseCCurrent(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseAActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseBActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseCActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetTotalActivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseAReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseBReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseCReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetTotalReactivePower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseAApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseBApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseCApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetTotalApparentPower(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseAPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseBPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetPhaseCPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetTotalPowerFactor(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetFrequency(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetForwardActiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetReverseActiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetForwardReactiveEnergy(plant_index, device_address))
        self._add_sensor(ro.PSSDistributionCabinetReverseReactiveEnergy(plant_index, device_address))

        self._add_sensor(rw.PSSMVCabinetG3CircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSMVCabinetG3CircuitBreakerSwitchOff(plant_index, device_address))
        self._add_sensor(rw.PSSLALowVoltageCabinetCircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSLALowVoltageCabinetCircuitBreakerSwitchOff(plant_index, device_address))
        self._add_sensor(rw.PSSLBLowVoltageCabinetCircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSLBLowVoltageCabinetCircuitBreakerSwitchOff(plant_index, device_address))
