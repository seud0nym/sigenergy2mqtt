from unittest.mock import patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass


class ConcreteSensor(Sensor):
    """Concrete implementation of Sensor for testing since Sensor is abstract."""

    async def _update_internal_state(self, **kwargs):
        return True


class TestSensorBase:
    @pytest.fixture
    def sensor(self):
        # We need to ensure unique_id and object_id allow re-use or are unique per test
        # The Sensor class asserts uniqueness globally in class attributes.
        # We might need to clear _used_unique_ids and _used_object_ids between tests?
        # Let's inspect Sensor code again or just use unique values.
        # Sensor._used_unique_ids = {}
        # Sensor._used_object_ids = {}
        # Actually better to patch them if possible, or just use fresh IDs.

        # Checking Sensor.__init__ assertions:
        # unique_id must start with Config.home_assistant.unique_id_prefix (default "sigenergy_")
        # object_id must start with Config.home_assistant.entity_id_prefix (default "sigenergy_")

        # We'll rely on default config values which should be loaded/mocked.

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="Test Sensor",
                unique_id="sigenergy_test_unique_id",
                object_id="sigenergy_test_object_id",
                unit="W",
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:solar-power",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
            yield s

    def test_init(self, sensor):
        assert sensor["name"] == "Test Sensor"
        assert sensor["unique_id"] == "sigenergy_test_unique_id"
        assert sensor.gain == 1.0
        assert sensor.precision == 2
        assert sensor.protocol_version == Protocol.V2_4.value

    def test_apply_gain_and_precision(self, sensor):
        # Default gain=1.0, precision=2
        assert sensor._apply_gain_and_precision(10.1234) == 10.12
        assert sensor._apply_gain_and_precision(10) == 10

        # Change gain
        sensor._gain = 10.0
        assert sensor._apply_gain_and_precision(100.0) == 10.0  # 100 / 10 = 10

        # Change precision
        sensor._gain = 1.0
        sensor.precision = 0
        assert sensor._apply_gain_and_precision(10.6) == 11.0

        # Raw value (no gain/precision applied)
        assert sensor._apply_gain_and_precision(10.1234, raw=True) == 10.1234

    def test_configure_mqtt_topics(self, sensor):
        # Mock Config to ensure consistent behaviour
        with patch("sigenergy2mqtt.sensors.base.Config") as MockConfig:
            MockConfig.home_assistant.enabled = True
            MockConfig.home_assistant.use_simplified_topics = False
            MockConfig.home_assistant.discovery_prefix = "homeassistant"

            base_topic = sensor.configure_mqtt_topics(device_id="test_device")

            assert base_topic == "homeassistant/sensor/test_device/sigenergy_test_object_id"
            assert sensor["state_topic"] == f"{base_topic}/state"
            assert sensor["raw_state_topic"] == f"{base_topic}/raw"
            assert sensor["json_attributes_topic"] == f"{base_topic}/attributes"
            assert sensor["availability_mode"] == "all"
            assert sensor["availability"] == [{"topic": "homeassistant/device/test_device/availability"}]

    def test_properties(self, sensor):
        # publishable
        with pytest.raises(ValueError):
            sensor.publishable = "yes"  # type: ignore
        sensor.publishable = False
        assert sensor.publishable is False
        sensor.publishable = True
        assert sensor.publishable is True

        # publish_raw
        with pytest.raises(ValueError):
            sensor.publish_raw = 1  # type: ignore
        sensor.publish_raw = True
        assert sensor.publish_raw is True

        # protocol_version setter
        # Accept enum
        sensor.protocol_version = Protocol.V2_4
        assert sensor.protocol_version == Protocol.V2_4.value
        # Accept float value corresponding to Protocol
        sensor.protocol_version = float(Protocol.V2_4.value)
        assert sensor.protocol_version == Protocol.V2_4.value
        # Invalid value
        with pytest.raises(AssertionError):
            sensor.protocol_version = "invalid"  # type: ignore

    def test_latest_properties_and_state_management(self, sensor):
        import time

        # No states initially
        assert sensor.latest_raw_state is None
        assert sensor.latest_interval is None
        assert sensor.latest_time == 0

        # Add one state
        now = time.time()
        sensor._states.append((now, 10))
        assert sensor.latest_raw_state == 10
        assert sensor.latest_time == now

        # Add second state and check interval
        later = now + 5
        sensor._states.append((later, 20))
        assert sensor.latest_interval == pytest.approx(5)
        assert sensor.latest_raw_state == 20


