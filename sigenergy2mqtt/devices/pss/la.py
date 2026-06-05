from __future__ import annotations

import sigenergy2mqtt.sensors.pss_read_only as ro
import sigenergy2mqtt.sensors.pss_read_write as rw
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice


class LA(ModbusDevice):
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
            name=f"{model_id} {serial} LA",
            plant_index=plant_index,
            device_address=device_address,
            model="PSS LA",
            protocol_version=protocol_version,
        )

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

        self._add_sensor(rw.PSSLALowVoltageCabinetCircuitBreakerSwitchOn(plant_index, device_address))
        self._add_sensor(rw.PSSLALowVoltageCabinetCircuitBreakerSwitchOff(plant_index, device_address))
