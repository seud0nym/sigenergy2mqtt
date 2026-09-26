"""Adapter for the vendored, unofficial mySigen app API."""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, TypeVar

from aiohttp import ClientError

from sigenergy2mqtt.metrics.metrics import Metrics

from .exceptions import (
    CloudControlAuthError,
    CloudControlRateLimitedError,
    CloudControlRejectedError,
    CloudControlUnavailableError,
    CloudControlUnsupportedError,
)
from .models import (
    Capabilities,
    InstantControlMode,
    InstantControlStatus,
    InstantOverrideCommand,
)
from .vendor.solidfox.sigenergy_cloud import (
    InstantManualMode,
    SigenergyCloudAPIError,
    SigenergyCloudAuthError,
    SigenergyCloudClient,
    SigenergyCloudError,
    SigenergyCloudRateLimitError,
)

_MODE_TO_APP_CODE = {
    InstantControlMode.CHARGE: InstantManualMode.CHARGING,
    InstantControlMode.DISCHARGE: InstantManualMode.DISCHARGING,
    InstantControlMode.HOLD: InstantManualMode.HOLD_BATTERY,
    InstantControlMode.SELF_CONSUMPTION: InstantManualMode.SELF_CONSUMPTION,
}
_APP_CODE_TO_MODE = {value: key for key, value in _MODE_TO_APP_CODE.items()}
_CAPABILITIES = Capabilities(
    features=frozenset(),
    min_duration=timedelta(minutes=1),
    max_duration=timedelta(minutes=1440),
)
_T = TypeVar("_T")

_TOPOLOGY_DEVICE_TYPES = {
    3: "Inverter",
    4: "Battery",
    5: "DcCharger",
    6: "AcCharger",
    8: "Gateway",
    9: "Meter",
}

logger = logging.getLogger(__name__)


def _api_error_indicates_availability(exc: SigenergyCloudAPIError) -> bool:
    """Return whether an API error contains a well-formed response from the cloud."""
    if exc.status_code is None or exc.status_code >= 500 or exc.response_body is None:
        return False
    try:
        payload = json.loads(exc.response_body)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    code = payload.get("code")
    try:
        numeric_code = int(code) if isinstance(code, (int, str)) else None
    except ValueError:
        numeric_code = None
    return numeric_code is None or numeric_code < 500


