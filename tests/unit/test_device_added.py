import asyncio
from typing import Any, cast

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry, SensorGroup


def test_sensor_group_scan_interval_empty_and_non_empty():
    sg = SensorGroup()
    assert sg.scan_interval == 86400

    from sigenergy2mqtt.sensors.base import ReadableSensorMixin

    class S(ReadableSensorMixin):
        pass

    # Instantiate without calling ReadableSensorMixin.__init__
    a = S.__new__(S)
    a.scan_interval = 10
    b = S.__new__(S)
    b.scan_interval = 5
    c = S.__new__(S)
    c.scan_interval = 20

    sg = SensorGroup(a, b, c)
    assert sg.scan_interval == 5


@pytest.mark.asyncio
async def test_device_online_future_cancel(monkeypatch):
    conf = cast(Any, Config)
    orig_devices = conf.modbus

    class D:
        registers = {}

    conf.modbus = [D()]

    # Isolate DeviceRegistry
    orig_registry = DeviceRegistry._devices.copy()
    DeviceRegistry._devices = {}

    dev = Device("TDev", 0, "uid123", "mf", "mdl", Protocol.V1_8)

    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    dev.online = fut
    assert dev._online is fut

    dev.online = False
    assert dev._online is False
    assert fut.cancelled()

    # restore
    DeviceRegistry._devices = orig_registry
    conf.modbus = orig_devices


def test_device_rediscover_setter_and_type_check():
    conf = cast(Any, Config)
    orig_devices = conf.modbus

    class D:
        registers = {}

    conf.modbus = [D()]

    orig_registry = DeviceRegistry._devices.copy()
    DeviceRegistry._devices = {}

    dev = Device("TDev", 0, "u_idx", "mf", "mdl", Protocol.V1_8)
    dev.rediscover = True
    assert dev.rediscover is True
    dev.rediscover = False
    assert dev.rediscover is False
    with pytest.raises(ValueError, match="rediscover must be a bool"):
        cast(Any, dev).rediscover = "yes"

    DeviceRegistry._devices = orig_registry
    conf.modbus = orig_devices


def test_add_child_device_adds_when_publishable():
    conf = cast(Any, Config)
    orig_devices = conf.modbus

    class D:
        registers = {}

    conf.modbus = [D()]
    orig_registry = DeviceRegistry._devices.copy()
    DeviceRegistry._devices = {}

    parent = Device("Parent", 0, "p_uid", "mf", "mdl", Protocol.V1_8)
    child = Device("Child", 0, "c_uid", "mf", "mdl", Protocol.V1_8)

    # create a fake publishable sensor in child's all_sensors
    class S:
        publishable = True

    cast(Any, child).all_sensors = {"s1": S()}

    parent._add_child_device(child)
    assert child.via_device == parent.unique_id
    assert child in parent.children

    # cleanup
    DeviceRegistry._devices = orig_registry
    conf.modbus = orig_devices
