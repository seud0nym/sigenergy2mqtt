"""Sigenergy cloud gateway device."""

from typing import Any

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.sensors.cloud.read_only import (
    GatewayCommunicationStatus,
    GatewayFirmwareVersion,
    GatewayInfoSnapshot,
    GatewayModel,
    GatewaySerialNumber,
    gateway_sensor_suffix,
    grid_sensor_details,
)

from .discovery import CloudDiscovery


class Gateway(Device):
    """Gateway child device populated from its discovery response."""

    @classmethod
    def from_discovery(cls, plant_index: int, station_id: str, discovery: CloudDiscovery) -> "Gateway | None":
        if not discovery.gateway_info:
            return None
        info = discovery.gateway_info
        raw_grid_side_info = info.get("gridSideInfoList")
        grid_side_info = [entry for entry in raw_grid_side_info if isinstance(entry, dict)] if isinstance(raw_grid_side_info, list) else []
        return cls(
            plant_index,
            station_id,
            model=str(info.get("deviceModel") or "Sigenergy Gateway"),
            sn=str(info.get("snCode") or info.get("showSnCode") or ""),
            sw=str(info.get("softVersion") or ""),
            grid_side_info=grid_side_info,
        )

    def __init__(self, plant_index: int, station_id: str, *, model: str, sn: str, sw: str, grid_side_info: list[dict[str, Any]]) -> None:
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        super().__init__(
            name=model,
            plant_index=plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{station_id}_gateway",
            manufacturer="Sigenergy",
            model="Gateway",
            model_id=model,
            protocol_version=ProtocolVersion.N_A,
            sn=sn,
            sw=sw,
            plant_suffix=plant_suffix,
        )
        seen_suffixes: set[str] = set()
        snapshot = GatewayInfoSnapshot()
        self._add_sensor(GatewayCommunicationStatus(plant_index, station_id, snapshot))
        self._add_sensor(GatewayFirmwareVersion(plant_index, station_id, snapshot))
        self._add_sensor(GatewayModel(plant_index, station_id, snapshot))
        self._add_sensor(GatewaySerialNumber(plant_index, station_id, snapshot))
        for entry in grid_side_info:
            param_key = entry.get("paramKey")
            if not isinstance(param_key, str) or not param_key:
                continue
            suffix = gateway_sensor_suffix(param_key)
            if not suffix or suffix in seen_suffixes:
                continue
            seen_suffixes.add(suffix)
            sensor_type, unit, device_class = grid_sensor_details(entry.get("paramValue"))
            self._add_sensor(sensor_type(plant_index, station_id, param_key, snapshot, unit=unit, device_class=device_class))
