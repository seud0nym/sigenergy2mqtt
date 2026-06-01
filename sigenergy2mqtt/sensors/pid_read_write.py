"""PID (Power Inverter Device) read-write sensors."""

from __future__ import annotations

from sigenergy2mqtt.common import InputType, Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import ScanInterval, SelectSensor


class PIDStartStop(SelectSensor, NonInverter):
    ADDRESS = 43000

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Start/Stop",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_start_stop",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            options=["Stop", "Start"],
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V2_9,
        )
