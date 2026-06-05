from __future__ import annotations

import sigenergy2mqtt.sensors.pss_read_only as ro
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice


class DistributionCabinet(ModbusDevice):
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
            name=f"{model_id} {serial} Distribution Cabinet",
            plant_index=plant_index,
            device_address=device_address,
            model="PSS Distribution Cabinet",
            protocol_version=protocol_version,
            # HA device registry attributes
            sn=serial,
            model_id=model_id,
            serial=serial,
        )

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
