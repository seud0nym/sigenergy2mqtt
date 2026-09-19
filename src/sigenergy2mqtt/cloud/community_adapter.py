"""Adapter for the vendored, unofficial mySigen app API."""

from datetime import timedelta
from typing import Any, Awaitable, Callable, TypeVar

from .exceptions import (
    BatteryControlAuthError,
    BatteryControlRateLimitedError,
    BatteryControlRejectedError,
    BatteryControlUnavailableError,
    BatteryControlUnsupportedError,
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


class CommunityCloudAdapter:
    """Translate domain commands to the unofficial, vendored cloud client."""

    def __init__(self, username: str, password: str, region: str) -> None:
        self._client = SigenergyCloudClient(username, password, region=region)
        self._connected = False

    @property
    def capabilities(self) -> Capabilities:
        return _CAPABILITIES

    async def connect(self) -> None:
        if self._connected:
            return
        try:
            await self._client.connect()
        except SigenergyCloudAuthError as exc:
            raise BatteryControlAuthError(str(exc)) from exc
        except SigenergyCloudRateLimitError as exc:
            raise BatteryControlRateLimitedError(str(exc)) from exc
        except (SigenergyCloudError, OSError, TimeoutError) as exc:
            raise BatteryControlUnavailableError(str(exc)) from exc
        self._connected = True

    async def close(self) -> None:
        await self._client.close()
        self._connected = False

    async def set_instant_override(self, command: InstantOverrideCommand) -> None:
        unsupported = []
        if command.power_kw is not None:
            unsupported.append("power limit")
        if (
            command.charge_priority is not None
            or command.discharge_priority is not None
        ):
            unsupported.append("source priority")
        if command.starts_at is not None:
            unsupported.append("scheduled start")
        if unsupported:
            raise BatteryControlUnsupportedError(
                f"Community backend does not support {', '.join(unsupported)}"
            )
        if (
            not self.capabilities.min_duration
            <= command.duration
            <= self.capabilities.max_duration
        ):
            raise BatteryControlRejectedError(
                "Duration must be between 1 and 1440 minutes"
            )
        duration_minutes = round(command.duration.total_seconds() / 60)
        await self.connect()
        try:
            await self._client.set_instant_manual_control(
                _MODE_TO_APP_CODE[command.mode], duration_minutes=duration_minutes
            )
        except SigenergyCloudRateLimitError as exc:
            raise BatteryControlRateLimitedError(str(exc)) from exc
        except SigenergyCloudAuthError as exc:
            self._connected = False
            raise BatteryControlAuthError(str(exc)) from exc
        except (ValueError, SigenergyCloudAPIError) as exc:
            raise BatteryControlRejectedError(str(exc)) from exc
        except (SigenergyCloudError, OSError, TimeoutError) as exc:
            raise BatteryControlUnavailableError(str(exc)) from exc

    async def clear_instant_override(self) -> None:
        await self.connect()
        try:
            await self._client.disable_instant_manual_control()
        except SigenergyCloudRateLimitError as exc:
            raise BatteryControlRateLimitedError(str(exc)) from exc
        except SigenergyCloudAuthError as exc:
            self._connected = False
            raise BatteryControlAuthError(str(exc)) from exc
        except (SigenergyCloudError, OSError, TimeoutError) as exc:
            raise BatteryControlUnavailableError(str(exc)) from exc

    async def instant_control_status(self) -> InstantControlStatus:
        await self.connect()
        try:
            status = await self._client.instant_manual_control()
        except SigenergyCloudRateLimitError as exc:
            raise BatteryControlRateLimitedError(str(exc)) from exc
        except SigenergyCloudAuthError as exc:
            self._connected = False
            raise BatteryControlAuthError(str(exc)) from exc
        except (SigenergyCloudError, OSError, TimeoutError) as exc:
            raise BatteryControlUnavailableError(str(exc)) from exc
        return InstantControlStatus(
            enabled=status.enabled,
            mode=_APP_CODE_TO_MODE.get(status.mode)
            if status.mode is not None
            else None,
            ends_at=float(status.end_time) if status.end_time is not None else None,
        )

    async def _operational_mode_operation(
        self, operation: Callable[[], Awaitable[_T]]
    ) -> _T:
        await self.connect()
        try:
            return await operation()
        except SigenergyCloudRateLimitError as exc:
            raise BatteryControlRateLimitedError(str(exc)) from exc
        except SigenergyCloudAuthError as exc:
            self._connected = False
            raise BatteryControlAuthError(str(exc)) from exc
        except (SigenergyCloudError, OSError, TimeoutError) as exc:
            raise BatteryControlUnavailableError(str(exc)) from exc

    async def available_operational_modes(self) -> dict[str, Any]:
        return await self._operational_mode_operation(
            self._client.available_operational_modes
        )

    async def get_operational_mode(self) -> tuple[int, int]:
        return await self._operational_mode_operation(self._client.get_operational_mode)

    async def set_operational_mode(
        self, mode: int, profile_id: int = -1
    ) -> dict[str, Any]:
        return await self._operational_mode_operation(
            lambda: self._client.set_operational_mode(mode, profile_id)
        )

    async def grid_export_limit(self) -> dict[str, Any]:
        return await self._operational_mode_operation(self._client.grid_export_limit)

    async def set_grid_export_limit(
        self, limit_kw: float, *, enabled: bool = True
    ) -> dict[str, Any]:
        return await self._operational_mode_operation(
            lambda: self._client.set_grid_export_limit(limit_kw, enabled=enabled)
        )

    async def grid_import_limit(self) -> dict[str, Any]:
        return await self._operational_mode_operation(self._client.grid_import_limit)

    async def set_grid_import_limit(
        self, limit_kw: float, *, enabled: bool = True
    ) -> dict[str, Any]:
        return await self._operational_mode_operation(
            lambda: self._client.set_grid_import_limit(limit_kw, enabled=enabled)
        )

    async def grid_connection_limit(self) -> dict[str, Any]:
        return await self._operational_mode_operation(
            self._client.grid_connection_limit
        )

    async def set_grid_connection_limit(
        self, limit_a: float, *, enabled: bool = True
    ) -> dict[str, Any]:
        return await self._operational_mode_operation(
            lambda: self._client.set_grid_connection_limit(limit_a, enabled=enabled)
        )

    async def battery_power_limit(self) -> dict[str, Any]:
        return await self._operational_mode_operation(self._client.battery_power_limit)

    async def set_battery_power_limit(
        self, *, max_charge_kw: float | None, max_discharge_kw: float | None
    ) -> dict[str, Any]:
        return await self._operational_mode_operation(
            lambda: self._client.set_battery_power_limit(
                max_charge_kw=max_charge_kw,
                max_discharge_kw=max_discharge_kw,
            )
        )

    async def solar_power_limit(self) -> dict[str, Any]:
        return await self._operational_mode_operation(self._client.solar_power_limit)

    async def set_solar_power_limit(self, limit_kw: float | None) -> dict[str, Any]:
        return await self._operational_mode_operation(
            lambda: self._client.set_solar_power_limit(limit_kw)
        )

    async def battery_export_limitation(self) -> dict[str, Any]:
        return await self._operational_mode_operation(
            self._client.battery_export_limitation
        )

    async def set_battery_export_limitation(self, enabled: bool) -> dict[str, Any]:
        return await self._operational_mode_operation(
            lambda: self._client.set_battery_export_limitation(enabled)
        )
