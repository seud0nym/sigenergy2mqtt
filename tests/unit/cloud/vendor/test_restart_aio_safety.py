"""Safety tests for restart_aio off-window guarantees."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.client import (
    SigenergyCloudClient,
)
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.errors import (
    SigenergyCloudRateLimitError,
)


class _RestartStub(SigenergyCloudClient):
    """Stub network methods used by restart_aio."""

    def __init__(self) -> None:
        # Skip real client __init__; only set fields restart_aio uses.
        self.station_id = "12025061000219"
        self.home_status_seq: list[int] = []
        self.power_on_seq: list[bool] = []
        self.topology_seq: list[dict[str, Any] | BaseException] = []
        self.power_on_posts: list[dict[str, Any]] = []
        self.toggle_calls = 0
        self._home_i = 0
        self._power_i = 0
        self._topo_i = 0

    def _station_id(self) -> str:
        return str(self.station_id)

    def _station_id_int(self) -> int:
        return int(self.station_id)

    async def _default_aio_sn(self) -> str:
        return "AIO1"

    async def get_station_home_status(self) -> dict[str, Any]:
        if self._home_i < len(self.home_status_seq):
            status = self.home_status_seq[self._home_i]
            self._home_i += 1
        else:
            status = self.home_status_seq[-1] if self.home_status_seq else 1
        return {"status": status, "statusDesc": str(status)}

    async def get_aio_power_on(self, *, sn_code: str | None = None) -> bool:
        if self._power_i < len(self.power_on_seq):
            value = self.power_on_seq[self._power_i]
            self._power_i += 1
            return value
        return self.power_on_seq[-1] if self.power_on_seq else True

    async def topology_evdc_status(self, *, dc_sn: str | None = None) -> dict[str, Any]:
        if self._topo_i >= len(self.topology_seq):
            return {
                "offline": True,
                "device_status": 1,
                "communicate_status": 1,
                "node_found": True,
            }
        item = self.topology_seq[self._topo_i]
        self._topo_i += 1
        if isinstance(item, BaseException):
            raise item
        return item

    async def toggle_aio_power(self, *, sn_code: str | None = None) -> Any:
        self.toggle_calls += 1
        return {"ok": True}

    async def _envelope(self, method: str, path: str, **kwargs: Any) -> Any:
        if path == "device/aio/on-off":
            self.power_on_posts.append(kwargs.get("json") or {})
        return {"code": 0}

    async def set_aio_power(
        self,
        power_on: bool,
        *,
        sn_code: str | None = None,
        timeout_s: float = 120.0,
        poll_s: float = 2.0,
    ) -> bool:
        # Mark subsequent home/power reads as on when force-on is requested.
        if power_on:
            self.home_status_seq.append(1)
            self.power_on_seq.append(True)
        return power_on


@pytest.mark.asyncio
async def test_restart_aio_aborts_evdc_wait_on_rate_limit() -> None:
    client = _RestartStub()
    # before home/power, then after off: off, then after on: on...
    client.home_status_seq = [1, 3, 3, 1, 1, 1, 1]
    client.power_on_seq = [True, False, True, True, True, True]
    client.topology_seq = [
        {
            "offline": False,
            "device_status": 1,
            "communicate_status": 2,
            "node_found": True,
        },
        SigenergyCloudRateLimitError("429"),
    ]

    result = await client.restart_aio(
        off_dwell_s=0.0,
        poll_s=0.0,
        timeout_s=5.0,
        wait_evdc_offline=True,
        evdc_offline_wait_s=30.0,
    )

    assert result["evdc_wait_aborted"] == "topology_rate_limited"
    assert result["evdc_offline_seen"] is False
    assert result["powered_on"] is True
    assert any(p.get("powerOn") is True for p in client.power_on_posts)
    # Must not keep polling topology after rate limit (seq exhausted at 2 reads:
    # before + one in wait, then rate limit on second wait read).
    assert client._topo_i == 2


@pytest.mark.asyncio
async def test_restart_aio_finally_powers_on_after_cancel() -> None:
    client = _RestartStub()
    client.home_status_seq = [1, 3, 3, 3, 3, 3, 1, 1]
    client.power_on_seq = [True, False, False, False, True, True]
    client.topology_seq = [
        {
            "offline": False,
            "device_status": 1,
            "communicate_status": 2,
            "node_found": True,
        },
    ]

    async def _cancel_during_wait() -> None:
        task = asyncio.create_task(
            client.restart_aio(
                off_dwell_s=0.0,
                poll_s=0.05,
                timeout_s=5.0,
                wait_evdc_offline=True,
                evdc_offline_wait_s=10.0,
            )
        )
        await asyncio.sleep(0.12)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    await _cancel_during_wait()
    assert client.toggle_calls == 1
    assert any(p.get("powerOn") is True for p in client.power_on_posts)


@pytest.mark.asyncio
async def test_restart_aio_force_on_when_status_reads_fail() -> None:
    """When status reads fail mid-cycle, finally still force-powers on."""
    client = _RestartStub()
    client.home_status_seq = [1, 3]  # before + first off poll only
    client.power_on_seq = [True, False]
    client.topology_seq = [
        {
            "offline": False,
            "device_status": 1,
            "communicate_status": 2,
            "node_found": True,
        },
    ]

    real_home = client.get_station_home_status
    calls = {"n": 0}

    async def flaky_home() -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] <= 2:
            return await real_home()
        raise SigenergyCloudRateLimitError("429 on home")

    client.get_station_home_status = flaky_home  # type: ignore[method-assign]

    with pytest.raises(SigenergyCloudRateLimitError):
        await client.restart_aio(
            off_dwell_s=0.0,
            poll_s=0.0,
            timeout_s=5.0,
            wait_evdc_offline=False,
        )
    # finally recovery must still have issued powerOn
    assert any(p.get("powerOn") is True for p in client.power_on_posts)


@pytest.mark.asyncio
async def test_restart_aio_marks_off_attempted_before_toggle_cancel() -> None:
    """Cancel during the off toggle still runs ensure-on recovery."""
    client = _RestartStub()
    client.home_status_seq = [1, 3, 1, 1]
    client.power_on_seq = [True, False, True, True]
    client.topology_seq = [
        {
            "offline": False,
            "device_status": 1,
            "communicate_status": 2,
            "node_found": True,
        },
    ]

    async def slow_toggle(*, sn_code: str | None = None) -> Any:
        client.toggle_calls += 1
        await asyncio.sleep(1.0)
        return {"ok": True}

    client.toggle_aio_power = slow_toggle  # type: ignore[method-assign]

    task = asyncio.create_task(
        client.restart_aio(
            off_dwell_s=0.0,
            poll_s=0.0,
            timeout_s=5.0,
            wait_evdc_offline=False,
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert any(p.get("powerOn") is True for p in client.power_on_posts)
