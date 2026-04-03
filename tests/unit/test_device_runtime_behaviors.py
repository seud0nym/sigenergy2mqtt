import asyncio
import copy
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.common import HybridInverter, Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices import ESS, ACCharger, DCCharger, Device, DeviceRegistry, Inverter, PowerPlant, PVString
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
        object.__setattr__(self, "protocol_version", Protocol.V1_8)
        object.__setattr__(self, "_publishable", publishable)
        object.__setattr__(self, "_states", [])
        object.__setattr__(self, "derived_sensors", {})
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
        object.__setattr__(self, "protocol_version", Protocol.V1_8)
        object.__setattr__(self, "debug_logging", False)


@pytest.fixture(autouse=True)
def mock_config():
    cfg = Config()
    mock_modbus = MagicMock()
    mock_modbus.registers = {}
    mock_modbus.disable_chunking = False
    mock_modbus.scan_interval.high = 60
    cfg.modbus = [mock_modbus]
    cfg.home_assistant.device_name_prefix = ""
    cfg.persistent_state_path = Path(".")

    with _swap_active_config(cfg):
        yield cfg
    DeviceRegistry.clear()


@pytest.mark.asyncio
async def test_device_online_setter_and_rediscover():
    dev = Device("dev", 0, "uid", "mf", "mdl", Protocol.V1_8)
    # set online future
    loop = asyncio.get_running_loop()
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
    dev = Device("dev3", 0, "uid3", "mf", "mdl", Protocol.V1_8)
    derived = DummyDerived()
    # all sources None -> no addition
    dev._add_derived_sensor(cast(Any, derived), None)

    # source provided but not registered -> won't be added
    src = DummyReadable(unique_id="missing")
    dev._add_derived_sensor(cast(Any, derived), cast(Any, src))
    # Nothing should have been added to all_sensors
    assert len(dev.all_sensors) == 0


def test_multi_modbus_device_naming_uses_plant_index_and_charger_sequence():
    cfg = Config()
    cfg.modbus = [cfg.modbus[0], copy.deepcopy(cfg.modbus[0])]

    with _swap_active_config(cfg):
        plant0 = PowerPlant(0, HybridInverter(), Protocol.V2_8)
        plant1 = PowerPlant(1, HybridInverter(), Protocol.V2_8)

        inverter1 = Inverter(1, 1, HybridInverter(), Protocol.V2_8, "SigenStor EC 10.0 SP", "SN123", "V01.01.113")
        ess1 = ESS(1, 1, HybridInverter(), Protocol.V2_8, "SigenStor EC 10.0 SP", "SN123")
        pv_string1 = PVString(1, 1, HybridInverter(), "SigenStor EC 10.0 SP", "SN123", 1, 31027, 31028, Protocol.V2_8)
        ac1 = ACCharger(1, 248 - 1, Protocol.V2_8, sequence_number=1, total_count=2)
        ac2 = ACCharger(0, 248 - 2, Protocol.V2_8, sequence_number=2, total_count=2)
        dc1 = DCCharger(1, 248 - 1, Protocol.V2_8, sequence_number=1, total_count=2)
        dc2 = DCCharger(0, 248 - 2, Protocol.V2_8, sequence_number=2, total_count=2)

    assert plant0["name"] == "Sigenergy Plant"
    assert plant1["name"] == "Sigenergy Plant 2"

    assert inverter1["name"].startswith("Sigenergy Plant 2 ") is False
    assert "Sigenergy Plant 2" not in ess1["name"]
    assert ess1["name"].endswith("SN123 ESS")
    assert pv_string1["name"].endswith("SN123 PV String 1")
    assert ac1["name"] == "Sigenergy AC Charger 1"
    assert ac2["name"] == "Sigenergy AC Charger 2"
    assert dc1["name"] == "Sigenergy DC Charger 1"
    assert dc2["name"] == "Sigenergy DC Charger 2"
