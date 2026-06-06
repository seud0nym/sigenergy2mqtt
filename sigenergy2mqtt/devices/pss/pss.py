from __future__ import annotations

import asyncio
from typing import cast

import sigenergy2mqtt.sensors.pss_read_only as ro
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient

from .distribution_cabinet import DistributionCabinet
from .la import LA
from .lb import LB
from .mv import MV
from .transformer import Transformer


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
        await pss._register_child_devices(plant_index, device_address, protocol_version, cast(str, model_id), cast(str, serial))
        await pss._register_sensors(plant_index, device_address, model, serial_number)
        return pss

    async def _register_child_devices(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
        model_id: str,
        serial: str,
    ) -> None:
        self._add_child_device(MV(plant_index, device_address, protocol_version, model_id, serial))
        self._add_child_device(LA(plant_index, device_address, protocol_version, model_id, serial))
        self._add_child_device(LB(plant_index, device_address, protocol_version, model_id, serial))
        self._add_child_device(Transformer(plant_index, device_address, protocol_version, model_id, serial))
        self._add_child_device(DistributionCabinet(plant_index, device_address, protocol_version, model_id, serial))

    async def _register_sensors(self, plant_index: int, device_address: int, model: ro.PSSModelType, serial_number: ro.PSSSerialNumber) -> None:
        self._add_sensor(model)
        self._add_sensor(serial_number)
        self._add_sensor(ro.PSSCommunicationStatus(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication1(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication2(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication3(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication4(plant_index, device_address))
        self._add_sensor(ro.PSSTeleindication5(plant_index, device_address))
