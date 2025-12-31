import asyncio
import types

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry, SensorGroup
from sigenergy2mqtt.sensors.base import ReadableSensorMixin, DerivedSensor


class DummyReadable(ReadableSensorMixin):
    def __init__(self, unique_id="dummy", publishable=True, scan_interval=10, address=1, count=1, device_address=1, input_type="holding", debug_logging=False):
        # avoid calling complex base initialisers
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "publishable", publishable)
        object.__setattr__(self, "scan_interval", scan_interval)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", device_address)
        object.__setattr__(self, "input_type", input_type)
        object.__setattr__(self, "debug_logging", debug_logging)
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "latest_raw_state", None)

    def apply_sensor_overrides(self, registers):
        self._overrides_applied = True

    def configure_mqtt_topics(self, unique_id):
        self._topics_configured = unique_id

    def add_derived_sensor(self, sensor):
        self._derived_sensors[sensor.__class__.__name__] = sensor

    def get_discovery(self, mqtt):
        return {}

    async def publish(self, mqtt, modbus=None, republish=False):
        return True

    def publish_attributes(self, mqtt, clean=False):
        return True


class DummyDerived(DerivedSensor):
    def __init__(self, unique_id="derived"):
        object.__setattr__(self, "unique_id", unique_id)


def setup_module(module):
    # Minimal Config scaffolding used by Device
    Config.devices = [types.SimpleNamespace(registers={}, disable_chunking=False)]
    Config.home_assistant = types.SimpleNamespace(
        device_name_prefix="",
        unique_id_prefix="sigen",
        discovery_prefix="homeassistant",
        enabled=False,
        republish_discovery_interval=0,
    )
    Config.persistent_state_path = "."


def teardown_function(func):
    # clear device registry to avoid cross-test leakage
    DeviceRegistry._devices.clear()


def test_sensor_group_scan_interval_empty_and_with_sensors():
    sg_empty = SensorGroup()
    assert sg_empty.scan_interval == 86400

    s1 = DummyReadable(unique_id="s1", scan_interval=5)
    s2 = DummyReadable(unique_id="s2", scan_interval=10)
    sg = SensorGroup(s1, s2)
    assert sg.scan_interval == 5


def test_device_online_setter_and_rediscover():
    dev = Device("dev", 0, "uid", "mf", "mdl", Config)
    # set online future
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    dev.online = fut
    assert dev._online is fut

    # setting to False cancels and sets offline
    dev.online = False
    assert dev._online is False

    # invalid boolean True should raise
    with pytest.raises(ValueError):
        dev.online = True

    # rediscover boolean enforcement
    dev.rediscover = True
    assert dev.rediscover is True
    dev.rediscover = False
    assert dev.rediscover is False
    with pytest.raises(ValueError):
        dev.rediscover = "no"


def test_add_child_device_only_when_publishable():
    parent = Device("parent", 0, "p_uid", "mf", "mdl", Config)
    child = Device("child", 0, "c_uid", "mf", "mdl", Config)
    # non-publishable sensor
    s = DummyReadable(unique_id="s1", publishable=False)
    child._add_read_sensor(s)
    parent._add_child_device(child)
    assert child not in parent.children

    # publishable sensor
    child2 = Device("child2", 0, "c2", "mf", "mdl", Config)
    s2 = DummyReadable(unique_id="s2", publishable=True)
    child2._add_read_sensor(s2)
    parent._add_child_device(child2)
    assert child2 in parent.children


def test_add_read_sensor_rejects_non_readable_and_add_to_all_sets_parent():
    dev = Device("dev2", 0, "uid2", "mf", "mdl", Config)
    class NotReadable:
        pass

    assert dev._add_read_sensor(NotReadable()) is False

    s = DummyReadable(unique_id="s_add")
    assert dev._add_read_sensor(s) is True
    # _add_to_all_sensors called as part of add; verify parent set
    assert s.unique_id in dev.all_sensors
    assert getattr(s, "parent_device") is dev


def test_add_derived_sensor_handles_none_and_unregistered():
    dev = Device("dev3", 0, "uid3", "mf", "mdl", Config)
    derived = object()
    # all sources None -> no addition
    dev._add_derived_sensor(derived, None)

    # source provided but not registered -> won't be added
    src = DummyReadable(unique_id="missing")
    dev._add_derived_sensor(derived, src)
    # Nothing should have been added to all_sensors
    assert len(dev.all_sensors) == 0
