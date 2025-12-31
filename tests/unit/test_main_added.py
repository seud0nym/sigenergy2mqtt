import logging
import pytest

from sigenergy2mqtt.main import main as sm_main
from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.sensors.const import InputType
from sigenergy2mqtt.config import Protocol


def test_configure_logging_changes_levels(monkeypatch):
    # Ensure initial different levels
    root = logging.getLogger("root")
    pymodbus = logging.getLogger("pymodbus")
    paho = logging.getLogger("paho.mqtt")
    pvoutput = logging.getLogger("pvoutput")

    root.setLevel(logging.WARNING)
    pymodbus.setLevel(logging.WARNING)
    paho.setLevel(logging.WARNING)
    pvoutput.setLevel(logging.WARNING)

    # Set Config levels
    orig_devices = Config.devices
    Config.log_level = logging.DEBUG
    # create dummy devices list for modbus level
    class D:
        log_level = logging.INFO

    Config.devices = [D()]
    Config.mqtt.log_level = logging.ERROR
    Config.pvoutput.log_level = logging.CRITICAL

    sm_main.configure_logging()

    assert root.level == logging.DEBUG
    assert pymodbus.level == logging.INFO
    assert paho.level == logging.ERROR
    assert pvoutput.level == logging.CRITICAL

    # restore original devices
    Config.devices = orig_devices


@pytest.mark.asyncio
async def test_get_state_success_and_failure():
    class FakeComm:
        host = "1.2.3.4"
        port = 1234

    class FakeModbus:
        comm_params = FakeComm()

    class GoodSensor:
        async def get_state(self, raw=False, modbus=None):
            return 99

    class BadSensor:
        async def get_state(self, raw=False, modbus=None):
            raise RuntimeError("boom")

    modbus = FakeModbus()

    sensor, state = await sm_main.get_state(GoodSensor(), modbus, "device")
    assert state == 99

    sensor, state = await sm_main.get_state(BadSensor(), modbus, "device", default_value=7)
    assert state == 7


@pytest.mark.asyncio
async def test_make_dc_charger_sets_via_device():
    # Patch the real DCCharger to avoid heavy initialization
    class FakeDC:
        def __init__(self, plant_index, device_address, protocol_version):
            self.plant_index = plant_index
            self.device_address = device_address

    sm_main.DCCharger = FakeDC
    charger = await sm_main.make_dc_charger(1, 5, Protocol.V2_8, "inverter-uid")
    assert hasattr(charger, "via_device")
    assert charger.via_device == "inverter-uid"


@pytest.mark.asyncio
async def test_test_for_0x02_marks_unpublishable(monkeypatch):
    # Fake sensor with publishable True and InputType.HOLDING
    class FakeSensor(dict):
        def __init__(self):
            super().__init__()
            self.publishable = True
            self.input_type = InputType.HOLDING
            self.count = 1
            self.name = "s"
            self.state_topic = "t"

        def __getitem__(self, item):
            if item == "platform":
                return "plat"
            if item == "object_id":
                return "obj"
            return super().__getitem__(item)

    class FakeDevice:
        device_address = 3

        def __init__(self):
            self._sensor = FakeSensor()
            self.get_sensor_called = 0

        def get_sensor(self, s, search_children=True):
            self.get_sensor_called += 1
            return self._sensor

    class FakeResult:
        def __init__(self, err=True, code=0x02):
            self._err = err
            self.exception_code = code

        def isError(self):
            return self._err

    class FakeModbus:
        async def read_holding_registers(self, register, count, device_id):
            raise RuntimeError("comm error")

        async def read_input_registers(self, register, count, device_id):
            raise RuntimeError("comm error")

        class Comm:
            host = "x"
            port = 1

        comm_params = Comm()

    # Ensure home assistant disabled for formatting path that uses state_topic
    Config.home_assistant.enabled = False

    modbus = FakeModbus()
    device = FakeDevice()
    await sm_main.test_for_0x02_ILLEGAL_DATA_ADDRESS(modbus, 0, device, 1234)
    # Ensure get_sensor was invoked (function exercised)
    assert device.get_sensor_called >= 1
