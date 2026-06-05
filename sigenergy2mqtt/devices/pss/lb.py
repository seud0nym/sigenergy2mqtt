from __future__ import annotations

import sigenergy2mqtt.sensors.pss_read_only as ro
import sigenergy2mqtt.sensors.pss_read_write as rw
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice


class LB(ModbusDevice):
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
            name=f"{model_id} {serial} LB",
            plant_index=plant_index,
            device_address=device_address,
            model="PSS LB",
            protocol_version=protocol_version,
            # HA device registry attributes
            sn=serial,
            model_id=model_id,
            serial=serial,
        )

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

        self._add_sensor(rw.PSSLBLowVoltageCabinetCircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSLBLowVoltageCabinetCircuitBreakerSwitchOff(plant_index, device_address))
