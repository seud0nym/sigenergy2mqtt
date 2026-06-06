from __future__ import annotations

import sigenergy2mqtt.sensors.pss_read_only as ro
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice


class Transformer(ModbusDevice):
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
            name=f"{model_id} {serial} Transformer",
            plant_index=plant_index,
            device_address=device_address,
            model="PSS Transformer",
            protocol_version=protocol_version,
            # HA device registry attributes
            sn=serial,
            model_id=model_id,
            serial=serial,
        )

        self._add_sensor(ro.PSSTransformerOilSurfaceTemperature(plant_index, device_address))
        self._add_sensor(ro.PSSTransformerWindingTemperature(plant_index, device_address))
