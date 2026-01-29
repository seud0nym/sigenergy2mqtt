import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import InputType, Sensor
from sigenergy2mqtt.sensors.inverter_derived import InverterBatteryChargingPower, InverterBatteryDischargingPower, PVStringPower
from sigenergy2mqtt.sensors.inverter_read_only import ChargeDischargePower, InverterFirmwareVersion, InverterModel, PVCurrentSensor, PVVoltageSensor
from sigenergy2mqtt.sensors.inverter_read_write import DCChargerStatus, InverterActivePowerPercentageAdjustment, InverterStatus


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


@pytest.fixture
def mock_config():
    with (
        patch("sigenergy2mqtt.sensors.inverter_read_only.Config") as mock_ro_config,
        patch("sigenergy2mqtt.sensors.inverter_read_write.Config") as mock_rw_config,
        patch("sigenergy2mqtt.sensors.inverter_derived.Config") as mock_der_config,
    ):
        for cfg in [mock_ro_config, mock_rw_config, mock_der_config]:
            cfg.home_assistant.entity_id_prefix = "sigenergy"
            cfg.home_assistant.unique_id_prefix = "sigenergy"
            cfg.home_assistant.discovery_prefix = "homeassistant"
            cfg.home_assistant.enabled = True
            cfg.home_assistant.use_simplified_topics = False
            cfg.home_assistant.edit_percentage_with_box = False
            cfg.modbus = [MagicMock()]
            cfg.modbus[0].scan_interval.high = 10
            cfg.modbus[0].scan_interval.realtime = 5
            cfg.modbus[0].scan_interval.low = 600
            cfg.modbus[0].scan_interval.medium = 60

        yield mock_ro_config


class TestInverterReadOnly:
    def test_inverter_model(self, mock_config):
        sensor = InverterModel(plant_index=0, device_address=1)
        assert sensor["name"] == "Model"
        assert sensor.address == 30500
        assert sensor["entity_category"] == "diagnostic"

    @pytest.mark.asyncio
    async def test_inverter_firmware_version(self, mock_config):
        sensor = InverterFirmwareVersion(plant_index=0, device_address=1)
        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_get_state:
            mock_get_state.return_value = "V1.0.0"
            assert await sensor.get_state() == "V1.0.0"


class TestInverterReadWrite:
    def test_inverter_status(self, mock_config):
        sensor = InverterStatus(plant_index=0, device_address=1)
        sensor.configure_mqtt_topics("test_device")
        attrs = sensor.get_attributes()
        assert "comment" in attrs
        assert "0:Stop 1:Start" in attrs["comment"]

    def test_dc_charger_status(self, mock_config):
        sensor = DCChargerStatus(plant_index=0, device_address=1)
        sensor.configure_mqtt_topics("test_device")
        attrs = sensor.get_attributes()
        assert "comment" in attrs
        assert "0:Start 1:Stop" in attrs["comment"]

    def test_inverter_active_power_adjustment(self, mock_config):
        sensor = InverterActivePowerPercentageAdjustment(plant_index=0, device_address=1)
        assert sensor["min"] == -100.0
        assert sensor["max"] == 100.0


class TestInverterDerived:
    def test_battery_charging_discharging_power(self, mock_config):
        # We need a source sensor
        source = ChargeDischargePower(plant_index=0, device_address=1)

        charging = InverterBatteryChargingPower(0, 1, source)
        discharging = InverterBatteryDischargingPower(0, 1, source)

        # Test positive value (charging)
        source.set_state(1500.0)
        charging.set_source_values(source, source._states)
        discharging.set_source_values(source, source._states)

        assert charging._states[-1][1] == 1500.0
        assert discharging._states[-1][1] == 0

        # Test negative value (discharging)
        source.set_state(-2000.0)
        charging.set_source_values(source, source._states)
        discharging.set_source_values(source, source._states)

        assert charging._states[-1][1] == 0
        assert discharging._states[-1][1] == 2000.0

    @pytest.mark.asyncio
    async def test_pv_string_power(self, mock_config):
        v = PVVoltageSensor(0, 1, 31000, 1, Protocol.V1_8)
        c = PVCurrentSensor(0, 1, 31001, 1, Protocol.V1_8)

        p = PVStringPower(0, 1, 1, Protocol.V1_8, v, c)

        # Set some values
        v.set_state(4000)  # 400.0V (gain=10)
        c.set_state(100)  # 1.0A (gain=100)

        p.set_source_values(v, v._states)
        assert p.voltage == 400.0
        assert p.current is None

        p.set_source_values(c, c._states)
        assert p.current == 1.0
        assert p._states[-1][1] == 400.0  # 400.0 * 1.0

        # Test publish clearing
        with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
            await p.publish(MagicMock(), MagicMock())
            assert p.voltage is None
            assert p.current is None
