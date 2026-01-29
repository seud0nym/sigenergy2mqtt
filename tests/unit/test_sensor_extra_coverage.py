import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock circular dependencies before importing sigenergy2mqtt
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor, Config, NumericSensor, RunningStateSensor, SelectSensor, Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, InputType, StateClass, UnitOfEnergy


@pytest.fixture(autouse=True)
def mock_config_global():
    with patch("sigenergy2mqtt.config.Config") as mock:
        mock.home_assistant.enabled = True
        mock.home_assistant.enabled_by_default = True
        mock.home_assistant.unique_id_prefix = "sigen"
        mock.home_assistant.entity_id_prefix = "sigen"
        mock.home_assistant.edit_percentage_with_box = False  # Default
        mock.sensor_debug_logging = True
        mock.persistent_state_path = "/tmp"
        mock.modbus = []
        mock.sensor_overrides = {}

        # Patch Config in base module
        with patch("sigenergy2mqtt.sensors.base.Config", mock):
            yield mock


@pytest.fixture(autouse=True)
def clear_sensor_registries():
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()
    yield
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


class TestSelectSensor:
    @pytest.mark.asyncio
    async def test_get_state_invalid_option(self):
        sensor = SelectSensor(
            availability_control_sensor=None,
            name="Test Select",
            object_id="sigen_test_select",
            plant_index=0,
            device_address=1,
            address=30000,
            scan_interval=60,
            options=["Option A", "Option B"],
            protocol_version=Protocol.V1_8,
        )

        # Valid cases
        with patch("sigenergy2mqtt.sensors.base.ReadWriteSensor.get_state", new_callable=AsyncMock) as mock_super:
            mock_super.return_value = 0
            assert await sensor.get_state() == "Option A"

            mock_super.return_value = 1
            assert await sensor.get_state() == "Option B"

            # Invalid cases
            mock_super.return_value = 2
            assert await sensor.get_state() == "Unknown Mode: 2"

            mock_super.return_value = -1
            assert await sensor.get_state() == "Unknown Mode: -1"


class TestNumericSensor:
    @pytest.mark.asyncio
    async def test_get_state_clamping(self):
        # NumericSensor is usually initialized via subclasses or mixins like WritableSensorMixin/ReadWriteSensor
        # We need to construct it carefully or use a concrete implementation.

        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test Number",
            object_id="sigen_test_number",
            plant_index=0,
            device_address=1,
            address=30000,
            input_type=InputType.HOLDING,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=60,
            protocol_version=Protocol.V1_8,
            minimum=10.0,
            maximum=20.0,
            unit="W",
            device_class=DeviceClass.POWER,
            state_class=None,
            icon=None,
            gain=None,
            precision=1,
        )
        # It sets gain=None by default unless specified

        with patch("sigenergy2mqtt.sensors.base.ReadWriteSensor.get_state", new_callable=AsyncMock) as mock_super:
            # Valid value
            mock_super.return_value = 15.0
            assert await sensor.get_state() == 15.0

            # Below min
            mock_super.return_value = 5.0
            # get_state should detect < min and return min (10.0)
            assert await sensor.get_state() == 10.0

            # Above max
            mock_super.return_value = 25.0
            # get_state should detect > max and return max (20.0)
            assert await sensor.get_state() == 20.0

    @pytest.mark.asyncio
    async def test_get_state_tuple_min_max(self):
        # Test range checking for tuple min/max (used for conditional ranges?)
        # base.py logic: isinstance(self["min"], tuple) and value < 0 and not min <= value <= max

        # Construct with tuple
        # Logic seems to be: minimum tuple defines range for negative values (?), maximum tuple for positive values (?)
        # Assertion requires min < max element-wise.
        # Let's try: min range [-20, -10], max range [10, 20]
        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test Number Tuple",
            object_id="sigen_test_number_tuple",
            plant_index=0,
            device_address=1,
            address=30000,
            input_type=InputType.HOLDING,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=60,
            protocol_version=Protocol.V1_8,
            minimum=(-20.0, -10.0),
            maximum=(10.0, 20.0),
            unit="W",
            device_class=DeviceClass.POWER,
            state_class=None,
            icon=None,
            gain=None,
            precision=1,
        )

        with patch("sigenergy2mqtt.sensors.base.ReadWriteSensor.get_state", new_callable=AsyncMock) as mock_super:
            # Valid Positive (in max range [10, 20])
            mock_super.return_value = 15.0
            assert await sensor.get_state() == 15.0

            # Valid Negative (in min range [-20, -10])
            mock_super.return_value = -15.0
            assert await sensor.get_state() == -15.0

            # Invalid Positive (Outside max range)
            # 5.0 is not in [10, 20]. Logic clamps to max(self["max"]) -> 20.0
            mock_super.return_value = 5.0
            assert await sensor.get_state() == 20.0

            # Invalid Negative (Outside min range)
            # -5.0 is not in [-20, -10]. Logic clamps to min(self["min"]) -> -20.0
            mock_super.return_value = -5.0
            assert await sensor.get_state() == -20.0


