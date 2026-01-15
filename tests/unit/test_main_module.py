import asyncio
import logging
import types

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.main import main as main_mod


def test_configure_logging_adjusts_levels(tmp_path, monkeypatch):
    # Ensure different levels are set and configure_logging applies them
    monkeypatch.setattr(Config, "log_level", logging.INFO, raising=False)
    monkeypatch.setattr(Config, "mqtt", Config.mqtt, raising=False)
    monkeypatch.setattr(Config.mqtt, "log_level", logging.DEBUG, raising=False)
    monkeypatch.setattr(Config, "pvoutput", Config.pvoutput, raising=False)
    monkeypatch.setattr(Config.pvoutput, "log_level", logging.ERROR, raising=False)
    # Avoid dependency on Config.modbus during logging configuration
    import logging as _logging

    monkeypatch.setattr(Config, "get_modbus_log_level", classmethod(lambda cls: _logging.INFO), raising=False)

    # Ensure root is not at desired level to exercise the change path
    root = logging.getLogger("root")
    root.setLevel(logging.WARNING)

    main_mod.configure_logging()

    assert logging.getLogger("root").level == Config.log_level
    assert logging.getLogger("paho.mqtt").level == Config.mqtt.log_level
    assert logging.getLogger("pvoutput").level == Config.pvoutput.log_level


@pytest.mark.asyncio
async def test_get_state_success_and_failure():
    class FakeSensor:
        def __init__(self, value=None, exc=None):
            self._value = value
            self._exc = exc

        async def get_state(self, **kwargs):
            if self._exc:
                raise self._exc
            return self._value

    class CommParams:
        def __init__(self, host, port):
            self.host = host
            self.port = port

    class FakeModbusClient:
        def __init__(self, host="127.0.0.1", port=502):
            self.comm_params = CommParams(host, port)

    modbus = FakeModbusClient(host="1.2.3.4", port=1502)

    sensor_ok = FakeSensor(value=123)
    sensor, value = await main_mod.get_state(sensor_ok, modbus, "dev")
    assert sensor is sensor_ok
    assert value == 123

    sensor_fail = FakeSensor(exc=RuntimeError("boom"))
    sensor2, value2 = await main_mod.get_state(sensor_fail, modbus, "dev", default_value=42)
    assert sensor2 is sensor_fail
    assert value2 == 42


@pytest.mark.asyncio
async def test_make_dc_charger_and_ac_charger_with_monkeypatch(monkeypatch):
    # Monkeypatch DCCharger to a lightweight dummy
    class DummyDC:
        def __init__(self, plant_index, device_address, protocol_version):
            self.plant_index = plant_index
            self.device_address = device_address
            self.protocol_version = protocol_version
            self.via_device = None

    monkeypatch.setattr(main_mod, "DCCharger", DummyDC)

    dc = await main_mod.make_dc_charger(1, 5, main_mod.Protocol.N_A, "inv-id")
    assert isinstance(dc, DummyDC)
    assert dc.via_device == "inv-id"

    # Test make_ac_charger by monkeypatching get_state and ACCharger
    async def fake_get_state(sensor, modbus_client, device):
        # return the sensor object and a numeric value
        return sensor, 7.5

    class DummyAC:
        def __init__(self, plant_index, device_address, protocol_version, ib_value, rc_value, input_breaker, rated_current):
            self.plant_index = plant_index
            self.device_address = device_address
            self.protocol_version = protocol_version
            self.ib_value = ib_value
            self.rc_value = rc_value
            self.via_device = None

    monkeypatch.setattr(main_mod, "get_state", fake_get_state)
    monkeypatch.setattr(main_mod, "ACCharger", DummyAC)

    # call make_ac_charger - modbus_client can be None because fake_get_state ignores it
    ac = await main_mod.make_ac_charger(2, None, 8, types.SimpleNamespace(unique_id="plant-uid", protocol_version=main_mod.Protocol.N_A))
    assert isinstance(ac, DummyAC)
    assert ac.via_device == "plant-uid"


@pytest.mark.asyncio
async def test_make_plant_and_inverter_with_existing_plant(monkeypatch):
    # Provide a fake get_state that returns expected values based on class name
    async def fake_get_state(sensor, modbus_client, device, raw=False, default_value=None):
        name = sensor.__class__.__name__
        mapping = {
            "InverterSerialNumber": (sensor, "SN123"),
            "InverterModel": (sensor, "ModelX"),
            "InverterFirmwareVersion": (sensor, "FW1"),
            "PVStringCount": (sensor, 2.0),
            "OutputType": (sensor, 0),
        }
        return mapping.get(name, (sensor, None))

    monkeypatch.setattr(main_mod, "get_state", fake_get_state)

    class DummyInverter:
        def __init__(self, *args, **kwargs):
            self.unique_id = "inv-uid"

    monkeypatch.setattr(main_mod, "Inverter", DummyInverter)
    # Ensure DeviceType.create returns a HybridInverter instance
    monkeypatch.setattr(main_mod.DeviceType, "create", lambda mdl: main_mod.HybridInverter())

    # Avoid constructing real sensor classes which access Config.modbus; provide dummy sensor classes
    class DummySensorFactory:
        def __init__(self, *args, **kwargs):
            pass

    for sym in ("InverterSerialNumber", "InverterModel", "InverterFirmwareVersion", "PVStringCount", "OutputType", "PACKBCUCount"):
        monkeypatch.setattr(main_mod, sym, DummySensorFactory)

    # Provide a fake get_state that returns values in sequence regardless of sensor class
    call_index = {"i": 0}

    async def fake_get_state_sequence(sensor, modbus_client, device, raw=False, default_value=None):
        seq = [
            (sensor, "SN123"),
            (sensor, "ModelX"),
            (sensor, "FW1"),
            (sensor, 2.0),
            (sensor, 0),
            (sensor, (None, 0)),
        ]
        i = call_index["i"]
        call_index["i"] += 1
        return seq[i]

    monkeypatch.setattr(main_mod, "get_state", fake_get_state_sequence)

    plant = types.SimpleNamespace(protocol_version=main_mod.Protocol.V2_8, unique_id="plant-uid")
    inv, returned_plant = await main_mod.make_plant_and_inverter(0, None, 1, plant)
    assert isinstance(inv, DummyInverter)
    assert returned_plant is plant
