"""Read-only sensors exposed by the mySigen gateway endpoint."""

from __future__ import annotations

import math
import re
from typing import Any

from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.common import DeviceClass, ProtocolVersion, StateClass
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import CloudSensor, DiscoveryKeys
from sigenergy2mqtt.sensors.cloud.functions import _identity


def gateway_sensor_suffix(param_key: str) -> str:
    """Create a stable entity suffix from the API's descriptive parameter key."""
    return re.sub(r"[^a-z0-9]+", "_", param_key.casefold()).strip("_")


class GatewayInfoSnapshot:
    """Share one gateway response between every sensor in a polling refresh."""

    def __init__(self) -> None:
        self._payload: dict[str, Any] | None = None
        self._error: Exception | None = None

    def begin_refresh(self) -> None:
        self._payload = None
        self._error = None

    async def read(self, port: CloudControlPort) -> dict[str, Any]:
        if self._error is not None:
            raise self._error
        if self._payload is None:
            try:
                self._payload = await port.gateway_info()
            except Exception as exc:
                self._error = exc
                raise
        return self._payload


class GatewaySensor(CloudSensor):
    """Common gateway sensor implementation."""

    def __init__(
        self,
        plant_index: int,
        station_id: str,
        suffix: str,
        name: str,
        snapshot: GatewayInfoSnapshot,
        *,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
    ) -> None:
        object_id, unique_id = _identity(plant_index, station_id, f"gateway_{suffix}")
        super().__init__(
            name=name,
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._snapshot = snapshot
        self._polling_coordinator = snapshot


class GatewayCommunicationStatus(GatewaySensor):
    def __init__(self, plant_index: int, station_id: str, snapshot: GatewayInfoSnapshot) -> None:
        super().__init__(
            plant_index=plant_index,
            station_id=station_id,
            suffix="communication_status",
            name="Communication Status",
            snapshot=snapshot,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:signal-variant",
        )

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        status = (await self._snapshot.read(port)).get("communicationStatus")
        if status is None:
            return "Unknown"
        try:
            status = int(status)
        except (TypeError, ValueError):
            return "Unknown"
        if status == 1:
            return "Offline"
        if status == 2:
            return "Online"
        return "Unknown"


class GatewayFirmwareVersion(GatewaySensor):
    def __init__(self, plant_index: int, station_id: str, snapshot: GatewayInfoSnapshot) -> None:
        super().__init__(
            plant_index=plant_index,
            station_id=station_id,
            suffix="firmware_version",
            name="Firmware Version",
            snapshot=snapshot,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
        )
        self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        return str((await self._snapshot.read(port)).get("softVersion") or "")


class GatewayModel(GatewaySensor):
    def __init__(self, plant_index: int, station_id: str, snapshot: GatewayInfoSnapshot) -> None:
        super().__init__(
            plant_index=plant_index,
            station_id=station_id,
            suffix="model",
            name="Model",
            snapshot=snapshot,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
        )
        self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        return str((await self._snapshot.read(port)).get("deviceModel") or "")


class GatewaySerialNumber(GatewaySensor):
    def __init__(self, plant_index: int, station_id: str, snapshot: GatewayInfoSnapshot) -> None:
        super().__init__(
            plant_index=plant_index,
            station_id=station_id,
            suffix="serial_number",
            name="Serial Number",
            snapshot=snapshot,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
        )
        self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        return str((await self._snapshot.read(port)).get("snCode") or (await self._snapshot.read(port)).get("showSnCode") or "")


class GatewayGridSideInfoSensor(GatewaySensor):
    """Base for dynamically discovered grid-side values."""

    def __init__(
        self,
        plant_index: int,
        station_id: str,
        param_key: str,
        snapshot: GatewayInfoSnapshot,
        *,
        unit: str | None,
        device_class: DeviceClass | None,
    ) -> None:
        self.param_key = param_key
        self._api_units = {"kVar", "kvar"} if unit == "kvar" else {unit}
        match unit:
            case "A":
                icon = "mdi:current-ac"
            case "kW" | "kVar" | "kvar":
                icon = "mdi:flash"
            case "Hz":
                icon = "mdi:sine-wave"
            case "V":
                icon = "mdi:lightning-bolt"
            case _:
                if "Contactor" in param_key:
                    icon = "mdi:toggle-switch-variant-off"
                else:
                    icon = None
        super().__init__(
            plant_index=plant_index,
            station_id=station_id,
            suffix=gateway_sensor_suffix(param_key),
            name=param_key,
            snapshot=snapshot,
            unit=unit,
            device_class=device_class,
            state_class=StateClass.MEASUREMENT if unit else None,
            icon=icon,
        )

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        entries = (await self._snapshot.read(port)).get("gridSideInfoList")
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("paramKey") != self.param_key:
                continue
            value = entry.get("paramValue")
            if not isinstance(value, str):
                return None
            if self.unit is None:
                return value
            parts = value.rsplit(maxsplit=1)
            if len(parts) != 2 or parts[1] not in self._api_units:
                return None
            try:
                number = float(parts[0])
            except ValueError:
                return None
            return number if math.isfinite(number) else None
        return None

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Grid-Side state read from the Gateway via the Cloud API"
        return attributes


class GatewayGridVoltage(GatewayGridSideInfoSensor):
    pass


class GatewayGridCurrent(GatewayGridSideInfoSensor):
    pass


class GatewayGridFrequency(GatewayGridSideInfoSensor):
    pass


class GatewayGridPower(GatewayGridSideInfoSensor):
    pass


class GatewayGridReactivePower(GatewayGridSideInfoSensor):
    pass


class GatewayGridText(GatewayGridSideInfoSensor):
    pass


GRID_SENSOR_TYPES: dict[str, tuple[type[GatewayGridSideInfoSensor], DeviceClass | None]] = {
    "V": (GatewayGridVoltage, DeviceClass.VOLTAGE),
    "A": (GatewayGridCurrent, DeviceClass.CURRENT),
    "Hz": (GatewayGridFrequency, DeviceClass.FREQUENCY),
    "kW": (GatewayGridPower, DeviceClass.POWER),
    "kVar": (GatewayGridReactivePower, DeviceClass.REACTIVE_POWER),
    "kvar": (GatewayGridReactivePower, DeviceClass.REACTIVE_POWER),
}


def grid_sensor_details(
    param_value: Any,
) -> tuple[type[GatewayGridSideInfoSensor], str | None, DeviceClass | None]:
    """Select the appropriate sensor base from the value's trailing unit."""
    if isinstance(param_value, str):
        parts = param_value.rsplit(maxsplit=1)
        if len(parts) == 2 and parts[1] in GRID_SENSOR_TYPES:
            sensor_type, device_class = GRID_SENSOR_TYPES[parts[1]]
            unit = "kvar" if parts[1] == "kVar" else parts[1]
            return sensor_type, unit, device_class
    return GatewayGridText, None, None
