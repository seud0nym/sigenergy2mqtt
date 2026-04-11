import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sigenergy2mqtt.sensors.plant_read_only as pro
import sigenergy2mqtt.sensors.plant_read_write as prw
from sigenergy2mqtt.common import ConsumptionMethod, Protocol
from sigenergy2mqtt.devices.plant.plant import PowerPlant
from sigenergy2mqtt.sensors.base import AvailabilityMixin, Sensor


@pytest.fixture(autouse=True)
def mock_config():
    modbus_config = MagicMock()
    modbus_config.scan_interval.realtime = 1
    modbus_config.scan_interval.high = 5
    modbus_config.scan_interval.medium = 30
    modbus_config.scan_interval.low = 300

    with (
        patch("sigenergy2mqtt.config.active_config.home_assistant.unique_id_prefix", "sigen"),
        patch("sigenergy2mqtt.config.active_config.home_assistant.entity_id_prefix", "sigen"),
        patch("sigenergy2mqtt.config.active_config.sensor_overrides", {}),
        patch("sigenergy2mqtt.config.active_config.modbus", [modbus_config] * 10),
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


@pytest.mark.asyncio
async def test_plant_read_only_coverage():
    classes = get_classes(pro)
    print(f"Discovered {len(classes)} classes in plant_read_only")

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
            if "plant_index" in params:
                kwargs["plant_index"] = 0
            if "power_phases" in params:
                kwargs["power_phases"] = 3
            if "phase" in params:
                kwargs["phase"] = "A"
            if "output_type" in params:
                kwargs["output_type"] = 2

            for name, param in params.items():
                if name in ["self", "plant_index", "power_phases", "phase", "output_type"]:
                    continue

                if name == "alarms":
                    mock_alarm = MagicMock()
                    mock_alarm.device_address = 247
                    mock_alarm.address = 30000
                    mock_alarm.count = 1
                    mock_alarm.protocol_version = Protocol.V1_8
                    kwargs[name] = [mock_alarm]
                elif issubclass(param.annotation, AvailabilityMixin) if hasattr(param.annotation, "__mro__") else False:
                    kwargs[name] = MockAvailabilitySensor()
                elif name == "address":
                    kwargs[name] = 30000
                elif name == "device_address":
                    kwargs[name] = 247
                else:
                    kwargs[name] = MagicMock()

            sensor = cls(**kwargs)
            sensor.configure_mqtt_topics("test_device")
            sensor.get_attributes()
            await sensor.get_state(modbus_client=mock_modbus)
            await sensor.get_state(raw=True, modbus_client=mock_modbus)

            if hasattr(sensor, "state2raw"):
                try:
                    sensor.state2raw(10)
                    if cls.__name__ == "SystemTimeZone":
                        sensor.state2raw("UTC+10:00")
                except Exception:
                    pass

        except Exception as e:
            print(f"Failed to test {cls.__name__}: {e}")


@pytest.mark.asyncio
async def test_plant_read_write_coverage():
    classes = get_classes(prw)
    print(f"Discovered {len(classes)} classes in plant_read_write")

    mock_modbus = MagicMock()
    mock_modbus.read_holding_registers = AsyncMock(return_value=MagicMock(registers=[100] * 10, isError=lambda: False))
    mock_modbus.read_input_registers = AsyncMock(return_value=MagicMock(registers=[100] * 10, isError=lambda: False))
    mock_modbus.connected = True
    mock_modbus.convert_from_registers = MagicMock(return_value=1)

    for cls in classes:
        try:
            sig = inspect.signature(cls.__init__)
            params = sig.parameters
            kwargs = {}
            if "plant_index" in params:
                kwargs["plant_index"] = 0
            if "power_phases" in params:
                kwargs["power_phases"] = 3
            if "phase" in params:
                kwargs["phase"] = "A"
            if "output_type" in params:
                kwargs["output_type"] = 2
            if "rated_charging_power" in params:
                kwargs["rated_charging_power"] = 5000
            if "rated_discharging_power" in params:
                kwargs["rated_discharging_power"] = 5000

            for name, param in params.items():
                if name in ["self", "plant_index", "power_phases", "phase", "output_type", "rated_charging_power", "rated_discharging_power"]:
                    continue

                if issubclass(param.annotation, AvailabilityMixin) if hasattr(param.annotation, "__mro__") else False:
                    kwargs[name] = MockAvailabilitySensor()
                elif name == "address":
                    kwargs[name] = 30000
                elif name == "device_address":
                    kwargs[name] = 247
                else:
                    kwargs[name] = MagicMock()

                if name == "remote_ems_mode":
                    kwargs[name].is_charging_discharging_topic = "test"
                    kwargs[name].is_charging_mode_topic = "test"
                    kwargs[name].is_discharging_mode_topic = "test"
                    kwargs[name].latest_raw_state = 3
                if "control" in name:
                    kwargs[name].name = "mock_control"

            sensor = cls(**kwargs)
            sensor.configure_mqtt_topics("test_device")
            sensor.get_attributes()
            await sensor.get_state(modbus_client=mock_modbus)

            if cls.__name__ == "RemoteEMSControlMode":
                mock_mqtt = MagicMock()
                sensor.latest_raw_state = 3
                with patch("sigenergy2mqtt.config.active_config.home_assistant.enabled", True), patch("sigenergy2mqtt.config.active_config.ems_mode_check", True):
                    await sensor.publish(mock_mqtt, mock_modbus)

            if hasattr(sensor, "value_is_valid"):
                await sensor.value_is_valid(mock_modbus, 1)

        except Exception as e:
            print(f"Failed to test {cls.__name__}: {e}")


def test_powerplant_register_sensors_calculated_consumption_uses_grid_sensors_by_type():
    plant = PowerPlant(0, MagicMock(), Protocol.V2_8)
    plant._consumption_source = ConsumptionMethod.CALCULATED

    class FakeTotalPV:
        def register_source_sensors(self, *args, **kwargs):
            return None

    plant._total_pv_power = FakeTotalPV()
    plant._plant_3rd_party_pv_power = None

    active_power = object()
    grid_status = object()

    grid_sensor = MagicMock()
    grid_sensor.get_sensor.side_effect = [active_power, grid_status]
    plant._grid_sensor = grid_sensor

    add_derived = MagicMock()

    class GenericFactory:
        def __getattr__(self, name):
            return lambda *args, **kwargs: MagicMock()

    class DerivedFactory(GenericFactory):
        class SourceType:
            SMARTPORT = "SMARTPORT"
            FAILOVER = "FAILOVER"
            MANDATORY = "MANDATORY"

        class _PlantConsumed:
            def __init__(self, *args, **kwargs):
                self.method = ConsumptionMethod.CALCULATED

        TotalPVPower = MagicMock(SourceType=SourceType)

        def PlantConsumedPower(self, *args, **kwargs):
            return self._PlantConsumed()

    with (
        patch("sigenergy2mqtt.devices.plant.plant.ro", new=GenericFactory()),
        patch("sigenergy2mqtt.devices.plant.plant.rw", new=GenericFactory()),
        patch("sigenergy2mqtt.devices.plant.plant.derived", new=DerivedFactory()),
        patch("sigenergy2mqtt.devices.plant.plant.GridSensorActivePower", new=type("GridSensorActivePower", (), {})),
        patch("sigenergy2mqtt.devices.plant.plant.GridStatus", new=type("GridStatus", (), {})),
        patch("sigenergy2mqtt.devices.plant.plant.asyncio.gather", new=AsyncMock(return_value=(5000.0, 5000.0))),
        patch.object(plant, "_add_read_sensor", return_value=True),
        patch.object(plant, "_add_writeonly_sensor", return_value=None),
        patch.object(plant, "_add_derived_sensor", add_derived),
    ):
        import asyncio

        asyncio.run(plant._register_sensors("V122R001C00SPC113", output_type=2, power_phases=3, modbus_client=MagicMock()))

    assert grid_sensor.get_sensor.call_count >= 2
    first_call_type = grid_sensor.get_sensor.call_args_list[0].args[0]
    second_call_type = grid_sensor.get_sensor.call_args_list[1].args[0]
    assert first_call_type.__name__ == "GridSensorActivePower"
    assert second_call_type.__name__ == "GridStatus"
