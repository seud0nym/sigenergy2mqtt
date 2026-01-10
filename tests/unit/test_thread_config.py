import asyncio

from sigenergy2mqtt.config.protocol import Protocol
from sigenergy2mqtt.devices.device import Device
from sigenergy2mqtt.main.thread_config import ThreadConfig, ThreadConfigFactory


def test_threadconfigfactory_get_config_ipv4_and_hostname(monkeypatch):
    # Reset factory cache
    ThreadConfigFactory._configs.clear()

    cfg = ThreadConfigFactory.get_config("1.2.3.4", 502)
    assert isinstance(cfg, ThreadConfig)
    assert cfg.name == "Modbus@01020304"

    # Non-standard port includes hex port
    cfg2 = ThreadConfigFactory.get_config("1.2.3.4", 1500)
    assert cfg2.name.endswith(":5DC")

    # Non-IP hostname preserved
    cfg3 = ThreadConfigFactory.get_config("my-host", 502)
    assert "my-host" in cfg3.name


def test_threadconfig_properties_and_methods(monkeypatch):
    tc = ThreadConfig("1.1.1.1", 502, name="")
    # description should fall back to url when name empty
    assert tc.description == tc.url
    assert tc.url == "modbus://1.1.1.1:502"

    # Create a Device and attach to ThreadConfig
    dev = Device("D1", 0, "uid-d1", "mf", "mdl", Protocol.N_A)
    tc.add_device(0, dev)
    assert dev in tc.devices

    # Test online assignment using a loop-bound Future
    loop = asyncio.new_event_loop()
    try:
        fut = loop.create_future()
        tc.online(fut)
        # The device should have its _online set to the future
        assert dev._online is fut

        # Test offline clears online
        tc.offline()
        assert dev._online is False
    finally:
        loop.close()

    # Test reload_config invokes sensor.apply_sensor_overrides
    called = {}

    class FakeSensor:
        def apply_sensor_overrides(self, registers):
            called['ok'] = registers

    dev.all_sensors = {"s1": FakeSensor()}
    dev.registers = {"r": 1}
    tc.reload_config()
    assert called.get('ok') == dev.registers