class TestSensorLogic:
    """Additional logic tests for specific sensor behaviors."""

    def test_resettable_accumulation_negative_increase(self, tmp_path):
        from unittest.mock import MagicMock

        from sigenergy2mqtt.modbus.types import ModbusDataType
        from sigenergy2mqtt.sensors.base import EnergyLifetimeAccumulationSensor, ReadOnlySensor, Sensor

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src"
        source.latest_interval = 100.0

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyLifetimeAccumulationSensor("Accumulated", "sigenergy_acc", "sigenergy_acc", source, ModbusDataType.UINT32, "kWh", DeviceClass.ENERGY, StateClass.TOTAL, "mdi:energy", 1.0, 2)
            sensor._current_total = 100.0
            values = [(1000.0, -10.0), (1100.0, -20.0)]
            with patch("asyncio.run_coroutine_threadsafe"), patch("asyncio.get_running_loop"):
                sensor.set_source_values(source, values)
                assert sensor._current_total == 100.0

    def test_alarm_sensor_binary(self):
        from sigenergy2mqtt.sensors.base import AlarmSensor, Sensor

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ConcreteAlarm(AlarmSensor):
                def decode_alarm_bit(self, bit_position: int) -> str | None:
                    return "Error"

            sensor = ConcreteAlarm("Alarm", "sigenergy_alarm", 0, 1, 30001, Protocol.V2_4, "Equipment")
            assert sensor.state2raw("No Alarm") == 0
            assert sensor.state2raw(1) == 1

    @pytest.mark.asyncio
    async def test_alarm_combined_sensor(self):
        from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor, Sensor

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ProxyAlarm(AlarmSensor):
                def __init__(self, name, oid, addr):
                    self["name"] = name
                    self["unique_id"] = oid
                    self.device_address = 1
                    self.address = addr
                    self.count = 1
                    self.scan_interval = 10
                    self.plant_index = 0
                    self._publishable = True
                    self._states = []

                def decode_alarm_bit(self, bit_position):
                    return "Error"

                @property
                def latest_raw_state(self):
                    return self._states[-1][1] if self._states else 0

                @latest_raw_state.setter
                def latest_raw_state(self, value):
                    if self._states:
                        latest = self._states.pop()
                        self._states.append((latest[0], value))
                    else:
                        self._states.append((0, value))

                async def get_state(self, raw=False, republish=False, **kwargs):
                    return "No Alarm" if self.latest_raw_state == 0 else "Error"

            a1 = ProxyAlarm("A1", "sigenergy_a1", 30001)
            a2 = ProxyAlarm("A2", "sigenergy_a2", 30002)
            sensor = AlarmCombinedSensor("Combined", "sigenergy_combined", "sigenergy_combined", a1, a2)
            assert await sensor.get_state() == "No Alarm"
            a1._states.append((0, 1))
            assert await sensor.get_state() == "Error"

    def test_sensor_init_assertions(self):
        from sigenergy2mqtt.sensors.base import Sensor

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # We need to use DIFFERENT classes to trigger the "already used for class X" assertion
            class SensorA(Sensor):
                async def _update_internal_state(self, **kw):
                    return True

            class SensorB(Sensor):
                async def _update_internal_state(self, **kw):
                    return True

            SensorA("S1", "sigenergy_u1", "sigenergy_o1", "W", None, None, None, 1.0, 0)
            with pytest.raises(AssertionError, match="unique_id sigenergy_u1 has already been used for class SensorA"):
                SensorB("S2", "sigenergy_u1", "sigenergy_o2", "W", None, None, None, 1.0, 0)

    def test_overrides_write_only_and_fallbacks(self):
        from sigenergy2mqtt.sensors.base import Sensor, WriteOnlySensor

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # name, object_id, plant_index, device_address, address, protocol_version
            s = WriteOnlySensor("WO", "sigenergy_wo", 0, 1, 30001, Protocol.V2_4)
            assert s.publishable is True
            assert s.publish_raw is False
