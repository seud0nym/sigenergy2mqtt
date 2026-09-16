"""Adapter for the vendored, unofficial mySigen app API."""

from datetime import timedelta

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

    async def current_strategy_label(self) -> str | None:
        await self.connect()
        try:
            return await self._client.current_operational_mode()
        except SigenergyCloudRateLimitError as exc:
            raise BatteryControlRateLimitedError(str(exc)) from exc
        except SigenergyCloudAuthError as exc:
            self._connected = False
            raise BatteryControlAuthError(str(exc)) from exc
        except (SigenergyCloudError, OSError, TimeoutError) as exc:
            raise BatteryControlUnavailableError(str(exc)) from exc
