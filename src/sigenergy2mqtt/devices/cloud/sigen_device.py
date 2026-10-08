"""Inverter and battery devices discovered through mySigen cloud."""

import asyncio
import logging
from typing import Any

from aiohttp import ClientError

from sigenergy2mqtt.cloud.exceptions import CloudControlError
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.base.device import Device
from sigenergy2mqtt.devices.base.poller import SensorGroupPoller
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.sensors.cloud.device_info import (
    DeviceInfoSensor,
    DeviceInfoSnapshot,
)
from sigenergy2mqtt.sensors.cloud.read_only import gateway_sensor_suffix

from .discovery import CloudDiscovery

logger = logging.getLogger(__name__)


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
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{station_id}_{kind}_{sn}",
            manufacturer="Sigenergy",
            model=kind.title(),
            protocol_version=ProtocolVersion.N_A,
            sn=sn,
            plant_suffix="" if plant_index == 0 else str(plant_index + 1),
            translate=False,
        )
        self._mqtt_handler: MqttHandler | None = None
        self._station_id = station_id
        self._sn = sn
        self._pending_info = {static for static, payload, key in (
            (False, dynamic, "realTimeInfo"), (True, static, "paramInfoVOList")
        ) if key not in payload}
        self._add_info(False, dynamic)
        self._add_info(True, static)

    def _add_info(self, is_static: bool, payload: dict[str, Any]) -> None:
        key = "paramInfoVOList" if is_static else "realTimeInfo"
        plant_index, station_id, sn = self.plant_index, self._station_id, self._sn
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

    def subscribe(self, mqtt_client: Any, mqtt_handler: MqttHandler) -> None:
        self._mqtt_handler = mqtt_handler
        super().subscribe(mqtt_client, mqtt_handler)

    async def recover_info(self, port: Any, mqtt_client: Any, parent: Device | None = None) -> None:
        """Retry missing startup metadata and start polling recovered sensors."""
        if parent is not None:
            self.online = parent._online
        polling: list[asyncio.Task] = []
        try:
            while self._pending_info and self.online and not self._shutdown_event.is_set():
                for static in tuple(self._pending_info):
                    method = port.device_static_info if static else port.device_dynamic_info
                    try:
                        payload = await method(self.device_type, self._sn)
                    except (ClientError, CloudControlError) as exc:
                        logger.warning("%s device info recovery failed: %s", self.log_identity, exc)
                        continue
                    key = "paramInfoVOList" if static else "realTimeInfo"
                    if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
                        continue
                    before = set(self.all_sensors)
                    self._add_info(static, payload)
                    self._pending_info.remove(static)
                    added = [sensor for uid, sensor in self.all_sensors.items() if uid not in before]
                    if self._mqtt_handler is not None:
                        for sensor in added:
                            debug_topic = f"{sensor._get_base_topic(self.unique_id)}/debug"
                            self._mqtt_handler.register(mqtt_client, debug_topic, sensor.set_debug_logging)
                    new = [sensor for sensor in added if sensor.publishable]
                    if new:
                        if active_config.home_assistant.enabled:
                            self.publish_discovery(mqtt_client, clean=False)
                            self.publish_availability(mqtt_client, "online")
                        else:
                            self.publish_attributes(mqtt_client, clean=False)
                        polling.append(asyncio.create_task(SensorGroupPoller(self).run(port, mqtt_client, f"Recovered-{static}", *new)))
                if self._pending_info:
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=max(1.0, active_config.cloud.scan_interval))
                    except TimeoutError:
                        pass
            if polling:
                await asyncio.gather(*polling)
        finally:
            for task in polling:
                task.cancel()
            if polling:
                await asyncio.gather(*polling, return_exceptions=True)


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
