from __future__ import annotations

import sigenergy2mqtt.sensors.pss_read_only as ro
import sigenergy2mqtt.sensors.pss_read_write as rw
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice


class MV(ModbusDevice):
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
            name=f"{model_id} {serial} MV",
            plant_index=plant_index,
            device_address=device_address,
            model="PSS MV",
            protocol_version=protocol_version,
            # HA device registry attributes
            sn=serial,
            model_id=model_id,
            serial=serial,
        )

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

        self._add_sensor(rw.PSSMVCabinetG3CircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSMVCabinetG3CircuitBreakerSwitchOff(plant_index, device_address))
