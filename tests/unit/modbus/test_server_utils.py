import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

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
    block = server.CustomDataBlock(device_address=1, mqtt_client=None, latency_budget=server.LatencyBudget())

    string_sensor = FakeSensor(address=10, count=4, data_type=ModbusClientMixin.DATATYPE.STRING)
    block.addresses[string_sensor.address] = string_sensor
    block._set_value(string_sensor, "ab")
    assert [block._initial_registers[addr] for addr in range(10, 14)] == ModbusClientMixin.convert_to_registers("ab", ModbusClientMixin.DATATYPE.STRING) + [0, 0, 0]

    phase_voltage_sensor = FakeSensor(address=PhaseVoltage.PHASE_A_ADDRESS, count=1)
    block.addresses[phase_voltage_sensor.address] = phase_voltage_sensor
    block._set_value(phase_voltage_sensor, 230)
    assert block._initial_registers[PhaseVoltage.PHASE_A_ADDRESS] == 230
    block.addresses[PhaseVoltage.PHASE_B_ADDRESS] = FakeSensor(address=PhaseVoltage.PHASE_B_ADDRESS, count=1)
    block.addresses[PhaseVoltage.PHASE_C_ADDRESS] = FakeSensor(address=PhaseVoltage.PHASE_C_ADDRESS, count=1)
    assert block._initial_registers[PhaseVoltage.PHASE_B_ADDRESS] == 230
    assert block._initial_registers[PhaseVoltage.PHASE_C_ADDRESS] == 230

    phase_current_sensor = FakeSensor(address=PhaseCurrent.PHASE_A_ADDRESS, count=1)
    block.addresses[phase_current_sensor.address] = phase_current_sensor
    block._set_value(phase_current_sensor, 7)
    block.addresses[PhaseCurrent.PHASE_B_ADDRESS] = FakeSensor(address=PhaseCurrent.PHASE_B_ADDRESS, count=1)
    block.addresses[PhaseCurrent.PHASE_C_ADDRESS] = FakeSensor(address=PhaseCurrent.PHASE_C_ADDRESS, count=1)
    assert block._initial_registers[PhaseCurrent.PHASE_B_ADDRESS] == 7
    assert block._initial_registers[PhaseCurrent.PHASE_C_ADDRESS] == 7

    block._written_addresses.add(55)
    locked_sensor = FakeSensor(address=55, count=1)
    block.addresses[locked_sensor.address] = locked_sensor
    block._set_value(locked_sensor, 999)
    assert 55 not in block._initial_registers


def test_get_initial_value_covers_primary_branches(monkeypatch):
    block = server.CustomDataBlock(device_address=1, mqtt_client=None, latency_budget=server.LatencyBudget())

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
    block = server.CustomDataBlock(device_address=1, mqtt_client=mqtt_client, latency_budget=server.LatencyBudget())

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
        block = server.CustomDataBlock(device_address=1, mqtt_client=None, latency_budget=server.LatencyBudget())

        guarded_sensor = FakeSensor(address=200)
        guarded_sensor._availability_control_sensor = RemoteEMS(0)
        block.addresses[200] = guarded_sensor

        class ReservedDummy(FakeSensor):
            pass

        reserved_sensor = ReservedDummy(address=250)
        block.add_sensor(reserved_sensor)

        action = block._make_device_action()
        mock_server = Mock()
        mock_server.context = Mock()

        async def mock_get_values(_unit, _fc, addr, count):
            return [block._initial_registers.get(addr + i, 0) for i in range(count)]

        async def mock_set_values(_unit, _fc, addr, vals):
            for i, v in enumerate(vals):
                block._initial_registers[addr + i] = v

        mock_server.context.async_getValues.side_effect = mock_get_values
        mock_server.context.async_setValues.side_effect = mock_set_values
        block._server = mock_server

        # Test RemoteEMS guard: disable RemoteEMS then try to write to guarded sensor
        block._initial_registers[RemoteEMS.ADDRESS] = 0
        result = await action(0x06, 0, 200, 1, [0], [55])
        assert result == ExcCodes.ILLEGAL_ADDRESS

        # Enable RemoteEMS then try to write again
        block._initial_registers[RemoteEMS.ADDRESS] = 1
        result = await action(0x06, 0, 200, 1, [0], [77])
        assert result is None

        # Specific requests for reserved registers must return ILLEGAL_ADDRESS
        result = await action(0x03, 0, 250, 1, [0], None)
        assert result == ExcCodes.ILLEGAL_ADDRESS

        # Bulk read spanning beyond reserved should be allowed
        result = await action(0x03, 0, 250, 2, [0, 0], None)
        assert result is None

        block.addresses[300] = FakeSensor(address=300, count=1)
        block.addresses[301] = FakeSensor(address=301, count=1)
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
        block = server.CustomDataBlock(device_address=1, mqtt_client=None, latency_budget=server.LatencyBudget())
        block.addresses[GridStatus.ADDRESS] = FakeSensor(address=GridStatus.ADDRESS)
        
        mock_server = Mock()
        mock_server.context = Mock()
        async def mock_set_values(_unit, _fc, addr, vals):
            for i, v in enumerate(vals):
                block._initial_registers[addr + i] = v
        mock_server.context.async_setValues.side_effect = mock_set_values
        block._server = mock_server

        task = asyncio.create_task(server.simulate_grid_outage(block, wait_for_seconds=0, duration_seconds=0))
        await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert block._initial_registers.get(GridStatus.ADDRESS) in (0, 1)

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


