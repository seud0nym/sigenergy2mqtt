import asyncio

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.main.thread_config import ThreadConfig, thread_config_registry


def test_threadconfigfactory_get_config_ipv4_and_hostname(monkeypatch):
    # Reset factory cache
    thread_config_registry.clear()

    ThreadConfig.create("1.2.3.4", 502)
    cfg = thread_config_registry.get_config("1.2.3.4", 502)
    assert isinstance(cfg, ThreadConfig)
    assert cfg.name == "Modbus@01020304"

    # Non-standard port includes hex port
    ThreadConfig.create("1.2.3.4", 1500)
    cfg2 = thread_config_registry.get_config("1.2.3.4", 1500)
    assert cfg2.name.endswith(":5DC")

    # Non-IP hostname preserved
    ThreadConfig.create("my-host", 502)
    cfg3 = thread_config_registry.get_config("my-host", 502)
    assert "my-host" in cfg3.name


def test_threadconfig_properties_and_methods(monkeypatch):
    tc = ThreadConfig.create(name="", host="1.1.1.1", port=502)
    # description should fall back to url when name empty
    assert tc.description == tc.url
    assert tc.url == "modbus://1.1.1.1:502"

    # description with space name
    tc.name = "  "
    assert tc.description == tc.url

    # description with name
    tc.name = "MyName"
    assert tc.description == "MyName"

    # Create a Device and attach to ThreadConfig
    dev = Device("D1", 0, "uid-d1", "mf", "mdl", Protocol.N_A)
    tc.add_device(dev)
    assert dev in tc.devices
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

    # Test reapply_sensor_overrides invokes sensor.apply_sensor_overrides
    called = {}

    class FakeSensor:
        def apply_sensor_overrides(self, registers):
            called["ok"] = registers

    dev.all_sensors = {"s1": FakeSensor()}
    dev.registers = {"r": 1}
    tc.reapply_sensor_overrides()
    assert called.get("ok") == dev.registers


def test_threadconfig_requires_host_or_name() -> None:
    try:
        ThreadConfig.create(name=" ", host="", port=502)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "host or name" in str(exc)


def test_threadconfig_invalid_port_rejected() -> None:
    for bad_port in (-1, 65536):
        try:
            ThreadConfig.create(name="x", host="1.2.3.4", port=bad_port)
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "Port" in str(exc)


def test_threadconfig_online_true_is_rejected() -> None:
    tc = ThreadConfig.create(name="x", host="1.2.3.4", port=502)
    try:
        tc.online(True)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Use a Future" in str(exc)


def test_threadconfig_registry_caches_first_timeout_and_retries() -> None:
    thread_config_registry.clear()

    ThreadConfig.create("10.0.0.1", 1502, timeout=2.5, retries=7)
    first = thread_config_registry.get_config("10.0.0.1", 1502)
    assert first.timeout == 2.5
    assert first.retries == 7

    first.timeout = 9.9
    first.retries = 0

    second = thread_config_registry.get_config("10.0.0.1", 1502)

    assert first is second
    assert second.timeout == 9.9
    assert second.retries == 0


def test_threadconfig_registry_get_all_returns_snapshot() -> None:
    thread_config_registry.clear()

    ThreadConfig.create("10.0.0.1", 502)
    snapshot = thread_config_registry.get_all()

    ThreadConfig.create("10.0.0.2", 502)

    assert len(snapshot) == 1
    assert len(thread_config_registry.get_all()) == 2
