from __future__ import annotations

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import WriteOnlySensor


class PIDStartStop(WriteOnlySensor, NonInverter):
    ADDRESS = 43000

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PID Start/Stop",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_start_stop",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V2_9,
            payload_off="stop",
            payload_on="start",
            name_off="Stop",
            name_on="Start",
            icon_off="mdi:stop",
            icon_on="mdi:play",
        )
