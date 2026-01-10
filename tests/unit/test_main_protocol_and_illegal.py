import types

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.sensors.const import InputType


def make_dummy_device_with_sensor(publishable=True, input_type=InputType.INPUT, count=1):
    class DummySensor:
        def __init__(self):
            self.publishable = publishable
            self.input_type = input_type
            self.count = count
            self.name = "S"
            self["platform"] = "sensor"
            self.state_topic = "t"

        def __setitem__(self, k, v):
            setattr(self, k, v)

    class DummyDevice:
        def __init__(self):
            self.name = "Dev"

        def get_sensor(self, *args, **kwargs):
            return DummySensor()

    return DummyDevice()

@pytest.mark.asyncio
async def test_test_for_0x02_illegal_data_address_marks_unpublishable(monkeypatch):

    # Prepare a device that returns a publishable sensor
    dev = types.SimpleNamespace()
    # create sensor object with publishable True and input_type
    # Make the sensor an instance of ModbusSensorMixin by monkeypatching the base and subclassing it
    class DummyBase:
        pass

    monkeypatch.setattr(main_mod, "ModbusSensorMixin", DummyBase, raising=False)

    class SensorObj(DummyBase):
        def __init__(self):
            self.publishable = True
            self.input_type = InputType.INPUT
            self.count = 1
            self.name = "Sensor"
            self.state_topic = "topic"

    sensor = SensorObj()

    device = types.SimpleNamespace(device_address=247, name="Device")
    def get_sensor(key, search_children=True):
        return sensor

    device.get_sensor = get_sensor

    # Fake modbus client that returns an object with isError() True and exception_code == 0x02
    class RR:
        def isError(self):
            return True

        @property
        def exception_code(self):
            return 0x02

    class FakeModbus:
        async def read_input_registers(self, register, count, device_id):
            return RR()

    fake_modbus = FakeModbus()

    # Run test_for_0x02_ILLEGAL_DATA_ADDRESS
    await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(fake_modbus, 0, device, 40000)

    # After running, sensor.publishable should be set to False when unpublishing occurs
    s = device.get_sensor(f"{Config.home_assistant.unique_id_prefix}_0_{device.device_address:03d}_40000", search_children=True)
    assert s.publishable is False


@pytest.mark.asyncio
async def test_test_for_0x02_illegal_data_address_handles_exceptions(monkeypatch):
    device = types.SimpleNamespace(device_address=247, name="Device2")
    class DummyBase2:
        pass

    monkeypatch.setattr(main_mod, "ModbusSensorMixin", DummyBase2, raising=False)

    class SensorObj(DummyBase2):
        def __init__(self):
            self.publishable = True
            self.input_type = InputType.HOLDING
            self.count = 2
            self.name = "Sensor2"
            self.state_topic = "topic2"

    sensor2 = SensorObj()
    device.get_sensor = lambda *a, **k: sensor2

    class FakeModbusErr:
        async def read_holding_registers(self, register, count, device_id):
            raise Exception("comm error")

    fake_modbus = FakeModbusErr()

    await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(fake_modbus, 0, device, 40001)

    s = device.get_sensor(f"{Config.home_assistant.unique_id_prefix}_0_{device.device_address:03d}_40001", search_children=True)
    assert s.publishable is False


@pytest.mark.asyncio
async def test_make_plant_and_inverter_protocol_probe_sets_default(monkeypatch):
    # Monkeypatch sensor classes to simple factories to avoid heavy Sensor init
    class DummySensorFactory:
        def __init__(self, *a, **k):
            pass

    for sym in ("InverterSerialNumber", "InverterModel", "InverterFirmwareVersion", "PVStringCount", "OutputType", "PACKBCUCount", "PlantRatedChargingPower", "PlantRatedDischargingPower"):
        monkeypatch.setattr(main_mod, sym, DummySensorFactory)

    # Sequence of get_state returns: serial, model, firmware, strings, output_type
    seq = [
        (None, "SNX"),
        (None, "ModelY"),
        (None, "FW1"),
        (None, 2.0),
        (None, 0),
        (None, 0),
    ]
    calls = {"i": 0}

    async def fake_get_state(sensor, modbus_client, device, raw=False, default_value=None):
        i = calls["i"]
        calls["i"] += 1
        if i < len(seq):
            return seq[i]
        # default fallback for any additional probes
        return (None, default_value if default_value is not None else 0)

    monkeypatch.setattr(main_mod, "get_state", fake_get_state)

    # Fake modbus client where read_input_registers raises (no registers found)
    class FakeModbus:
        def __init__(self):
            self.comm_params = types.SimpleNamespace(host="fakehost", port=1234)

        async def read_input_registers(self, register, count, device_id):
            raise Exception("not found")

    fake_modbus = FakeModbus()

    # Capture protocol passed to PowerPlant by monkeypatching it
    captured = {}

    class DummyPlant:
        def __init__(self, plant_index, device_type, protocol, *a, **k):
            captured["protocol"] = protocol
            self.protocol_version = protocol
            self.unique_id = "plant-uid"

    class DummyInverter:
        def __init__(self, *a, **k):
            self.unique_id = "inv-uid"

    monkeypatch.setattr(main_mod, "PowerPlant", DummyPlant)
    monkeypatch.setattr(main_mod, "Inverter", DummyInverter)
    monkeypatch.setattr(main_mod.DeviceType, "create", lambda mdl: types.SimpleNamespace(has_grid_code_interface=False))

    inv, plant = await main_mod.make_plant_and_inverter(0, fake_modbus, 1, None)

    # Protocol should be set to Protocol.V1_8 when probing finds nothing
    assert captured.get("protocol") == main_mod.Protocol.V1_8
    assert plant.protocol_version == main_mod.Protocol.V1_8
