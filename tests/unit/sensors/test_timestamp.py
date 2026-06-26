import logging
import asyncio
from datetime import timezone
from types import SimpleNamespace

import pytest

from sigenergy2mqtt.sensors.plant_read_only import SystemTime
from sigenergy2mqtt.sensors.base.readable import ReadOnlySensor


@pytest.fixture(autouse=True)
def patch_active_config(monkeypatch):
    cfg = SimpleNamespace(
        home_assistant=SimpleNamespace(
            entity_id_prefix="test_prefix",
            enabled=False,
            sigenergy_local_modbus_naming=False,
        )
    )
    monkeypatch.setattr("sigenergy2mqtt.config.active_config", cfg)
    yield


def make_sensor(tz=timezone.utc):
    """Create a SystemTime sensor (concrete subclass of TimestampSensor)."""
    return SystemTime(plant_index=1, tz=tz)


# ---------------------------------------------------------------------------
# get_state tests (lines 73, 74, 76, 77, 85, 86, 88, 89, 91)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_value, raw_flag, expected",
    [
        # line 73-74: raw=True → return value unchanged
        (1234567890, True, 1234567890),
        # line 73-74: raw=True with None → return None unchanged
        (None, True, None),
        # line 76-77: value == 0 → return None
        (0, False, None),
        # lines 80-91: normal conversion, UTC epoch → ISO 8601
        (1609459200, False, "2021-01-01T00:00:00+00:00"),
    ],
)
def test_get_state_variations(monkeypatch, raw_value, raw_flag, expected):
    sensor = make_sensor()

    async def fake_super_get_state(*args, **kwargs):
        return raw_value

    monkeypatch.setattr(ReadOnlySensor, "get_state", fake_super_get_state)
    result = asyncio.run(sensor.get_state(raw=raw_flag))
    assert result == expected


def test_get_state_debug_logging(monkeypatch, caplog):
    """Line 88-89: debug log is emitted when debug_logging is True."""
    sensor = make_sensor()
    sensor.debug_logging = True

    async def fake_super_get_state(*args, **kwargs):
        return 1609459200

    monkeypatch.setattr(ReadOnlySensor, "get_state", fake_super_get_state)
    caplog.set_level(logging.DEBUG)
    asyncio.run(sensor.get_state(raw=False))
    assert any("get_state" in rec.msg for rec in caplog.records)


# ---------------------------------------------------------------------------
# state2raw tests (lines 102, 103, 105, 106, 110-118, 119-121)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "state, expected",
    [
        # lines 102-103: numeric int → returned as int unchanged
        (12345, 12345),
        # lines 102-103: numeric float → truncated to int
        (12345.67, 12345),
        # lines 105-106: HA unavailable marker → 0
        ("--", 0),
        # lines 110-118: valid ISO 8601 string → converted to Unix timestamp
        ("2021-01-01T00:00:00+00:00", 1609459200),
    ],
)
def test_state2raw_valid(caplog, state, expected):
    sensor = make_sensor()
    sensor.debug_logging = True
    caplog.set_level(logging.DEBUG)
    result = sensor.state2raw(state)
    assert result == expected
    if isinstance(state, str) and state != "--":
        # lines 115-116: debug log emitted for ISO string path
        assert any("state2raw" in rec.msg for rec in caplog.records)


def test_state2raw_invalid(caplog):
    """Lines 119-121: ValueError → logs error and returns 0."""
    sensor = make_sensor()
    caplog.set_level(logging.ERROR)
    result = sensor.state2raw("not-a-timestamp")
    assert result == 0
    assert any("Invalid timestamp" in rec.msg for rec in caplog.records)
