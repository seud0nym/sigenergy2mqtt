import asyncio
import types
from pathlib import Path
from typing import Any, cast

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry, SensorGroup
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.base import DerivedSensor, ReadableSensorMixin, Sensor


class DummyReadable(ReadableSensorMixin):
    def __init__(self, unique_id="dummy", publishable=True, scan_interval=10, address=1, count=1, device_address=1, input_type="holding", debug_logging=False):
        # avoid calling complex base initializers
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "scan_interval", scan_interval)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", device_address)
        object.__setattr__(self, "input_type", input_type)
        object.__setattr__(self, "debug_logging", debug_logging)
        object.__setattr__(self, "_publishable", publishable)
        object.__setattr__(self, "_states", [])
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)

    async def _update_internal_state(self, **kwargs) -> bool:
        return False

    def configure_mqtt_topics(self, device_id: str) -> str:
        self._topics_configured = device_id
        return ""

    def get_discovery(self, mqtt_client: mqtt.Client) -> dict:
        return {}

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None = None, republish: bool = False) -> bool:
        return True

    def publish_attributes(self, mqtt_client: mqtt.Client, clean: bool = False, **kwargs) -> None:
        return None


class DummyDerived(DerivedSensor):
    def __init__(self, unique_id="derived"):
        object.__setattr__(self, "unique_id", unique_id)


def setup_module(module):
    # Minimal Config scaffolding used by Device
    conf = cast(Any, Config)
    conf.devices = [types.SimpleNamespace(registers={}, disable_chunking=False)]
    conf.home_assistant = types.SimpleNamespace(
        device_name_prefix="",
        unique_id_prefix="sigen",
        discovery_prefix="homeassistant",
        enabled=False,
        republish_discovery_interval=0,
    )
    conf.persistent_state_path = Path(".")


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
    dev = Device("dev", 0, "uid", "mf", "mdl", Protocol.V1_8)
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
    with pytest.raises(ValueError, match="rediscover must be a bool"):
        cast(Any, dev).rediscover = "no"


def test_add_child_device_only_when_publishable():
    parent = Device("parent", 0, "p_uid", "mf", "mdl", Protocol.V1_8)
    child = Device("child", 0, "c_uid", "mf", "mdl", Protocol.V1_8)
    # non-publishable sensor
    s = DummyReadable(unique_id="s1", publishable=False)
    child._add_read_sensor(cast(Sensor, s))
    parent._add_child_device(child)
    assert child not in parent.children

    # publishable sensor
    child2 = Device("child2", 0, "c2", "mf", "mdl", Protocol.V1_8)
    s2 = DummyReadable(unique_id="s2", publishable=True)
    child2._add_read_sensor(cast(Sensor, s2))
    parent._add_child_device(child2)
    assert child2 in parent.children


def test_add_read_sensor_rejects_non_readable_and_add_to_all_sets_parent():
    dev = Device("dev2", 0, "uid2", "mf", "mdl", Protocol.V1_8)

    class NotReadable:
        pass

    assert dev._add_read_sensor(cast(Any, NotReadable())) is False

    s = DummyReadable(unique_id="s_add")
    assert dev._add_read_sensor(cast(Sensor, s)) is True
    # _add_to_all_sensors called as part of add; verify parent set
    assert s.unique_id in dev.all_sensors
    assert getattr(s, "parent_device") is dev


def test_add_derived_sensor_handles_none_and_unregistered():
    dev = Device("dev3", 0, "uid3", "mf", "mdl", Protocol.V1_8)
    derived = object()
    # all sources None -> no addition
    dev._add_derived_sensor(cast(Any, derived), None)

    # source provided but not registered -> won't be added
    src = DummyReadable(unique_id="missing")
    dev._add_derived_sensor(cast(Any, derived), cast(Any, src))
    # Nothing should have been added to all_sensors
    assert len(dev.all_sensors) == 0
