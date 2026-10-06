"""Inverter and battery devices discovered through mySigen cloud."""

from typing import Any

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.sensors.cloud.device_info import (
    DeviceInfoSensor,
    DeviceInfoSnapshot,
)
from sigenergy2mqtt.sensors.cloud.read_only import gateway_sensor_suffix

from .discovery import CloudDiscovery


class SigenCloudDevice(Device):
    device_type: int

    def __init__(
        self,
        plant_index: int,
        station_id: str,
        device: dict[str, Any],
        dynamic: dict[str, Any],
        static: dict[str, Any],
    ) -> None:
        sn = str(device["serialNumber"])
        position = device.get("attrMap", {}).get("batPosition")
        kind = "inverter" if self.device_type == 3 else "battery"
        battery_name = position if position is not None else sn
        default_model = "SigenStor Inverter" if self.device_type == 3 else "SigenStor Battery"
        static_entries = static.get("paramInfoVOList", [])
        if not isinstance(static_entries, list):
            static_entries = []
        device_model = next(
            (entry.get("paramValue") for entry in static_entries if isinstance(entry, dict) and entry.get("paramKey") == "Device Model"),
            None,
        )
        model_name = str(device_model) if device_model else default_model
        name = f"{model_name} {sn if self.device_type == 3 else battery_name}"
        super().__init__(
            name,
            plant_index,
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_cloud_{station_id}_{kind}_{sn}",
            manufacturer="Sigenergy",
            model=kind.title(),
            protocol_version=ProtocolVersion.N_A,
            sn=sn,
            plant_suffix="" if plant_index == 0 else str(plant_index + 1),
            translate=False,
        )
        for is_static, payload, key in (
            (False, dynamic, "realTimeInfo"),
            (True, static, "paramInfoVOList"),
        ):
            snapshot = DeviceInfoSnapshot(self.device_type, sn, is_static)
            seen_suffixes: set[str] = set()
            entries = payload.get(key, [])
            for entry in entries if isinstance(entries, list) else []:
                param_key = entry.get("paramKey") if isinstance(entry, dict) else None
                suffix = gateway_sensor_suffix(param_key) if isinstance(param_key, str) else ""
                if param_key and suffix and suffix not in seen_suffixes:
                    seen_suffixes.add(suffix)
                    self._add_sensor(
                        DeviceInfoSensor(
                            plant_index,
                            station_id,
                            sn,
                            param_key,
                            str(entry.get("paramValueUnit") or ""),
                            snapshot,
                            static=is_static,
                        )
                    )


class CloudInverter(SigenCloudDevice):
    device_type = 3


class CloudBattery(SigenCloudDevice):
    device_type = 4


def build_sigen_devices(plant_index: int, station_id: str, discovery: CloudDiscovery) -> list[Device]:
    result: list[Device] = []
    for device in discovery.device_list:
        device_name = device.get("deviceType")
        if not active_config.cloud.discover_inverters and device_name == "Inverter":
            continue
        cls = {"Inverter": CloudInverter, "Battery": CloudBattery}.get(device_name) if isinstance(device_name, str) else None
        sn = device.get("serialNumber")
        info = (discovery.device_info or {}).get(sn) if isinstance(sn, str) else None
        if cls is not None and info is not None:
            result.append(cls(plant_index, station_id, device, *info))
    return result
