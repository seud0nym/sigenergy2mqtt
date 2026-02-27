from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass, UnitOfPower


class ConcreteSensor(Sensor):
    """Concrete implementation of Sensor for testing since Sensor is abstract."""

    async def _update_internal_state(self, **kwargs):
        return True


class TestSensorBase:
    @pytest.fixture
    def sensor(self):
        cfg = Config()
        cfg.home_assistant.unique_id_prefix = "sigen"
        cfg.home_assistant.entity_id_prefix = "sigen"

        with _swap_active_config(cfg):
            with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
                s = ConcreteSensor(
                    name="Test Sensor",
                    unique_id="sigen_test_unique_id",
                    object_id="sigen_test_object_id",
                    unit=UnitOfPower.WATT,
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
        assert sensor["unique_id"] == "sigen_test_unique_id"
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
        # Use _swap_active_config to ensure consistent behaviour
        cfg = Config()
        cfg.home_assistant.enabled = True
        cfg.home_assistant.use_simplified_topics = False
        cfg.home_assistant.discovery_prefix = "homeassistant"
        with _swap_active_config(cfg):
            base_topic = sensor.configure_mqtt_topics(device_id="test_device")

            assert base_topic == "homeassistant/sensor/test_device/sigen_test_object_id"
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

        from sigenergy2mqtt.modbus.types import ModbusDataType
        from sigenergy2mqtt.sensors.base import EnergyLifetimeAccumulationSensor, ReadOnlySensor, Sensor

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src"
        source.latest_interval = 100.0

        cfg = Config()
        cfg.home_assistant.unique_id_prefix = "sigen"
        cfg.home_assistant.entity_id_prefix = "sigen"

        with _swap_active_config(cfg):
            with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
                sensor = EnergyLifetimeAccumulationSensor("Accumulated", "sigen_acc", "sigen_acc", source, ModbusDataType.UINT32, "kWh", DeviceClass.ENERGY, StateClass.TOTAL, "mdi:energy", 1.0, 2)
                sensor._current_total = 100.0
                values = [(1000.0, -10.0), (1100.0, -20.0)]
                with patch("asyncio.run_coroutine_threadsafe"), patch("asyncio.get_running_loop"):
                    sensor.set_source_values(source, values)
                    assert sensor._current_total == 100.0

    def test_alarm_sensor_binary(self):
        from sigenergy2mqtt.sensors.base import AlarmSensor, Sensor

        cfg = Config()
        cfg.home_assistant.unique_id_prefix = "sigen"
        cfg.home_assistant.entity_id_prefix = "sigen"

        with _swap_active_config(cfg):
            with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

                class ConcreteAlarm(AlarmSensor):
                    def decode_alarm_bit(self, bit_position: int) -> str | None:
                        return "Error"

                sensor = ConcreteAlarm("Alarm", "sigen_alarm", 0, 1, 30001, Protocol.V2_4, "Equipment")
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

            a1 = ProxyAlarm("A1", "sigen_a1", 30001)
            a2 = ProxyAlarm("A2", "sigen_a2", 30002)

            cfg = Config()
            cfg.home_assistant.unique_id_prefix = "sigen"
            cfg.home_assistant.entity_id_prefix = "sigen"

            with _swap_active_config(cfg):
                sensor = AlarmCombinedSensor("Combined", "sigen_combined", "sigen_combined", a1, a2)
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

            cfg = Config()
            cfg.home_assistant.unique_id_prefix = "sigen"
            cfg.home_assistant.entity_id_prefix = "sigen"

            with _swap_active_config(cfg):
                SensorA("S1", "sigen_u1", "sigen_o1", "W", None, None, None, 1.0, 0)
                with pytest.raises(AssertionError, match="unique_id sigen_u1 has already been used for class SensorA"):
                    SensorB("S2", "sigen_u1", "sigen_o2", "W", None, None, None, 1.0, 0)

    def test_overrides_write_only_and_fallbacks(self):
        from sigenergy2mqtt.sensors.base import Sensor, WriteOnlySensor

        cfg = Config()
        cfg.home_assistant.unique_id_prefix = "sigen"
        cfg.home_assistant.entity_id_prefix = "sigen"

        with _swap_active_config(cfg):
            with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
                # name, object_id, plant_index, device_address, address, protocol_version
                s = WriteOnlySensor("WO", "sigen_wo", 0, 1, 30001, Protocol.V2_4)
                assert s.publishable is True
                assert s.publish_raw is False


class TestScanInterval:
    def test_scan_interval_defaults(self):
        from sigenergy2mqtt.common import ScanIntervalDefault
        from sigenergy2mqtt.config import Config, _swap_active_config
        from sigenergy2mqtt.sensors.base.scan_interval import ScanInterval

        cfg = Config()
        cfg.modbus = []  # No plants configured

        with _swap_active_config(cfg):
            assert ScanInterval.realtime(0) == ScanIntervalDefault.REALTIME.value
            assert ScanInterval.high(0) == ScanIntervalDefault.HIGH.value
            assert ScanInterval.medium(0) == ScanIntervalDefault.MEDIUM.value
            assert ScanInterval.low(0) == ScanIntervalDefault.LOW.value

            # Test invalid plant index
            assert ScanInterval.realtime(1) == ScanIntervalDefault.REALTIME.value

    def test_scan_interval_from_config(self):
        from sigenergy2mqtt.config import Config, _swap_active_config
        from sigenergy2mqtt.config.models.modbus import ModbusConfig
        from sigenergy2mqtt.sensors.base.scan_interval import ScanInterval

        cfg = Config()
        m1 = ModbusConfig(host="1.1.1.1", port=502)
        m1.scan_interval.realtime = 1
        m1.scan_interval.high = 2
        m1.scan_interval.medium = 3
        m1.scan_interval.low = 4

        cfg.modbus = [m1]

        with _swap_active_config(cfg):
            assert ScanInterval.realtime(0) == 1
            assert ScanInterval.high(0) == 2
            assert ScanInterval.medium(0) == 3
            assert ScanInterval.low(0) == 4

            # Out of range plant index
            from sigenergy2mqtt.common import ScanIntervalDefault

            assert ScanInterval.realtime(1) == ScanIntervalDefault.REALTIME.value
