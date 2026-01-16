import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import ConsumptionMethod, Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import PVPowerSensor, Sensor
from sigenergy2mqtt.sensors.plant_derived import (
    PlantConsumedPower,
    TotalLifetimePVEnergy,
    TotalPVPower,
)
from sigenergy2mqtt.sensors.plant_read_only import (
    BatteryPower,
    GeneralLoadPower,
    GridSensorActivePower,
    GridStatus,
    PlantPVPower,
    PlantPVTotalGeneration,
    ThirdPartyLifetimePVEnergy,
    TotalLoadPower,
)


@pytest.fixture(autouse=True)
def mock_config():
    with patch("sigenergy2mqtt.sensors.plant_derived.Config") as mock_der_config:
        mock_der_config.home_assistant.entity_id_prefix = "sigenergy"
        mock_der_config.home_assistant.unique_id_prefix = "sigenergy"
        mock_der_config.home_assistant.discovery_prefix = "homeassistant"
        mock_der_config.home_assistant.enabled = True
        mock_der_config.home_assistant.use_simplified_topics = False
        mock_der_config.home_assistant.edit_percentage_with_box = False
        mock_der_config.modbus = [MagicMock()]
        mock_der_config.modbus[0].smartport.enabled = False
        mock_der_config.modbus[0].smartport.mqtt = []
        mock_der_config.sensor_overrides = {}
        mock_der_config.consumption = ConsumptionMethod.CALCULATED
        yield mock_der_config


class TestBasicDerivedSensorsCoverage:
    def test_battery_charging_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import BatteryChargingPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            bp = MagicMock(spec=BatteryPower)
            bp.device_class = "power"
            bp.state_class = "measurement"
            bp.protocol_version = Protocol.V2_4
            sensor = BatteryChargingPower(0, bp)
            assert "BatteryPower &gt; 0" in sensor.get_attributes()["source"]

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor), [])
            assert "Attempt to call" in caplog.text

    def test_battery_discharging_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import BatteryDischargingPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            bp = MagicMock(spec=BatteryPower)
            bp.device_class = "power"
            bp.state_class = "measurement"
            bp.protocol_version = Protocol.V2_4
            sensor = BatteryDischargingPower(0, bp)
            assert "BatteryPower &lt; 0" in sensor.get_attributes()["source"]

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor), [])
            assert "Attempt to call" in caplog.text

    def test_grid_export_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import GridSensorExportPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            gp = MagicMock(spec=GridSensorActivePower)
            gp.device_class = "power"
            gp.state_class = "measurement"
            gp.precision = 2
            gp.protocol_version = Protocol.V2_4
            sensor = GridSensorExportPower(0, gp)
            assert "GridSensorActivePower &lt; 0" in sensor.get_attributes()["source"]

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor), [])
            assert "Attempt to call" in caplog.text

    def test_grid_import_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import GridSensorImportPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            gp = MagicMock(spec=GridSensorActivePower)
            gp.device_class = "power"
            gp.state_class = "measurement"
            gp.precision = 2
            gp.protocol_version = Protocol.V2_4
            sensor = GridSensorImportPower(0, gp)
            assert "GridSensorActivePower &gt; 0" in sensor.get_attributes()["source"]

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor), [])
            assert "Attempt to call" in caplog.text

    def test_daily_accumulation_sensors(self):
        from sigenergy2mqtt.sensors.plant_derived import GridSensorDailyExportEnergy, GridSensorDailyImportEnergy, PlantDailyChargeEnergy, PlantDailyDischargeEnergy, PlantDailyPVEnergy, TotalDailyPVEnergy
        from sigenergy2mqtt.sensors.plant_read_only import PlantTotalExportedEnergy, PlantTotalImportedEnergy

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # Export
            source_exp = MagicMock(spec=PlantTotalExportedEnergy)
            source_exp.unique_id = "exp_uid"
            source_exp.data_type = ModbusDataType.UINT32
            source_exp.protocol_version = Protocol.V2_4
            source_exp.unit = "kWh"
            source_exp.object_id = "exp_oid"
            source_exp.state_class = "total_increasing"
            source_exp.precision = 2
            s_exp = GridSensorDailyExportEnergy(0, source_exp)
            assert "PlantTotalExportedEnergy" in s_exp.get_attributes()["source"]

            # Import
            source_imp = MagicMock(spec=PlantTotalImportedEnergy)
            source_imp.unique_id = "imp_uid"
            source_imp.data_type = ModbusDataType.UINT32
            source_imp.protocol_version = Protocol.V2_4
            source_imp.unit = "kWh"
            source_imp.object_id = "imp_oid"
            source_imp.state_class = "total_increasing"
            source_imp.precision = 2
            s_imp = GridSensorDailyImportEnergy(0, source_imp)
            assert "PlantTotalImportedEnergy" in s_imp.get_attributes()["source"]

            # Total PV
            source_tpv = MagicMock(spec=PlantPVTotalGeneration)
            source_tpv.unique_id = "tpv_uid"
            source_tpv.data_type = ModbusDataType.UINT32
            source_tpv.protocol_version = Protocol.V2_4
            source_tpv.unit = "kWh"
            source_tpv.object_id = "tpv_oid"
            source_tpv.state_class = "total_increasing"
            source_tpv.precision = 2
            s_tpv = TotalDailyPVEnergy(0, source_tpv)
            assert "TotalLifetimePVEnergy" in s_tpv.get_attributes()["source"]

            # Plant Daily PV
            s_pdpv = PlantDailyPVEnergy(0, source_tpv)
            assert "PlantLifetimePVEnergy" in s_pdpv.get_attributes()["source"]

            # Plant Daily Charge
            from sigenergy2mqtt.sensors.plant_read_only import ESSTotalChargedEnergy, ESSTotalDischargedEnergy

            source_charge = MagicMock(spec=ESSTotalChargedEnergy)
            source_charge.unique_id = "ch_uid"
            source_charge.data_type = ModbusDataType.UINT32
            source_charge.protocol_version = Protocol.V2_4
            source_charge.unit = "kWh"
            source_charge.object_id = "ch_oid"
            source_charge.state_class = "total_increasing"
            source_charge.precision = 2
            s_pdc = PlantDailyChargeEnergy(0, source_charge)
            assert "DailyChargeEnergy" in s_pdc.get_attributes()["source"]

            # Plant Daily Discharge
            source_discharge = MagicMock(spec=ESSTotalDischargedEnergy)
            source_discharge.unique_id = "dis_uid"
            source_discharge.data_type = ModbusDataType.UINT32
            source_discharge.protocol_version = Protocol.V2_4
            source_discharge.unit = "kWh"
            source_discharge.object_id = "dis_oid"
            source_discharge.state_class = "total_increasing"
            source_discharge.precision = 2
            s_pdd = PlantDailyDischargeEnergy(0, source_discharge)
            assert "DailyDischargeEnergy" in s_pdd.get_attributes()["source"]


