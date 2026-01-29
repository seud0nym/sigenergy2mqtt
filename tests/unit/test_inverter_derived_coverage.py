import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.inverter_derived import (
    InverterBatteryChargingPower,
    InverterBatteryDischargingPower,
    PVStringDailyEnergy,
    PVStringLifetimeEnergy,
    PVStringPower,
)
from sigenergy2mqtt.sensors.inverter_read_only import (
    ChargeDischargePower,
    PVCurrentSensor,
    PVVoltageSensor,
)


@pytest.fixture(autouse=True)
def mock_config():
    with patch("sigenergy2mqtt.sensors.inverter_derived.Config") as mock_der_config:
        mock_der_config.home_assistant.entity_id_prefix = "sigenergy"
        mock_der_config.home_assistant.unique_id_prefix = "sigenergy"
        mock_der_config.home_assistant.discovery_prefix = "homeassistant"
        mock_der_config.home_assistant.enabled = True
        mock_der_config.home_assistant.use_simplified_topics = False
        mock_der_config.home_assistant.edit_percentage_with_box = False
        mock_der_config.modbus = [MagicMock()]
        mock_der_config.modbus[0].smartport.enabled = False
        mock_der_config.sensor_overrides = {}
        yield mock_der_config


class TestBatteryDerivedPowerCoverage:
    def test_get_attributes_charging(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            cdp = MagicMock(spec=ChargeDischargePower)
            cdp.device_class = "power"
            cdp.state_class = "measurement"
            cdp.protocol_version = Protocol.V2_4
            sensor = InverterBatteryChargingPower(0, 1, cdp)
            assert "ChargeDischargePower &gt; 0" in sensor.get_attributes()["source"]

    def test_set_source_values_error_charging(self, caplog):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            cdp = MagicMock(spec=ChargeDischargePower)
            cdp.device_class = "power"
            cdp.state_class = "measurement"
            cdp.protocol_version = Protocol.V2_4
            sensor = InverterBatteryChargingPower(0, 1, cdp)

            # Wrong sensor type
            assert sensor.set_source_values(MagicMock(spec=Sensor), []) is False
            assert "Attempt to call" in caplog.text

    def test_get_attributes_discharging(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            cdp = MagicMock(spec=ChargeDischargePower)
            cdp.device_class = "power"
            cdp.state_class = "measurement"
            cdp.protocol_version = Protocol.V2_4
            sensor = InverterBatteryDischargingPower(0, 1, cdp)
            assert "ChargeDischargePower &lt; 0" in sensor.get_attributes()["source"]

    def test_set_source_values_error_discharging(self, caplog):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            cdp = MagicMock(spec=ChargeDischargePower)
            cdp.device_class = "power"
            cdp.state_class = "measurement"
            cdp.protocol_version = Protocol.V2_4
            sensor = InverterBatteryDischargingPower(0, 1, cdp)

            # Wrong sensor type
            assert sensor.set_source_values(MagicMock(spec=Sensor), []) is False
            assert "Attempt to call" in caplog.text


class TestPVStringPowerCoverage:
    def test_get_attributes(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            v = MagicMock(spec=PVVoltageSensor)
            v.gain = 10
            v.protocol_version = Protocol.V2_4
            c = MagicMock(spec=PVCurrentSensor)
            c.gain = 100
            c.protocol_version = Protocol.V2_4
            sensor = PVStringPower(0, 1, 1, Protocol.V2_4, v, c)
            assert "PVVoltageSensor &times; PVCurrentSensor" in sensor.get_attributes()["source"]

    @pytest.mark.asyncio
    async def test_publish_skipped_and_ready(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            v = MagicMock(spec=PVVoltageSensor)
            v.gain = 10
            v.protocol_version = Protocol.V2_4
            c = MagicMock(spec=PVCurrentSensor)
            c.gain = 100
            c.protocol_version = Protocol.V2_4
            sensor = PVStringPower(0, 1, 1, Protocol.V2_4, v, c)
            sensor.debug_logging = True

            # Missing values -> skip
            assert await sensor.publish(MagicMock(), None) is False
            assert "Publishing SKIPPED" in caplog.text

            # Ready
            sensor.voltage = 400.0
            sensor.current = 10.0
            with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
                assert await sensor.publish(MagicMock(), None) is True
                assert "Publishing READY" in caplog.text
                assert sensor.voltage is None
                assert sensor.current is None

    def test_set_source_values_error(self, caplog):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            v = MagicMock(spec=PVVoltageSensor)
            v.gain = 10
            v.protocol_version = Protocol.V2_4
            c = MagicMock(spec=PVCurrentSensor)
            c.gain = 100
            c.protocol_version = Protocol.V2_4
            sensor = PVStringPower(0, 1, 1, Protocol.V2_4, v, c)

            # Wrong sensor type
            assert sensor.set_source_values(MagicMock(spec=Sensor), []) is False
            assert "Attempt to call" in caplog.text


class TestPVStringEnergyCoverage:
    def test_energy_sensors(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            v = MagicMock(spec=PVVoltageSensor)
            v.gain = 10
            v.protocol_version = Protocol.V2_4
            c = MagicMock(spec=PVCurrentSensor)
            c.gain = 100
            c.protocol_version = Protocol.V2_4

            power = PVStringPower(0, 1, 1, Protocol.V2_4, v, c)
            power.unique_id = "power_uid"
            power.object_id = "power_oid"
            power.precision = 2

            # Lifetime
            lifetime = PVStringLifetimeEnergy(0, 1, 1, Protocol.V2_4, power)
            assert "Riemann &sum; of PVStringPower" in lifetime.get_attributes()["source"]

            # Daily
            daily = PVStringDailyEnergy(0, 1, 1, Protocol.V2_4, lifetime)
            assert "PVStringLifetimeEnergy &minus;" in daily.get_attributes()["source"]
