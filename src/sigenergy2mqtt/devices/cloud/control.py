"""Cloud-backed Instant Manual Control device."""

import logging
from collections.abc import Callable

from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.sensors.cloud.read_write import (
    BatteryChargePowerLimit,
    BatteryDischargePowerLimit,
    GridConnectionLimit,
    GridExportLimit,
    GridImportLimit,
    InstantControlDuration,
    InstantControlMode,
    InstantControlSwitch,
    OperationalMode,
    SolarPowerLimit,
)

from .discovery import CloudDiscovery
from .gateway import Gateway

logger = logging.getLogger(__name__)

ChildBuilder = Callable[[int, str, CloudDiscovery], Device | None]
_CHILD_BUILDERS: tuple[ChildBuilder, ...] = (Gateway.from_discovery,)


class CloudControl(Device):
    """Expose cloud controls through normal MQTT sensors."""

    def __init__(self, plant_index: int, port: CloudControlPort, discovery: CloudDiscovery) -> None:
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        super().__init__(
            "Sigenergy Cloud",
            plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_cloud_{port.station_id}",
            manufacturer="Sigenergy",
            model=port.model,
            protocol_version=ProtocolVersion.N_A,
            plant_suffix=plant_suffix,
        )
        station_id = port.station_id
        mode = InstantControlMode(plant_index, station_id)
        duration = InstantControlDuration(plant_index, station_id)
        switch = InstantControlSwitch(plant_index, station_id, mode, duration)
        mode.set_availability_control_sensor(switch)
        duration.set_availability_control_sensor(switch)

        self._add_sensor(switch)
        self._add_sensor(mode)
        self._add_sensor(duration)
        if discovery.operational_modes:
            try:
                self._add_sensor(OperationalMode(plant_index, station_id, discovery.operational_modes))
            except ValueError as exc:
                logger.warning("Cloud operational-mode sensor disabled: %s", exc)

        self._add_sensor(GridExportLimit(plant_index, station_id))
        self._add_sensor(GridImportLimit(plant_index, station_id))
        self._add_sensor(GridConnectionLimit(plant_index, station_id))
        self._add_sensor(SolarPowerLimit(plant_index, station_id))

        if discovery.has_battery:
            battery_charge_limit = BatteryChargePowerLimit(plant_index, station_id)
            battery_discharge_limit = BatteryDischargePowerLimit(plant_index, station_id, battery_charge_limit._snapshot)
            self._add_sensor(battery_charge_limit)
            self._add_sensor(battery_discharge_limit)

        for build_child in _CHILD_BUILDERS:
            if (child := build_child(plant_index, station_id, discovery)) is not None:
                self._add_child_device(child)