class MySigenCloudAdapter:
    """Translate domain commands to the unofficial, vendored cloud client."""

    def __init__(self, username: str, password: str, region: str) -> None:
        self._client = SigenergyCloudClient(username, password, region=region)
        self._connected = False
        self._connection_generation = 0
        self._connect_lock = asyncio.Lock()

    @property
    def model(self) -> str:
        return "mySigen Cloud (unofficial)"

    @property
    def station_id(self) -> str:
        """Return the station selected during cloud discovery."""
        if self._client.station_id is None:
            raise CloudControlUnavailableError("Cloud station has not been discovered")
        return self._client.station_id

    @property
    def capabilities(self) -> Capabilities:
        return _CAPABILITIES

    async def connect(self) -> None:
        async with self._connect_lock:
            await self._connect_locked()

    async def _connect_locked(self) -> None:
        """Connect while the caller holds ``_connect_lock``."""
        if self._connected:
            return
        started = time.monotonic()
        try:
            await self._client.connect()
            logger.info(f"Connected to {self._client.base_url} Cloud API (region={self._client.region})")
        except SigenergyCloudAuthError as exc:
            await Metrics.cloud_connection(connected=False, error=True)
            raise CloudControlAuthError(str(exc)) from exc
        except SigenergyCloudRateLimitError as exc:
            await Metrics.cloud_connection(connected=False, error=True)
            raise CloudControlRateLimitedError(str(exc)) from exc
        except (ClientError, SigenergyCloudError, OSError, TimeoutError) as exc:
            await Metrics.cloud_connection(connected=False, error=True)
            raise CloudControlUnavailableError(str(exc)) from exc
        except Exception:
            await Metrics.cloud_connection(connected=False, error=True)
            raise
        finally:
            await Metrics.cloud_connection_attempt(time.monotonic() - started)
        self._connected = True
        self._connection_generation += 1
        await Metrics.cloud_connection(connected=True)

    async def _reconnect(self, failed_generation: int) -> None:
        """Replace an invalid cloud login unless another task already did so."""
        async with self._connect_lock:
            logger.debug(f"Reconnecting to {self._client.base_url} Cloud API (_connection_generation={self._connection_generation}, failed_generation={failed_generation})")
            if self._connection_generation != failed_generation:
                return
            self._connected = False
            await Metrics.cloud_connection(connected=False, reconnect=True)
            await self._connect_locked()

    async def _invalidate_connection(self, failed_generation: int) -> None:
        """Invalidate a failed login without overwriting a newer connection."""
        async with self._connect_lock:
            if self._connection_generation == failed_generation:
                self._connected = False
                await Metrics.cloud_connection(connected=False)
                logger.debug(f"Connection to {self._client.base_url} Cloud API invalidated (_connection_generation={self._connection_generation}, failed_generation={failed_generation})")

    async def close(self) -> None:
        await self._client.close()
        self._connected = False
        await Metrics.cloud_connection(connected=False)
        logger.info(f"Disconnected from {self._client.base_url} Cloud API")

    async def device_list(self) -> list[dict[str, Any]]:
        """Return app topology devices in the official cloud API shape."""
        topology = await self._cloud_operation(self._client.device_topology)
        devices: list[dict[str, Any]] = []
        for node in self._client.iter_topology_nodes(topology):
            raw_device_type = node.get("deviceType")
            if not isinstance(raw_device_type, int):
                continue
            device_type = _TOPOLOGY_DEVICE_TYPES.get(raw_device_type)
            if device_type is None:
                # AIO nodes are topology containers, not an official API device type.
                continue

            offline = self._client.topology_node_is_offline(node)
            status = "Offline" if offline else "Normal" if offline is False else "Fault"
            attributes: dict[str, Any] = {}
            if device_type == "Inverter" and node.get("ratedActivePower") is not None:
                attributes["ratedActivePower"] = node["ratedActivePower"]

            devices.append({
                "systemId": str(node.get("stationId") or topology.get("stationId") or ""),
                "serialNumber": str(node.get("snCode") or node.get("showSnCode") or ""),
                "deviceType": device_type,
                "status": status,
                "pn": str(node.get("deviceCode") or node.get("gatewayDeviceCode") or ""),
                "firmwareVersion": str(node.get("modelVersionStr") or ""),
                "attrMap": attributes,
            })
        return devices

    async def gateway_info(self) -> dict[str, Any]:
        """Return details and live grid-side values for the station gateway."""
        return await self._cloud_operation(self._client.gateway_info)

    async def set_instant_override(self, command: InstantOverrideCommand) -> None:
        unsupported = []
        if command.power_kw is not None:
            unsupported.append("power limit")
        if command.charge_priority is not None or command.discharge_priority is not None:
            unsupported.append("source priority")
        if command.starts_at is not None:
            unsupported.append("scheduled start")
        if unsupported:
            raise CloudControlUnsupportedError(f"mySigen cloud backend does not support {', '.join(unsupported)}")
        if not self.capabilities.min_duration <= command.duration <= self.capabilities.max_duration:
            raise CloudControlRejectedError("Duration must be between 1 and 1440 minutes")
        duration_minutes = round(command.duration.total_seconds() / 60)
        await self._cloud_operation(
            lambda: self._client.set_instant_manual_control(_MODE_TO_APP_CODE[command.mode], duration_minutes=duration_minutes),
            reject_api_errors=True,
        )

    async def clear_instant_override(self) -> None:
        await self._cloud_operation(self._client.disable_instant_manual_control)

    async def instant_control_status(self) -> InstantControlStatus:
        status = await self._cloud_operation(self._client.instant_manual_control)
        return InstantControlStatus(
            enabled=status.enabled,
            mode=_APP_CODE_TO_MODE.get(status.mode) if status.mode is not None else None,
            ends_at=float(status.end_time) if status.end_time is not None else None,
        )

    async def _cloud_operation(
        self,
        operation: Callable[[], Awaitable[_T]],
        *,
        reject_api_errors: bool = False,
    ) -> _T:
        """Run an operation, renewing a cloud login invalidated by the server.

        Logging in to the app on another device can invalidate an otherwise
        healthy session. Retry exactly once after re-authentication; persistent
        authentication failures are still reported to the caller.
        """
        await self.connect()
        generation = self._connection_generation
        for attempt in range(2):
            started = time.monotonic()
            try:
                try:
                    logger.debug(f"mySigen {operation.__name__} executing (attempt {attempt + 1}/2, generation={generation})")
                    result = await operation()
                finally:
                    # Stop timing before error handling can reconnect. Login and
                    # station-discovery latency is tracked independently.
                    await Metrics.cloud_query(time.monotonic() - started)
                logger.debug(f"mySigen {operation.__name__} returned: {result}")
                await Metrics.cloud_availability(True)
                return result
            except SigenergyCloudRateLimitError as exc:
                await Metrics.cloud_query_error(rate_limited=True)
                # A rate-limit response proves the API is reachable even though
                # it did not accept this request.
                await Metrics.cloud_availability(True)
                raise CloudControlRateLimitedError(str(exc)) from exc
            except SigenergyCloudAuthError as exc:
                await Metrics.cloud_query_error(auth=True)
                if attempt == 0:
                    await self._reconnect(generation)
                    generation = self._connection_generation
                    continue
                await self._invalidate_connection(generation)
                raise CloudControlAuthError(str(exc)) from exc
            except ValueError as exc:
                await Metrics.cloud_query_error()
                if reject_api_errors:
                    raise CloudControlRejectedError(str(exc)) from exc
                raise
            except SigenergyCloudAPIError as exc:
                await Metrics.cloud_query_error()
                # Any well-formed non-5xx response proves availability, whether
                # it rejects a command or reports an application-level error.
                # Server errors and malformed responses indicate an outage.
                await Metrics.cloud_availability(_api_error_indicates_availability(exc))
                if reject_api_errors:
                    raise CloudControlRejectedError(str(exc)) from exc
                raise CloudControlUnavailableError(str(exc)) from exc
            except (ClientError, SigenergyCloudError, OSError, TimeoutError) as exc:
                await Metrics.cloud_query_error()
                # A transport failure says nothing about whether the server has
                # invalidated the authenticated session. Preserve it so the next
                # operation can retry without an avoidable password login and
                # station discovery, while reporting degraded reachability.
                await Metrics.cloud_availability(False)
                raise CloudControlUnavailableError(str(exc)) from exc
            except Exception:
                # Malformed or otherwise unexpected vendor responses are still
                # failed queries even when their exception is not normalized.
                await Metrics.cloud_query_error()
                await Metrics.cloud_availability(False)
                raise
        raise AssertionError("cloud operation retry loop exhausted")

    async def available_operational_modes(self) -> dict[str, Any]:
        return await self._cloud_operation(self._client.available_operational_modes)

    async def get_operational_mode(self) -> tuple[int, int]:
        return await self._cloud_operation(self._client.get_operational_mode)

    async def set_operational_mode(self, mode: int, profile_id: int = -1) -> dict[str, Any]:
        return await self._cloud_operation(lambda: self._client.set_operational_mode(mode, profile_id))

    async def grid_export_limit(self) -> dict[str, Any]:
        return await self._cloud_operation(self._client.grid_export_limit)

    async def set_grid_export_limit(self, limit_kw: float, *, enabled: bool = True) -> dict[str, Any]:
        return await self._cloud_operation(lambda: self._client.set_grid_export_limit(limit_kw, enabled=enabled))

    async def grid_import_limit(self) -> dict[str, Any]:
        return await self._cloud_operation(self._client.grid_import_limit)

    async def set_grid_import_limit(self, limit_kw: float, *, enabled: bool = True) -> dict[str, Any]:
        return await self._cloud_operation(lambda: self._client.set_grid_import_limit(limit_kw, enabled=enabled))

    async def grid_connection_limit(self) -> dict[str, Any]:
        return await self._cloud_operation(self._client.grid_connection_limit)

    async def set_grid_connection_limit(self, limit_a: float, *, enabled: bool = True) -> dict[str, Any]:
        return await self._cloud_operation(lambda: self._client.set_grid_connection_limit(limit_a, enabled=enabled))

    async def battery_power_limit(self) -> dict[str, Any]:
        return await self._cloud_operation(self._client.battery_power_limit)

    async def set_battery_power_limit(self, *, max_charge_kw: float | None, max_discharge_kw: float | None) -> dict[str, Any]:
        return await self._cloud_operation(
            lambda: self._client.set_battery_power_limit(
                max_charge_kw=max_charge_kw,
                max_discharge_kw=max_discharge_kw,
            )
        )

    async def solar_power_limit(self) -> dict[str, Any]:
        return await self._cloud_operation(self._client.solar_power_limit)

    async def set_solar_power_limit(self, limit_kw: float | None) -> dict[str, Any]:
        return await self._cloud_operation(lambda: self._client.set_solar_power_limit(limit_kw))

    async def battery_export_limitation(self) -> dict[str, Any]:
        return await self._cloud_operation(self._client.battery_export_limitation)

    async def set_battery_export_limitation(self, enabled: bool) -> dict[str, Any]:
        return await self._cloud_operation(lambda: self._client.set_battery_export_limitation(enabled))
