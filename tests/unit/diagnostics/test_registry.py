import asyncio
import time
from typing import Any

import pytest

from sigenergy2mqtt.diagnostics.registry import DiagnosticsRegistry


@pytest.fixture
def registry() -> DiagnosticsRegistry:
    return DiagnosticsRegistry()


def test_register_and_unregister(registry: DiagnosticsRegistry) -> None:
    def dummy() -> dict[str, Any]:
        return {"ok": True}

    registry.register("foo", dummy)
    assert "foo" in registry._providers

    registry.unregister("foo")
    assert "foo" not in registry._providers

    # unregistering twice doesn't crash
    registry.unregister("foo")


@pytest.mark.asyncio
async def test_snapshot_success(registry: DiagnosticsRegistry) -> None:
    def sync_dummy() -> dict[str, Any]:
        return {"type": "sync"}

    async def async_dummy() -> dict[str, Any]:
        return {"type": "async"}

    registry.register("s", sync_dummy)
    registry.register("a", async_dummy)

    start = time.time()
    snapshot = await registry.snapshot()
    
    assert "timestamp" in snapshot
    assert snapshot["timestamp"] >= int(start)
    assert snapshot["s"] == {"type": "sync"}
    assert snapshot["a"] == {"type": "async"}


@pytest.mark.asyncio
async def test_snapshot_provider_failure(registry: DiagnosticsRegistry) -> None:
    def broken() -> dict[str, Any]:
        raise ValueError("I am broken")
        
    def working() -> dict[str, Any]:
        return {"ok": True}

    registry.register("broken", broken)
    registry.register("working", working)

    snapshot = await registry.snapshot()
    
    assert snapshot["broken"] == {"error": "I am broken"}
    assert snapshot["working"] == {"ok": True}
