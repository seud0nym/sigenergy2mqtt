"""Cloud-backed Instant Manual Control device."""

from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.sensors.cloud.read_write import (
    BatteryChargePowerLimit,
    BatteryDischargePowerLimit,
    BatteryExportLimitation,
    GridConnectionLimit,
    GridExportLimit,
    GridImportLimit,
    InstantControlDuration,
    InstantControlMode,
    InstantControlSwitch,
    SolarPowerLimit,
)


class SigenergyCloudControl(Device):
    """Expose cloud Instant Manual Control through normal MQTT sensors."""

    def __init__(self, plant_index: int, port: CloudControlPort) -> None:
        super().__init__(
            name="Sigenergy Cloud",
            plant_index=plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_cloud_control",
            manufacturer="Sigenergy",
            model=port.model,
            protocol_version=ProtocolVersion.N_A,
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

        self._add_sensor(GridExportLimit(plant_index))
        self._add_sensor(GridImportLimit(plant_index))
        self._add_sensor(GridConnectionLimit(plant_index))
        battery_charge_limit = BatteryChargePowerLimit(plant_index)
        battery_discharge_limit = BatteryDischargePowerLimit(
            plant_index, battery_charge_limit._snapshot
        )
        self._add_sensor(battery_charge_limit)
        self._add_sensor(battery_discharge_limit)
        self._add_sensor(SolarPowerLimit(plant_index))
        self._add_sensor(BatteryExportLimitation(plant_index))
