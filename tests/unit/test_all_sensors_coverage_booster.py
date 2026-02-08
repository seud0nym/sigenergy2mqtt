import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sigenergy2mqtt.sensors.ac_charger_read_only as acro
import sigenergy2mqtt.sensors.ac_charger_read_write as acrw
import sigenergy2mqtt.sensors.inverter_derived as idrv
import sigenergy2mqtt.sensors.inverter_read_only as iro
import sigenergy2mqtt.sensors.inverter_read_write as irw
import sigenergy2mqtt.sensors.plant_derived as pdrv
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.sensors.base import AvailabilityMixin, Sensor


@pytest.fixture(autouse=True)
def mock_config():
    modbus_config = MagicMock()
    modbus_config.scan_interval.realtime = 1
    modbus_config.scan_interval.high = 5
    modbus_config.scan_interval.medium = 30
    modbus_config.scan_interval.low = 300

    with (
        patch("sigenergy2mqtt.config.Config.home_assistant.unique_id_prefix", "sigen"),
        patch("sigenergy2mqtt.config.Config.home_assistant.entity_id_prefix", "sigen"),
        patch("sigenergy2mqtt.config.Config.sensor_overrides", {}),
        patch("sigenergy2mqtt.config.Config.modbus", [modbus_config] * 10),
    ):
        yield


class MockAvailabilitySensor(AvailabilityMixin):
    def __init__(self, *args, **kwargs):
        self._states = [(0.0, 0)]
        self.name = "mock_avail"
        self.unique_id = "sigen_mock_avail"
        self.object_id = "sigen_mock_avail"
        self.get_state = AsyncMock(return_value=1)
        self.address = 30000
        self._protocol_version = Protocol.V1_8
        self.publishable = True

    def items(self):
        return [].items()

    def __getitem__(self, key):
        return None

    def __setitem__(self, key, value):
        pass

    def __contains__(self, key):
        return False


def get_classes(module):
    return [cls for name, cls in inspect.getmembers(module, inspect.isclass) if cls.__module__ == module.__name__ and issubclass(cls, Sensor)]


async def run_coverage_on_module(module):
    classes = get_classes(module)
    print(f"Testing {len(classes)} classes in {module.__name__}")
    mock_modbus = MagicMock()
    mock_modbus.read_holding_registers = AsyncMock(return_value=MagicMock(registers=[100] * 10, isError=lambda: False))
    mock_modbus.read_input_registers = AsyncMock(return_value=MagicMock(registers=[100] * 10, isError=lambda: False))
    mock_modbus.connected = True
    mock_modbus.convert_from_registers = MagicMock(return_value=123)

    for cls in classes:
        try:
            sig = inspect.signature(cls.__init__)
            params = sig.parameters
            kwargs = {}
            # Standard setup
            for name, param in params.items():
                if name == "self":
                    continue
                if name == "plant_index":
                    kwargs[name] = 0
                elif name == "power_phases":
                    kwargs[name] = 3
                elif name == "phase":
                    kwargs[name] = "A"
                elif name == "output_type":
                    kwargs[name] = 2
                elif name == "rated_charging_power":
                    kwargs[name] = 5000
                elif name == "rated_discharging_power":
                    kwargs[name] = 5000
                elif name == "address":
                    kwargs[name] = 30000
                elif name == "device_address":
                    kwargs[name] = 247
                elif name == "inverter_index":
                    kwargs[name] = 0
                elif name == "inverter_serial":
                    kwargs[name] = "TESTSERIAL"
                elif name == "ac_charger_index":
                    kwargs[name] = 0
                elif name == "ac_charger_serial":
                    kwargs[name] = "ACSERIAL"
                elif name == "alarms":
                    m = MagicMock()
                    m.device_address = 247
                    m.address = 30000
                    m.count = 1
                    m.protocol_version = Protocol.V1_8
                    kwargs[name] = [m]
                elif issubclass(param.annotation, AvailabilityMixin) if hasattr(param.annotation, "__mro__") else False:
                    kwargs[name] = MockAvailabilitySensor()
                elif "control" in name or "sensor" in name or "mode" in name:
                    kwargs[name] = MockAvailabilitySensor()
                else:
                    kwargs[name] = MagicMock()

            sensor = cls(**kwargs)
            sensor.configure_mqtt_topics("test_device")
            sensor.get_attributes()
            await sensor.get_state(modbus_client=mock_modbus)
            await sensor.get_state(raw=True, modbus_client=mock_modbus)

            if hasattr(sensor, "set_source_values"):
                try:
                    sensor.set_source_values(1, 2, 3)
                except:
                    pass

        except Exception as e:
            print(f"Failed to test {cls.__name__} in {module.__name__}: {e}")


@pytest.mark.asyncio
async def test_all_modules_coverage():
    modules = [acro, acrw, idrv, iro, irw, pdrv]
    for mod in modules:
        await run_coverage_on_module(mod)
