"""Cloud-backed Instant Manual Control device."""

from typing import Any

from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.sensors.cloud.read_only import (
    GatewayCommunicationStatus,
    GatewayInfoSnapshot,
    gateway_sensor_suffix,
    grid_sensor_details,
)
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


class SigenergyGateway(Device):
    """Gateway child device populated from its discovery response."""

    def __init__(
        self,
        plant_index: int,
        station_id: str,
        *,
        model: str,
        sn: str,
        hw: str,
        grid_side_info: list[dict[str, Any]],
    ) -> None:
        name = "Sigenergy Gateway"
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        super().__init__(
            name=name,
            plant_index=plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{station_id}_gateway",
            manufacturer="Sigenergy",
            model=model,
            protocol_version=ProtocolVersion.N_A,
            sn=sn,
            hw=hw,
            plant_suffix=plant_suffix,
        )
        snapshot = GatewayInfoSnapshot()
        self._add_sensor(GatewayCommunicationStatus(plant_index, station_id, snapshot))
        seen_suffixes: set[str] = set()
        for entry in grid_side_info:
            param_key = entry.get("paramKey")
            if not isinstance(param_key, str) or not param_key:
                continue
            suffix = gateway_sensor_suffix(param_key)
            if not suffix or suffix in seen_suffixes:
                continue
            seen_suffixes.add(suffix)
            sensor_type, unit, device_class = grid_sensor_details(entry.get("paramValue"))
            self._add_sensor(
                sensor_type(
                    plant_index,
                    station_id,
                    param_key,
                    snapshot,
                    unit=unit,
                    device_class=device_class,
                )
            )


class SigenergyCloudControl(Device):
    """Expose cloud Instant Manual Control through normal MQTT sensors."""

    def __init__(self, plant_index: int, port: CloudControlPort, gateway_info: dict | None = None) -> None:
        name = "Sigenergy Cloud"
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        super().__init__(
            name=name,
            plant_index=plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{port.station_id}_cloud_control",
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

        # The switch must be registered first so its state topic exists when
        # the selectors add their availability gates.
        self._add_sensor(switch)
        self._add_sensor(mode)
        self._add_sensor(duration)

        self._add_sensor(GridExportLimit(plant_index, station_id))
        self._add_sensor(GridImportLimit(plant_index, station_id))
        self._add_sensor(GridConnectionLimit(plant_index, station_id))
        battery_charge_limit = BatteryChargePowerLimit(plant_index, station_id)
        battery_discharge_limit = BatteryDischargePowerLimit(plant_index, station_id, battery_charge_limit._snapshot)
        self._add_sensor(battery_charge_limit)
        self._add_sensor(battery_discharge_limit)
        self._add_sensor(SolarPowerLimit(plant_index, station_id))
        self._add_sensor(BatteryExportLimitation(plant_index, station_id))

        if gateway_info:
            raw_grid_side_info = gateway_info.get("gridSideInfoList")
            grid_side_info = [entry for entry in raw_grid_side_info if isinstance(entry, dict)] if isinstance(raw_grid_side_info, list) else []
            self._add_child_device(
                SigenergyGateway(
                    plant_index,
                    station_id,
                    model=str(gateway_info.get("deviceModel") or "Sigenergy Gateway"),
                    sn=str(gateway_info.get("snCode") or gateway_info.get("showSnCode") or ""),
                    hw=str(gateway_info.get("softVersion") or ""),
                    grid_side_info=grid_side_info,
                )
            )
