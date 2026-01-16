import sys
import time
import types

import pytest

# Prevent circular imports by stubbing heavy submodules used at import-time
sys.modules.setdefault("sigenergy2mqtt.devices", types.ModuleType("sigenergy2mqtt.devices"))
types_mod = types.ModuleType("sigenergy2mqtt.common.types")
types_mod.HybridInverter = type("HybridInverter", (), {})
types_mod.PVInverter = type("PVInverter", (), {})
sys.modules.setdefault("sigenergy2mqtt.common.types", types_mod)

from sigenergy2mqtt.common import Protocol  # noqa: E402
from sigenergy2mqtt.config import Config  # noqa: E402
from sigenergy2mqtt.sensors.base import Sensor  # noqa: E402
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass  # noqa: E402


class DummySensor(Sensor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def make_sensor(unique_suffix: str = "1") -> DummySensor:
    # Respect configured prefixes
    prefix_u = Config.home_assistant.unique_id_prefix
    prefix_o = Config.home_assistant.entity_id_prefix
    unique_id = f"{prefix_u}_test_{unique_suffix}"
    object_id = f"{prefix_o}_test_{unique_suffix}"
    return DummySensor("Test", unique_id, object_id, "W", DeviceClass.POWER, StateClass.MEASUREMENT, "mdi:power", 2.0, 2, Protocol.V2_4)


def test_apply_gain_and_precision_applies_gain_and_rounds():
    s = make_sensor()
    s.precision = 2
    s.gain = 10.0
    # value should be divided by gain and rounded to precision
    out = s._apply_gain_and_precision(123.456)
    assert isinstance(out, float)
    assert out == round(123.456 / 10.0, 2)


def test_apply_gain_and_precision_raw_returns_value():
    s = make_sensor()
    s.gain = 10.0
    out = s._apply_gain_and_precision(123.456, raw=True)
    assert out == 123.456


def test_publishable_setter_type_validation():
    s = make_sensor()
    with pytest.raises(ValueError):
        s.publishable = "yes"  # type: ignore
    # valid set
    s.publishable = False
    assert s.publishable is False


def test_publish_raw_setter_type_validation():
    s = make_sensor()
    with pytest.raises(ValueError):
        s.publish_raw = 1  # type: ignore
    s.publish_raw = True
    assert s.publish_raw is True


def test_protocol_version_setter_accepts_float_and_enum():
    s = make_sensor()
    # Accept enum
    s.protocol_version = Protocol.V2_4
    assert s.protocol_version == Protocol.V2_4
    # Accept float value corresponding to Protocol
    s.protocol_version = float(Protocol.V2_4.value)
    assert s.protocol_version == Protocol.V2_4
    # Invalid value
    with pytest.raises(AssertionError):
        s.protocol_version = "invalid"  # type: ignore


def test_latest_properties_and_state_management():
    s = make_sensor()
    # No states initially
    assert s.latest_raw_state is None
    assert s.latest_interval is None
    assert s.latest_time == 0

    # Add one state
    now = time.time()
    s._states.append((now, 10))
    assert s.latest_raw_state == 10
    assert s.latest_time == now

    # Add second state and check interval
    later = now + 5
    s._states.append((later, 20))
    assert s.latest_interval == pytest.approx(5)
    assert s.latest_raw_state == 20
