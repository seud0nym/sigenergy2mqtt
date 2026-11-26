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
    BatteryExportLimitation,
    GridConnectionLimit,
    GridExportLimit,
    GridImportLimit,
    InstantControlDuration,
    InstantControlMode,
    InstantControlSwitch,
    OperationalMode,
    SitePvSurplusPriority,
    SolarPowerLimit,
)

from .dc_charger import CloudDcCharger
from .discovery import CloudDiscovery
from .gateway import Gateway
from .sigen_device import SigenCloudDevice, build_sigen_devices

logger = logging.getLogger(__name__)

#: ``sgDeviceType`` of a DC charger in the Surplus PV priority list.
_DC_CHARGER_SG_DEVICE_TYPE = 5

ChildBuilder = Callable[[int, str, CloudDiscovery], Device | None]
_CHILD_BUILDERS: tuple[ChildBuilder, ...] = (Gateway.from_discovery,)


class CloudControl(Device):
    """Expose cloud controls through normal MQTT sensors."""

    def __init__(self, plant_index: int, port: CloudControlPort, discovery: CloudDiscovery) -> None:
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        super().__init__(
            "Sigenergy Cloud",
            plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{port.station_id}",
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
            self._add_sensor(BatteryExportLimitation(plant_index, station_id))
        # A site-wide setting, offered when a DC charger shares surplus PV
        if _DC_CHARGER_SG_DEVICE_TYPE in discovery.surplus_pv_devices:
            try:
                self._add_sensor(SitePvSurplusPriority(plant_index, station_id, discovery.surplus_pv_devices))
            except ValueError as exc:
                logger.warning("Cloud Site PV Surplus Priority sensor disabled: %s", exc)

        for build_child in _CHILD_BUILDERS:
            if (child := build_child(plant_index, station_id, discovery)) is not None:
                self._add_child_device(child)
        for dc_charger in CloudDcCharger.from_discovery(plant_index, station_id, discovery):
            self._add_child_device(dc_charger)
        for child in build_sigen_devices(plant_index, station_id, discovery):
            self._add_child_device(child)
            if isinstance(child, SigenCloudDevice) and child._pending_info and child not in self.children:
                child.via_device = self.unique_id
                child.parent_device = self
                self.children.append(child)

    def schedule(self, transport, mqtt_client):
        tasks = super().schedule(transport, mqtt_client)
        tasks.extend(child.recover_info(transport, mqtt_client, self) for child in self.children if isinstance(child, SigenCloudDevice) and child._pending_info)
        return tasks