def test_pv_string_mirroring_and_action_mirroring():
    async def _run():
        block = server.CustomDataBlock(device_address=1, mqtt_client=None, latency_budget=server.LatencyBudget())

        # Setup PV String 1 and 2
        pv1_v = FakeSensor(name="PV String 1 Voltage", address=31027)
        pv2_v = FakeSensor(name="PV String 2 Voltage", address=31031)
        block.add_sensor(pv1_v)
        block.add_sensor(pv2_v)

        # Test initial cache mirroring
        block._set_value(pv1_v, 400)
        assert block._initial_registers[31027] == 400
        assert block._initial_registers[31031] == 400

        # Setup Phase Mirroring sensors
        block.addresses[PhaseVoltage.PHASE_A_ADDRESS] = FakeSensor(address=PhaseVoltage.PHASE_A_ADDRESS)
        block.addresses[PhaseVoltage.PHASE_B_ADDRESS] = FakeSensor(address=PhaseVoltage.PHASE_B_ADDRESS)

        action = block._make_device_action()
        mock_server = Mock()
        mock_server.context = Mock()

        async def mock_set_values(_unit, _fc, addr, vals):
            for i, v in enumerate(vals):
                block._initial_registers[addr + i] = v

        mock_server.context.async_setValues.side_effect = mock_set_values
        block._server = mock_server

        # Test action-based mirroring for Phase A
        await action(0x10, 0, PhaseVoltage.PHASE_A_ADDRESS, 1, [0], [235])
        assert block._initial_registers[PhaseVoltage.PHASE_B_ADDRESS] == 235

        # Test action-based mirroring for PV String 1
        await action(0x10, 0, 31027, 1, [400], [410])
        assert block._initial_registers[31031] == 410

    asyncio.run(_run())


def test_build_sim_device_logic():
    block = server.CustomDataBlock(device_address=3, mqtt_client=None, latency_budget=server.LatencyBudget())

    # Sensor with value > 32767 to test signed conversion
    s = FakeSensor(address=100, count=1)
    block.addresses[100] = s
    block._initial_registers[100] = 60000  # 0xEA60

    sim_device = block.build_sim_device()
    assert sim_device.id == 3

    # Check SimData values
    sim_data = sim_device.simdata[0]
    assert sim_data.address == 100
    # 60000 - 65536 = -5536
    assert sim_data.values == [-5536]


def test_latency_budget_increments():
    async def _run():
        budget = server.LatencyBudget()
        block = server.CustomDataBlock(device_address=1, mqtt_client=None, latency_budget=budget)
        action = block._make_device_action()

        await action(0x03, 0, 100, 1, [0], None)
        assert budget.request_count == 1
        assert budget.total_sleep_ms >= server.DELAY_MIN

    asyncio.run(_run())
