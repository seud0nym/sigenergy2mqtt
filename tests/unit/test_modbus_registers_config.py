from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol, RegisterAccess
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.config.modbus_config import ModbusConfiguration
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.base import (
    DerivedSensor,
    ReadableSensorMixin,
    Sensor,
    WritableSensorMixin,
    WriteOnlySensor,
)
from sigenergy2mqtt.sensors.const import InputType

MODBUS_DATA_TYPE = ModbusClient.DATATYPE


class TestModbusRegistersConfig:
    def test_default_values(self):
        config = ModbusConfiguration()
        assert config.registers.no_remote_ems is False
        assert config.registers.read_only is True
        assert config.registers.read_write is True
        assert config.registers.write_only is True

    def test_configure_registers_individually(self):
        config = ModbusConfiguration()

        config.configure({"no-remote-ems": True})
        assert config.registers.no_remote_ems is True

        config.configure({"read-only": False})
        assert config.registers.read_only is False

        config.configure({"read-write": False})
        assert config.registers.read_write is False

        config.configure({"write-only": False})
        assert config.registers.write_only is False

    def test_instance_isolation(self):
        c1 = ModbusConfiguration()
        c2 = ModbusConfiguration()

        c1.configure({"read-only": False})
        assert c1.registers.read_only is False
        assert c2.registers.read_only is True
        assert c1.registers is not c2.registers

    def test_scan_interval_isolation(self):
        c1 = ModbusConfiguration()
        c2 = ModbusConfiguration()

        c1.configure({"scan-interval-low": 999})
        assert c1.scan_interval.low == 999
        assert c2.scan_interval.low == 600
        assert c1.scan_interval is not c2.scan_interval


class MockReadableSensor(ReadableSensorMixin, Sensor):
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "test")
        kwargs.setdefault("unique_id", "sigen_test")
        kwargs.setdefault("object_id", "sigen_test")
        kwargs.setdefault("unit", "V")
        kwargs.setdefault("device_class", None)
        kwargs.setdefault("state_class", None)
        kwargs.setdefault("icon", "mdi:test")
        kwargs.setdefault("gain", 1.0)
        kwargs.setdefault("precision", 1)
        kwargs.setdefault("protocol_version", Protocol.V2_4)
        kwargs.setdefault("scan_interval", 60)
        super().__init__(**kwargs)

    async def _update_internal_state(self, **kwargs):
        return True


class MockWritableSensor(WritableSensorMixin, Sensor):
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "test")
        kwargs.setdefault("unique_id", "sigen_test_w")
        kwargs.setdefault("object_id", "sigen_test_w")
        kwargs.setdefault("unit", "V")
        kwargs.setdefault("device_class", None)
        kwargs.setdefault("state_class", None)
        kwargs.setdefault("icon", "mdi:test")
        kwargs.setdefault("gain", 1.0)
        kwargs.setdefault("precision", 1)
        kwargs.setdefault("protocol_version", Protocol.V2_4)
        kwargs.setdefault("data_type", MODBUS_DATA_TYPE.UINT16)
        kwargs.setdefault("input_type", InputType.HOLDING)
        kwargs.setdefault("plant_index", 1)
        kwargs.setdefault("device_address", 1)
        kwargs.setdefault("address", 40002)
        kwargs.setdefault("count", 1)
        super().__init__(**kwargs)

    async def _update_internal_state(self, **kwargs):
        return True

    async def value_is_valid(self, modbus_client, raw_value):
        return True


class MockWriteOnlySensor(WriteOnlySensor):
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "test")
        kwargs.setdefault("object_id", "sigen_test_wo")
        kwargs.setdefault("plant_index", 1)
        kwargs.setdefault("device_address", 1)
        kwargs.setdefault("address", 40001)
        kwargs.setdefault("protocol_version", Protocol.V2_4)
        # We don't want to pass data_type or other fields that WriteOnlySensor sets itself
        super().__init__(**kwargs)


class MockDerivedSensor(DerivedSensor):
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "test")
        kwargs.setdefault("unique_id", "sigen_test_d")
        kwargs.setdefault("object_id", "sigen_test_d")
        kwargs.setdefault("unit", "V")
        kwargs.setdefault("device_class", None)
        kwargs.setdefault("state_class", None)
        kwargs.setdefault("icon", "mdi:test")
        kwargs.setdefault("gain", 1.0)
        kwargs.setdefault("precision", 1)
        kwargs.setdefault("data_type", MODBUS_DATA_TYPE.UINT16)
        super().__init__(**kwargs)

    def set_source_values(self, sensor, values):
        return True


class TestSensorPublishableState:
    @pytest.fixture(autouse=True)
    def setup_config(self, tmp_path):
        with patch.object(Config, "home_assistant", MagicMock(unique_id_prefix="sigen", entity_id_prefix="sigen", enabled_by_default=True)):
            with patch.object(Config, "sensor_overrides", {}):
                with patch.object(Config, "persistent_state_path", tmp_path):
                    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
                        yield

    def test_no_remote_ems_override(self):
        reg_access = RegisterAccess(no_remote_ems=True)

        # Sensor with _remote_ems
        sensor = MockReadableSensor()
        sensor._remote_ems = True
        sensor.apply_sensor_overrides(reg_access)
        assert sensor.publishable is False

        # Sensor with address 40029
        sensor2 = MockReadableSensor()
        sensor2.address = 40029
        sensor2.apply_sensor_overrides(reg_access)
        assert sensor2.publishable is False

    def test_read_only_override(self):
        # Readable Sensor
        reg_access = RegisterAccess(read_only=False)
        sensor = MockReadableSensor()
        sensor.apply_sensor_overrides(reg_access)
        assert sensor.publishable is False

        # Derived Sensor
        sensor2 = MockDerivedSensor()
        sensor2.apply_sensor_overrides(reg_access)
        assert sensor2.publishable is False

    def test_read_write_override(self):
        reg_access = RegisterAccess(read_write=False)
        sensor = MockWritableSensor()
        sensor.apply_sensor_overrides(reg_access)
        assert sensor.publishable is False

    def test_write_only_override(self):
        reg_access = RegisterAccess(write_only=False)
        sensor = MockWriteOnlySensor()
        sensor.apply_sensor_overrides(reg_access)
        assert sensor.publishable is False

    def test_publishable_remains_true_if_access_allowed(self):
        reg_access = RegisterAccess(read_only=True, read_write=True, write_only=True, no_remote_ems=False)

        sensors = [MockReadableSensor(), MockWritableSensor(), MockWriteOnlySensor(), MockDerivedSensor()]
        for s in sensors:
            s.apply_sensor_overrides(reg_access)
            assert s.publishable is True