class TestPlantConsumedPowerCoverage:
    def test_value_repr(self):
        val = PlantConsumedPower.Value(state=100.0, last_update=time.time())
        assert repr(val) == "100.0"

        val_no_state = PlantConsumedPower.Value(last_update=time.time() - 10)
        assert "10.0s ago" in repr(val_no_state)

        val_never = PlantConsumedPower.Value()
        assert repr(val_never) == "Never"

    def test_init_modes(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s_gen = PlantConsumedPower(0, ConsumptionMethod.GENERAL)
            assert s_gen.get_attributes()["source"] == "GeneralLoadPower"

            s_tot = PlantConsumedPower(0, ConsumptionMethod.TOTAL)
            assert s_tot.get_attributes()["source"] == "TotalLoadPower"

    def test_negative_consumption_adjustment(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
            # pv=0, battery=0, grid=-100 -> sum = -100
            sensor._update_source("pv", 0)
            sensor._update_source("battery", 0)
            sensor._update_source("grid", -100)
            sensor._set_latest_consumption()
            assert sensor.latest_raw_state == 0
            assert "consumed_power (-100.0) is NEGATIVE" in caplog.text

    @pytest.mark.asyncio
    async def test_publish_skipped_and_reset(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
            sensor.debug_logging = True
            sensor.configure_mqtt_topics("test_device")
            mqtt_client = MagicMock()
            # Missing values -> skip
            assert await sensor.publish(mqtt_client, None) is False
            assert "Publishing SKIPPED" in caplog.text

            # All values populated
            sensor._update_source("pv", 1000)
            sensor._update_source("battery", 0)
            sensor._update_source("grid", 0)

            with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
                assert await sensor.publish(mqtt_client, None) is True
                mock_pub.assert_called_once()
                # Verify internal states reset
                for v in sensor._sources.values():
                    assert v.state is None

    @pytest.mark.asyncio
    async def test_notify_edge_cases(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
            sensor.debug_logging = True
            sensor.configure_mqtt_topics("test_device")
            # Unregistered topic
            assert await sensor.notify(None, MagicMock(), 100, "unknown_topic", MagicMock()) is False
            assert "topic is not registered" in caplog.text

            # Valid topic but not enough values to publish
            await sensor.notify(None, MagicMock(), 100, "pv", MagicMock())
            assert sensor._sources["pv"].state == 100.0
            assert "Updated from topic pv" in caplog.text
            assert "Attempt to call" in caplog.text

    def test_observable_topics_with_chargers(self):
        from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerChargingPower
        from sigenergy2mqtt.sensors.inverter_read_only import DCChargerOutputPower

        class MockACCharger:
            pass

        with patch("sigenergy2mqtt.sensors.plant_derived.DeviceRegistry.get") as mock_get:
            charger = MockACCharger()
            ac_sensor = MagicMock(spec=ACChargerChargingPower)
            ac_sensor.state_topic = "ac_topic"
            ac_sensor.gain = 1.0
            ac_sensor.scan_interval = 10

            charger.get_all_sensors = MagicMock(return_value={"ac": ac_sensor})
            mock_get.return_value = [charger]

            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
            sensor.debug_logging = True
            with patch("logging.debug") as mock_log:
                topics = sensor.observable_topics()
                assert "ac_topic" in topics
                assert "ac_topic" in sensor._sources
                # Verify debug log was called with some string containing Added MQTT topic
                any_added = any("Added MQTT topic" in call.args[0] for call in mock_log.call_args_list)
                assert any_added

    def test_set_source_values_branches(self, caplog):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)

            # GridStatus restoration/detected
            gs = MagicMock(spec=GridStatus)
            gs.unique_id = "gs"

            # Initial status (sets _grid_status = 0)
            sensor.set_source_values(gs, [(0, 0)])
            assert sensor._grid_status == 0

            # Off grid transition
            sensor.set_source_values(gs, [(0, 1)])
            assert sensor._grid_status == 1
            assert "Off Grid detected" in caplog.text

            # Grid restored transition
            sensor.set_source_values(gs, [(0, 0)])
            assert sensor._grid_status == 0
            assert "Grid restored" in caplog.text

            # Unrecognized sensor
            assert sensor.set_source_values(MagicMock(spec=Sensor), [(0, 100)]) is False


class TestTotalPVPowerCoverage:
    def test_value_repr(self):
        val = TotalPVPower.Value(gain=1.0, type=TotalPVPower.SourceType.MANDATORY, state=100.0)
        assert "100.0 (m/enabled)" in repr(val)

    def test_failover_and_fallback(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s1 = MagicMock(spec=PVPowerSensor)
            s1.unique_id = "s1"
            s1.gain = 1.0
            sensor = TotalPVPower(0, s1)

            # Add a failover source
            s2_id = "s2"
            sensor._sources[s2_id] = TotalPVPower.Value(gain=1.0, type=TotalPVPower.SourceType.FAILOVER, enabled=False)

            # Trigger failover
            assert sensor.failover(s1) is True
            # Try again (already enabled)
            assert sensor.failover(s1) is True

            assert sensor._sources[s2_id].enabled is True
            assert sensor._sources["s1"].enabled is False

            # Trigger fallback
            sensor._sources[s1.unique_id].state = 50.0
            sensor.fallback(s1.unique_id)
            assert sensor._sources[s1.unique_id].enabled is True
            assert sensor._sources[s2_id].enabled is False

    def test_get_attributes_smartport(self, mock_config):
        mock_config.modbus[0].smartport.enabled = True
        sensor = TotalPVPower(0)
        assert "Smart-Port" in sensor.get_attributes()["source"]

        mock_config.modbus[0].smartport.enabled = False
        sensor2 = TotalPVPower(0)
        assert "Third-Party" in sensor2.get_attributes()["source"]

    @pytest.mark.asyncio
    async def test_notify_edge_cases(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalPVPower(0)
            sensor.debug_logging = True
            sensor.configure_mqtt_topics("test_device")
            # Unregistered topic
            assert await sensor.notify(None, MagicMock(), 100, "unknown", MagicMock()) is False
            assert "topic is not registered" in caplog.text

            # Valid topic, disabled -> trigger fallback
            sensor._sources["t1"] = TotalPVPower.Value(1.0, TotalPVPower.SourceType.SMARTPORT, enabled=False)
            await sensor.notify(None, MagicMock(), 100, "t1", MagicMock())
            assert sensor._sources["t1"].enabled is True
            assert "Updated from (enabled) topic t1" in caplog.text

    def test_observable_topics_smartport(self, mock_config, caplog):
        caplog.set_level(logging.DEBUG)
        mock_config.modbus[0].smartport.enabled = True

        # Valid topic
        topic_mock = MagicMock()
        topic_mock.topic = "smart_topic"
        topic_mock.gain = 1.0

        # Empty topic
        topic_empty = MagicMock()
        topic_empty.topic = ""

        mock_config.modbus[0].smartport.mqtt = [topic_mock, topic_empty]

        sensor = TotalPVPower(0)
        sensor.debug_logging = True
        topics = sensor.observable_topics()
        assert "smart_topic" in topics
        assert "Added Smart-Port MQTT topic smart_topic" in caplog.text
        assert "Empty Smart-Port MQTT topic ignored" in caplog.text

    @pytest.mark.asyncio
    async def test_publish_skipped(self):
        sensor = TotalPVPower(0)
        sensor.debug_logging = True
        sensor.configure_mqtt_topics("test_device")
        sensor._sources["t1"] = TotalPVPower.Value(1.0, TotalPVPower.SourceType.MANDATORY, enabled=True, state=None)
        assert await sensor.publish(MagicMock(), None) is False

        sensor._sources["t1"].state = 100.0
        with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock):
            assert await sensor.publish(MagicMock(), None) is True

    def test_register_source(self):
        sensor = TotalPVPower(0)
        sensor.debug_logging = True
        s1 = MagicMock(spec=PVPowerSensor)
        s1.unique_id = "s1"
        s1.gain = 1.0
        with patch("logging.debug") as mock_log:
            sensor.register_source_sensors(s1, type=TotalPVPower.SourceType.MANDATORY)
            # Check for "Added sensor s1"
            any_added = any("Added sensor s1" in call.args[0] for call in mock_log.call_args_list)
            assert any_added

    def test_set_source_values_ignored(self, caplog):
        sensor = TotalPVPower(0)
        sensor.debug_logging = True
        # Not a PVPowerSensor
        ms = MagicMock(spec=Sensor)
        ms.unique_id = "ms_uid"
        assert sensor.set_source_values(ms, []) is False
        assert "not PVPower instance" in caplog.text

        # Not registered
        s1 = MagicMock(spec=PVPowerSensor)
        s1.unique_id = "unregistered"
        assert sensor.set_source_values(s1, []) is False
        assert "sensor is not registered" in caplog.text

    def test_set_source_values_debug(self, caplog):
        caplog.set_level(logging.DEBUG)
        s1 = MagicMock(spec=PVPowerSensor)
        s1.unique_id = "s1"
        s1.gain = 1.0
        sensor = TotalPVPower(0, s1)
        sensor.debug_logging = True
        sensor.set_source_values(s1, [(0, 100)])
        assert "Updated from enabled source 's1'" in caplog.text


class TestTotalLifetimePVEnergyCoverage:
    def test_get_discovery_components(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0)
            sensor.get_attributes()
            comps = sensor.get_discovery_components()
            assert f"{sensor.unique_id}_reset" in comps

    @pytest.mark.asyncio
    async def test_publish_skipped_and_reset(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0)
            sensor.debug_logging = True
            sensor.configure_mqtt_topics("test_device")
            assert await sensor.publish(MagicMock(), None) is False
            assert "Publishing SKIPPED" in caplog.text

            sensor.plant_lifetime_pv_energy = 100.0
            sensor.plant_3rd_party_lifetime_pv_energy = 50.0
            with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
                assert await sensor.publish(MagicMock(), None) is True
                assert "Publishing READY" in caplog.text
                assert sensor.plant_lifetime_pv_energy is None
                assert sensor.plant_3rd_party_lifetime_pv_energy is None

    def test_set_source_values_branches(self, caplog):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0)

            # PlantPVTotalGeneration
            sg = MagicMock(spec=PlantPVTotalGeneration)
            sensor.set_source_values(sg, [(0, 1000)])
            assert sensor.plant_lifetime_pv_energy == 1000

            # ThirdPartyLifetimePVEnergy
            tp = MagicMock(spec=ThirdPartyLifetimePVEnergy)
            sensor.set_source_values(tp, [(0, 500)])
            assert sensor.plant_3rd_party_lifetime_pv_energy == 500
            assert sensor.latest_raw_state == 1500

            # Unrecognized
            assert sensor.set_source_values(MagicMock(spec=Sensor), []) is False
            assert "Attempt to call" in caplog.text
