"""DC charger settings and values from the mySigen cloud."""

import logging

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.sensors.cloud.dc_charger import (
    CloudResponseSnapshot,
    DcChargerBatteryBoost,
    DcChargerBatteryBoostCutoffSoc,
    DcChargerChargingMode,
    DcChargerLifetimeChargedEnergy,
    DcChargerMonthlyChargedEnergy,
    DcChargerOcppLinkStatus,
    DcChargerOcppServerUrl,
    DcChargerPrimaryVehicle,
    DcChargerPrimaryVehicleBatteryCapacity,
    DcChargerStatusCode,
    DcChargerSurplusPvPriority,
    DcChargerV2xDischargeCutoffSoc,
    DcChargerV2xDischargeEnabled,
    DcChargerV2xDischargePowerLimit,
    DcChargerWeeklyChargedEnergy,
)

from .discovery import CloudDiscovery, DcChargerDiscovery

logger = logging.getLogger(__name__)

#: ``sgDeviceType`` of a DC charger in the Surplus PV priority list.
_DC_CHARGER_SG_DEVICE_TYPE = 5


class CloudDcCharger(Device):
    """A DC charger child device populated from the cloud."""

    # A separate physical product: stays a regular device linked with via_device
    ha_child_device_eligible = False

    @classmethod
    def from_discovery(cls, plant_index: int, station_id: str, discovery: CloudDiscovery) -> list["CloudDcCharger"]:
        count = len(discovery.dc_chargers)
        return [cls(plant_index, station_id, charger, index, count) for index, charger in enumerate(discovery.dc_chargers)]

    def __init__(self, plant_index: int, station_id: str, charger: DcChargerDiscovery, index: int = 0, count: int = 1) -> None:
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        sn = charger.serial_number
        super().__init__(
            name="Sigenergy Cloud DC Charger",
            plant_index=plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{station_id}_dc_charger_{sn}",
            manufacturer="Sigenergy",
            model="DC Charger",
            protocol_version=ProtocolVersion.N_A,
            sn=sn,
            plant_suffix=plant_suffix,
            sequence_suffix="" if count <= 1 else str(index + 1),
        )
        ids = (plant_index, station_id, sn, index)

        mode = CloudResponseSnapshot(lambda port: port.dc_charge_mode(sn))
        if charger.charge_modes:
            self._add_sensor(DcChargerChargingMode(*ids, charger.charge_modes, mode))
            self._add_sensor(DcChargerBatteryBoost(*ids, mode))
            self._add_sensor(DcChargerBatteryBoostCutoffSoc(*ids, charger.soc_range, mode))
            self._add_sensor(DcChargerV2xDischargePowerLimit(*ids, mode))
            self._add_sensor(DcChargerV2xDischargeCutoffSoc(*ids, mode))
        # pvPriority is station-wide, so only the first charger exposes it.
        if index == 0 and _DC_CHARGER_SG_DEVICE_TYPE in charger.surplus_pv_devices:
            try:
                self._add_sensor(DcChargerSurplusPvPriority(*ids, charger.surplus_pv_devices))
            except ValueError as exc:
                logger.warning("Cloud Surplus PV Priority sensor disabled: %s", exc)

        self._add_sensor(DcChargerStatusCode(*ids))
        energy = CloudResponseSnapshot(lambda port: port.dc_energy_totals(sn))
        self._add_sensor(DcChargerWeeklyChargedEnergy(*ids, energy))
        self._add_sensor(DcChargerMonthlyChargedEnergy(*ids, energy))
        self._add_sensor(DcChargerLifetimeChargedEnergy(*ids, energy))
        ocpp = CloudResponseSnapshot(lambda port: port.dc_ocpp_status(sn))
        self._add_sensor(DcChargerOcppLinkStatus(*ids, ocpp))
        self._add_sensor(DcChargerOcppServerUrl(*ids, ocpp))
        self._add_sensor(DcChargerV2xDischargeEnabled(*ids))
        vehicles = CloudResponseSnapshot(lambda port: port.dc_vehicles(sn))
        self._add_sensor(DcChargerPrimaryVehicle(*ids, vehicles))
        self._add_sensor(DcChargerPrimaryVehicleBatteryCapacity(*ids, vehicles))
