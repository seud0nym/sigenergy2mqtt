import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.constants import ExcCodes

from sigenergy2mqtt.common import DeviceClass
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, PhaseCurrent, PhaseVoltage, PowerFactor
from sigenergy2mqtt.sensors.plant_read_only import GridStatus
from sigenergy2mqtt.sensors.plant_read_write import RemoteEMS
from tests.utils import modbus_test_server as server


class FakeSensor:
    def __init__(self, **kwargs):
        defaults = {
            "name": "fake_sensor",
            "address": 100,
            "count": 1,
            "data_type": ModbusClientMixin.DATATYPE.UINT16,
            "publishable": True,
            "state_topic": "fake/topic",
            "gain": 1,
            "device_class": None,
            "debug_logging": False,
            "latest_raw_state": None,
            "input_type": 3,
            "device_address": 1,
            "platform": "sensor",
            "sanity_check": SimpleNamespace(min_raw=0, max_raw=10, delta=None),
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

    def state2raw(self, value):
        return int(value * self.gain)


def test_custom_mqtt_handler_reconnect_and_dispatches_messages():
    async def _run():
        loop = asyncio.get_running_loop()
        handler = server.CustomMqttHandler(loop)

        calls = []

        class Receiver:
            def on_value(self, topic, value, debug):
                calls.append((topic, value, debug))

        receiver = Receiver()

        client = Mock()
        handler._topics = {"sig/topic": [receiver.on_value]}

        handler.on_reconnect(client)
        handler.on_reconnect(client)
        assert handler.connected is True
        client.unsubscribe.assert_called_once_with("sig/topic")
        client.subscribe.assert_called_once_with("sig/topic")

        handler.on_message("sig/topic", " 123 ")
        await asyncio.sleep(0)
        assert calls == [("sig/topic", "123", False)]

        handler.on_message("unknown/topic", "12")
        handler.on_message("sig/topic", "")
        await asyncio.sleep(0)
        assert calls == [("sig/topic", "123", False)]

    asyncio.run(_run())


def test_custom_mqtt_handler_register_subscribes():
    loop = asyncio.new_event_loop()
    try:
        handler = server.CustomMqttHandler(loop)
        client = Mock()
        receiver = object()

        handler.register(client, "a/topic", receiver)

        assert handler._topics["a/topic"] == [receiver]
        client.subscribe.assert_called_once_with("a/topic")
    finally:
        loop.close()


def test_set_value_string_padding_and_phase_mirroring_and_written_skip():
    block = server.CustomDataBlock(device_address=1, mqtt_client=None)

    string_sensor = FakeSensor(address=10, count=4, data_type=ModbusClientMixin.DATATYPE.STRING)
    block.addresses[string_sensor.address] = string_sensor
    block._set_value(string_sensor, "ab")
    assert block.getValues(10, 4) == ModbusClientMixin.convert_to_registers("ab", ModbusClientMixin.DATATYPE.STRING) + [0, 0, 0]

    phase_voltage_sensor = FakeSensor(address=PhaseVoltage.PHASE_A_ADDRESS, count=1)
    block.addresses[phase_voltage_sensor.address] = phase_voltage_sensor
    block._set_value(phase_voltage_sensor, 230)
    assert block.getValues(PhaseVoltage.PHASE_A_ADDRESS, 1) == [230]
    block.addresses[PhaseVoltage.PHASE_B_ADDRESS] = FakeSensor(address=PhaseVoltage.PHASE_B_ADDRESS, count=1)
    block.addresses[PhaseVoltage.PHASE_C_ADDRESS] = FakeSensor(address=PhaseVoltage.PHASE_C_ADDRESS, count=1)
    assert block.getValues(PhaseVoltage.PHASE_B_ADDRESS, 1) == [230]
    assert block.getValues(PhaseVoltage.PHASE_C_ADDRESS, 1) == [230]

    phase_current_sensor = FakeSensor(address=PhaseCurrent.PHASE_A_ADDRESS, count=1)
    block.addresses[phase_current_sensor.address] = phase_current_sensor
    block._set_value(phase_current_sensor, 7)
    block.addresses[PhaseCurrent.PHASE_B_ADDRESS] = FakeSensor(address=PhaseCurrent.PHASE_B_ADDRESS, count=1)
    block.addresses[PhaseCurrent.PHASE_C_ADDRESS] = FakeSensor(address=PhaseCurrent.PHASE_C_ADDRESS, count=1)
    assert block.getValues(PhaseCurrent.PHASE_B_ADDRESS, 1) == [7]
    assert block.getValues(PhaseCurrent.PHASE_C_ADDRESS, 1) == [7]

    block._written_addresses.add(55)
    locked_sensor = FakeSensor(address=55, count=1)
    block.addresses[locked_sensor.address] = locked_sensor
    block._set_value(locked_sensor, 999)
    assert block.getValues(55, 1) == ExcCodes.ILLEGAL_ADDRESS


def test_get_initial_value_covers_primary_branches(monkeypatch):
    block = server.CustomDataBlock(device_address=1, mqtt_client=None)

    fw = FakeSensor(address=InverterFirmwareVersion.ADDRESS)
    assert block._get_initial_value(fw) == (server.TestConfig.initial_firmware, "inverter_firmware_version")

    s = FakeSensor(data_type=ModbusClientMixin.DATATYPE.STRING, latest_raw_state=None)
    assert block._get_initial_value(s) == ("string value", "string")

    s2 = FakeSensor(data_type=ModbusClientMixin.DATATYPE.STRING, latest_raw_state="abc")
    assert block._get_initial_value(s2) == ("abc", "string")

    monkeypatch.setattr(server, "randint", lambda lo, hi: lo)
    server.TestConfig.simulate_power_factor_errors = True
    try:
        pf = FakeSensor(address=PowerFactor.ADDRESS, gain=100)
        value, source = block._get_initial_value(pf)
        assert source == "power_factor"
        assert value == 645.72
    finally:
        server.TestConfig.simulate_power_factor_errors = False

    latest = FakeSensor(latest_raw_state=20, gain=10)
    assert block._get_initial_value(latest) == (2.0, "latest_raw_state")

    ts = FakeSensor(device_class=DeviceClass.TIMESTAMP)
    value, source = block._get_initial_value(ts)
    assert source == "timestamp"
    assert "T" in value

    switch = FakeSensor()
    switch.state_off = 0
    switch.state_on = 1
    assert block._get_initial_value(switch) == (0, "switch_sensor")

    with_min_max = FakeSensor(min=(3, 4), max=(9, 10))
    assert block._get_initial_value(with_min_max) == (3, "min_max")

    with_options = FakeSensor(options=["a", "b"])
    assert block._get_initial_value(with_options) == (0, "options")

    with_sanity_delta = FakeSensor()
    with_sanity_delta.sanity_check = SimpleNamespace(min_raw=10, max_raw=20, delta=2)
    assert block._get_initial_value(with_sanity_delta) == (10, "sanity_check")


def test_register_mqtt_topic_and_warning_path(caplog):
    class FakeUserData:
        def __init__(self):
            self.register = Mock()

    user_data = FakeUserData()
    mqtt_client = Mock()
    mqtt_client.user_data_get.return_value = user_data
    block = server.CustomDataBlock(device_address=1, mqtt_client=mqtt_client)

    sensor = FakeSensor(state_topic="plant/topic")
    block._register_mqtt_topic(sensor, source="latest_raw_state")
    assert block._topics["plant/topic"] is sensor
    user_data.register.assert_called_once()

    no_topic_sensor = FakeSensor()
    delattr(no_topic_sensor, "state_topic")
    with caplog.at_level("WARNING"):
        block._register_mqtt_topic(no_topic_sensor, source="latest_raw_state")
    assert "does not have a state_topic" in caplog.text

    excluded_sensor = FakeSensor(state_topic="x/y")
    block._register_mqtt_topic(excluded_sensor, source="power_factor")
    assert "x/y" not in block._topics


def test_async_set_values_remote_ems_guard_and_get_values_paths():
    async def _run():
        block = server.CustomDataBlock(device_address=1, mqtt_client=None)

        guarded_sensor = FakeSensor(address=200)
        guarded_sensor._availability_control_sensor = RemoteEMS(0)
        block.addresses[200] = guarded_sensor

        await block.async_setValues(0x06, RemoteEMS.ADDRESS, [0])
        result = await block.async_setValues(0x06, 200, [55])
        assert result == ExcCodes.ILLEGAL_ADDRESS

        await block.async_setValues(0x06, RemoteEMS.ADDRESS, [1])
        result = await block.async_setValues(0x06, 200, [77])
        assert result is None
        assert block.getValues(200, 1) == [77]

        class ReservedDummy(FakeSensor):
            pass

        block._mqtt_client = None
        reserved_sensor = ReservedDummy(address=250)
        block.add_sensor(reserved_sensor)
        assert block.getValues(250, 1) == ExcCodes.ILLEGAL_ADDRESS

        block.addresses[300] = FakeSensor(address=300, count=1)
        block.addresses[301] = FakeSensor(address=301, count=1)
        await block.async_setValues(0x06, 300, [1])
        await block.async_setValues(0x06, 301, [2])
        assert block.getValues(300, 2) == [1, 2]

    asyncio.run(_run())


def test_wait_for_server_start_retries_then_succeeds(monkeypatch):
    attempts = {"count": 0}

    class DummyWriter:
        def close(self):
            return None

        async def wait_closed(self):
            return None

    async def fake_open_connection(host, port):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionRefusedError
        return object(), DummyWriter()

    monkeypatch.setattr(asyncio, "open_connection", fake_open_connection)
    async def _run():
        assert await server.wait_for_server_start("127.0.0.1", 502, timeout=1.0) is True
        assert attempts["count"] == 3

    asyncio.run(_run())


def test_simulate_grid_outage_and_callbacks(monkeypatch):
    async def _run():
        block = server.CustomDataBlock(device_address=1, mqtt_client=None)
        block.addresses[GridStatus.ADDRESS] = FakeSensor(address=GridStatus.ADDRESS)

        task = asyncio.create_task(server.simulate_grid_outage(block, wait_for_seconds=0, duration_seconds=0))
        await asyncio.sleep(0.01)
        task.cancel()
        await task

        assert block.getValues(GridStatus.ADDRESS, 1) in ([0], [1])

        userdata = server.CustomMqttHandler(asyncio.get_running_loop())
        client = Mock()
        server.on_connect(client, userdata, None, 0, None)
        assert userdata.connected is True

        exit_calls = []
        monkeypatch.setattr(server.os, "_exit", lambda code: exit_calls.append(code))
        server.on_connect(client, userdata, None, 2, None)
        assert exit_calls == [2]

        server.on_disconnect(client, userdata, None, 1, None)
        assert userdata.connected is False

        forward_calls = []
        monkeypatch.setattr(userdata, "on_message", lambda topic, payload: forward_calls.append((topic, payload)))
        monkeypatch.setattr(userdata, "on_reconnect", lambda _client: forward_calls.append(("reconnect", "")))
        message = SimpleNamespace(topic="a/topic", payload=b"42")
        server.on_message(client, userdata, message)
        assert forward_calls == [("a/topic", "42"), ("reconnect", "")]

    asyncio.run(_run())