class ConcreteAlarmSensor(AlarmSensor):
    def decode_alarm_bit(self, bit_position: int) -> str | None:
        if bit_position == 0:
            return "Error 0"
        if bit_position == 1:
            return "Error 1"
        return None


class TestAlarmSensor:
    @pytest.mark.asyncio
    async def test_get_state_logic(self):
        sensor = ConcreteAlarmSensor(name="Test Alarm", object_id="sigen_test_alarm", plant_index=0, device_address=1, address=30000, protocol_version=Protocol.V1_8, alarm_type="TestType")
        with patch("sigenergy2mqtt.sensors.base.Sensor.get_state", new_callable=AsyncMock) as mock_super:
            # 1. No Alarm cases
            mock_super.return_value = 0
            assert await sensor.get_state() == "No Alarm"

            mock_super.return_value = None
            assert await sensor.get_state() == "No Alarm"

            mock_super.return_value = 65535
            assert await sensor.get_state() == "No Alarm"

            # 2. Single bit set
            mock_super.return_value = 1  # Bit 0
            assert await sensor.get_state() == "Error 0"

            mock_super.return_value = 2  # Bit 1
            assert await sensor.get_state() == "Error 1"

            # 3. Multiple bits
            mock_super.return_value = 3  # Bit 0 and 1
            assert await sensor.get_state() == "Error 0, Error 1"

            # 4. Unknown bit
            mock_super.return_value = 4  # Bit 2 (not defined in ConcreteAlarmSensor)
            assert await sensor.get_state() == "Unknown (bit2∈4)"

            # 5. List value (PCS special case: [0, alarm_val])
            mock_super.return_value = [0, 1]
            assert await sensor.get_state() == "Error 0"

            # 6. Truncation
            # Construct a long error string
            mock_super.return_value = 3
            # We can force truncation by passing max_length in kwargs or relies on HA enabled check.
            # base.py: max_length = 255 if not ("max_length" in kwargs ...) else ...

            res = await sensor.get_state(max_length=5)
            # "Error 0, Error 1" is > 5 chars
            # Logic: re.sub ... then alarms[: (max_length - 3)] + "..."
            # "Error 0, Error 1" -> "Error 0, Error 1" (no extra spaces)
            # 5 - 3 = 2 chars
            # "Er..."
            assert res == "Er..."


class TestAlarmCombinedSensor:
    @pytest.mark.asyncio
    async def test_get_state_aggregation(self):
        # Create child sensors with mocked get_state
        a1 = ConcreteAlarmSensor("A1", "sigen_a1", 0, 1, 30000, Protocol.V1_8, alarm_type="TypeA")
        a2 = ConcreteAlarmSensor("A2", "sigen_a2", 0, 1, 30001, Protocol.V1_8, alarm_type="TypeB")

        combined = AlarmCombinedSensor("Combined", "sigen_combined_uid", "sigen_combined_oid", a1, a2)
        # Test 1: All No Alarm
        with patch.object(a1, "get_state", new_callable=AsyncMock) as m1, patch.object(a2, "get_state", new_callable=AsyncMock) as m2:
            m1.return_value = "No Alarm"
            m2.return_value = "No Alarm"

            assert await combined.get_state() == "No Alarm"

        # Test 2: One has alarm
        with patch.object(a1, "get_state", new_callable=AsyncMock) as m1, patch.object(a2, "get_state", new_callable=AsyncMock) as m2:
            m1.return_value = "Error 0"
            m2.return_value = "No Alarm"

            assert await combined.get_state() == "Error 0"

        # Test 3: Both have alarm
        with patch.object(a1, "get_state", new_callable=AsyncMock) as m1, patch.object(a2, "get_state", new_callable=AsyncMock) as m2:
            m1.return_value = "Error 0"
            m2.return_value = "Error 1"

            assert await combined.get_state() == "Error 0, Error 1"


class TestRunningStateSensor:
    @pytest.mark.asyncio
    async def test_get_state_invalid_index(self):
        sensor = RunningStateSensor(name="Run State", object_id="sigen_run_state", plant_index=0, device_address=1, address=30000, protocol_version=Protocol.V1_8)
        # RunningStateSensor defines options in __init__

        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super:
            # Valid
            mock_super.return_value = 0
            assert await sensor.get_state() == "Standby"

            # Invalid
            mock_super.return_value = 100
            assert await sensor.get_state() == "Unknown State code: 100"
