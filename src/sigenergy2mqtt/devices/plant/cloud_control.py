"""Cloud-backed Instant Manual Control device."""

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.sensors.plant_cloud_control import (
    InstantControlDuration,
    InstantControlMode,
    InstantControlSwitch,
)


class SigenergyCloudControl(Device):
    """Expose cloud Instant Manual Control through normal MQTT sensors."""

    def __init__(self, plant_index: int) -> None:
        super().__init__(
            name="Sigenergy Cloud Control",
            plant_index=plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_cloud_control",
            manufacturer="Sigenergy",
            model="mySigen Cloud (unofficial)",
            protocol_version=ProtocolVersion.V2_4,
        )
        mode = InstantControlMode(plant_index)
        duration = InstantControlDuration(plant_index)
        switch = InstantControlSwitch(plant_index, mode, duration)
        mode.set_availability_control_sensor(switch)
        duration.set_availability_control_sensor(switch)

        # The switch must be registered first so its state topic exists when
        # the selectors add their availability gates.
        self._add_sensor(switch)
        self._add_sensor(mode)
        self._add_sensor(duration)
