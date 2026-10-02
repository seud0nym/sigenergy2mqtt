"""Sensors backed by the per-device cloud information endpoints."""

import math
from typing import Any

from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.common import (
    DeviceClass,
    ProtocolVersion,
    ScanIntervalDefault,
    StateClass,
)
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import CloudSensor, DiscoveryKeys
from sigenergy2mqtt.sensors.cloud.functions import _identity

from .read_only import gateway_sensor_suffix


_UNIT_CLASSES = {
    "A": DeviceClass.CURRENT,
    "V": DeviceClass.VOLTAGE,
    "Hz": DeviceClass.FREQUENCY,
    "kW": DeviceClass.POWER,
    "kVar": DeviceClass.REACTIVE_POWER,
    "kWh": DeviceClass.ENERGY_STORAGE,
    "%": DeviceClass.BATTERY,
    "℃": DeviceClass.TEMPERATURE,
    "℉": DeviceClass.TEMPERATURE,
    "°C": DeviceClass.TEMPERATURE,
    "°F": DeviceClass.TEMPERATURE,
}

_NORMALIZED_UNITS = {"kVar": "kvar", "℃": "°C", "℉": "°F"}


class DeviceInfoSnapshot:
    def __init__(self, device_type: int, sn_code: str, static: bool) -> None:
        self.device_type, self.sn_code, self.static = device_type, sn_code, static
        self._payload: dict[str, Any] | None = None
        self._error: Exception | None = None

    def begin_refresh(self) -> None:
        self._payload = None
        self._error = None

    async def read(self, port: CloudControlPort) -> dict[str, Any]:
        if self._error is not None:
            raise self._error
        if self._payload is None:
            method = (
                port.device_static_info if self.static else port.device_dynamic_info
            )
            try:
                self._payload = await method(self.device_type, self.sn_code)
            except Exception as exc:
                self._error = exc
                raise
        return self._payload


class DeviceInfoSensor(CloudSensor):
    def __init__(
        self,
        plant_index: int,
        station_id: str,
        sn_code: str,
        param_key: str,
        unit: str,
        snapshot: DeviceInfoSnapshot,
        *,
        static: bool,
    ) -> None:
        suffix = f"{snapshot.device_type}_{sn_code}_{'static' if static else 'dynamic'}_{gateway_sensor_suffix(param_key)}"
        object_id, unique_id = _identity(plant_index, station_id, suffix)
        normalized_unit = _NORMALIZED_UNITS.get(unit, unit) or None
        device_class = _UNIT_CLASSES.get(unit)
        super().__init__(
            name=param_key,
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=ScanIntervalDefault.LOW
            if static
            else active_config.cloud.scan_interval,
            unit=normalized_unit,
            device_class=device_class,
            state_class=StateClass.MEASUREMENT if unit else None,
            icon=None,
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self.param_key, self._snapshot, self._polling_coordinator = (
            param_key,
            snapshot,
            snapshot,
        )
        self._static = static
        if static:
            self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        payload = await self._snapshot.read(port)
        entries = payload.get("paramInfoVOList" if self._static else "realTimeInfo", [])
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and entry.get("paramKey") == self.param_key:
                value = entry.get("paramValueText")
                if self.unit is not None:
                    if not isinstance(value, (int, float, str)):
                        return None
                    try:
                        number = float(value)
                    except (TypeError, ValueError):
                        return None
                    return number if math.isfinite(number) else None
                return str(value) if value is not None else None
        return None
