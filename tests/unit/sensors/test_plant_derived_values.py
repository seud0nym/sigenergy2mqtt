import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import ConsumptionMethod, DeviceClass, Protocol, StateClass
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import PVPowerSensor, Sensor
from sigenergy2mqtt.sensors.plant_derived import (
    PlantConsumedPower,
    TotalLifetimePVEnergy,
    TotalPVPower,
)
from sigenergy2mqtt.sensors.plant_read_only import (
    BatteryPower,
    GridSensorActivePower,
    GridStatus,
    PlantPVTotalGeneration,
    ThirdPartyLifetimePVEnergy,
)


@pytest.fixture(autouse=True)
def mock_config():
    cfg = Config()
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.enabled = True
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    mock_modbus = MagicMock()
    mock_modbus.scan_interval.low = 600
    mock_modbus.scan_interval.medium = 60
    mock_modbus.scan_interval.high = 10
    mock_modbus.scan_interval.realtime = 5
    cfg.modbus = [mock_modbus]
    cfg.sensor_overrides = {}
    cfg.consumption = ConsumptionMethod.CALCULATED

    with _swap_active_config(cfg):
        yield cfg


class TestBasicDerivedSensorsCoverage:
    def test_battery_charging_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import BatteryChargingPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            bp = MagicMock(spec=BatteryPower)
            bp.device_class = DeviceClass.POWER
            bp.state_class = StateClass.MEASUREMENT
            bp.protocol_version = Protocol.V2_4
            sensor = BatteryChargingPower(0, bp)
            assert "BatteryPower > 0" in str(sensor.get_attributes()["source"])

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor))
            assert "Attempt to call" in caplog.text

    def test_battery_discharging_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import BatteryDischargingPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            bp = MagicMock(spec=BatteryPower)
            bp.device_class = DeviceClass.POWER
            bp.state_class = StateClass.MEASUREMENT
            bp.protocol_version = Protocol.V2_4
            sensor = BatteryDischargingPower(0, bp)
            assert "BatteryPower < 0" in str(sensor.get_attributes()["source"])

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor))
            assert "Attempt to call" in caplog.text

    def test_grid_export_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import GridSensorExportPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            gp = MagicMock(spec=GridSensorActivePower)
            gp.device_class = DeviceClass.POWER
            gp.state_class = StateClass.MEASUREMENT
            gp.precision = 2
            gp.protocol_version = Protocol.V2_4
            sensor = GridSensorExportPower(0, gp)
            assert "GridSensorActivePower < 0" in str(sensor.get_attributes()["source"])

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor))
            assert "Attempt to call" in caplog.text

    def test_grid_import_power(self, caplog):
        from sigenergy2mqtt.sensors.plant_derived import GridSensorImportPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            gp = MagicMock(spec=GridSensorActivePower)
            gp.device_class = DeviceClass.POWER
            gp.state_class = StateClass.MEASUREMENT
            gp.precision = 2
            gp.protocol_version = Protocol.V2_4
            sensor = GridSensorImportPower(0, gp)
            assert "GridSensorActivePower > 0" in str(sensor.get_attributes()["source"])

            # Error branch
            sensor.set_source_values(MagicMock(spec=Sensor))
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
            source_exp.device_class = DeviceClass.ENERGY
            source_exp.state_class = "total_increasing"
            source_exp.precision = 2
            s_exp = GridSensorDailyExportEnergy(0, source_exp)
            assert "PlantTotalExportedEnergy" in str(s_exp.get_attributes()["source"])

            # Import
            source_imp = MagicMock(spec=PlantTotalImportedEnergy)
            source_imp.unique_id = "imp_uid"
            source_imp.data_type = ModbusDataType.UINT32
            source_imp.protocol_version = Protocol.V2_4
            source_imp.unit = "kWh"
            source_imp.object_id = "imp_oid"
            source_imp.device_class = DeviceClass.ENERGY
            source_imp.state_class = "total_increasing"
            source_imp.precision = 2
            s_imp = GridSensorDailyImportEnergy(0, source_imp)
            assert "PlantTotalImportedEnergy" in str(s_imp.get_attributes()["source"])

            # Total PV
            source_tpv = MagicMock(spec=PlantPVTotalGeneration)
            source_tpv.unique_id = "tpv_uid"
            source_tpv.data_type = ModbusDataType.UINT32
            source_tpv.protocol_version = Protocol.V2_4
            source_tpv.unit = "kWh"
            source_tpv.object_id = "tpv_oid"
            source_tpv.device_class = DeviceClass.ENERGY
            source_tpv.state_class = "total_increasing"
            source_tpv.precision = 2
            s_tpv = TotalDailyPVEnergy(0, source_tpv)
            assert "TotalLifetimePVEnergy" in str(s_tpv.get_attributes()["source"])

            # Plant Daily PV
            s_pdpv = PlantDailyPVEnergy(0, source_tpv)
            assert "PlantLifetimePVEnergy" in str(s_pdpv.get_attributes()["source"])

            # Plant Daily Charge
            from sigenergy2mqtt.sensors.plant_read_only import ESSTotalChargedEnergy, ESSTotalDischargedEnergy

            source_charge = MagicMock(spec=ESSTotalChargedEnergy)
            source_charge.unique_id = "ch_uid"
            source_charge.data_type = ModbusDataType.UINT32
            source_charge.protocol_version = Protocol.V2_4
            source_charge.unit = "kWh"
            source_charge.object_id = "ch_oid"
            source_charge.device_class = DeviceClass.ENERGY
            source_charge.state_class = "total_increasing"
            source_charge.precision = 2
            s_pdc = PlantDailyChargeEnergy(0, source_charge)
            assert "DailyChargeEnergy" in str(s_pdc.get_attributes()["source"])

            # Plant Daily Discharge
            source_discharge = MagicMock(spec=ESSTotalDischargedEnergy)
            source_discharge.unique_id = "dis_uid"
            source_discharge.data_type = ModbusDataType.UINT32
            source_discharge.protocol_version = Protocol.V2_4
            source_discharge.unit = "kWh"
            source_discharge.object_id = "dis_oid"
            source_discharge.device_class = DeviceClass.ENERGY
            source_discharge.state_class = "total_increasing"
            source_discharge.precision = 2
            s_pdd = PlantDailyDischargeEnergy(0, source_discharge)
            assert "DailyDischargeEnergy" in str(s_pdd.get_attributes()["source"])


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
            s_gen = PlantConsumedPower(0, method=ConsumptionMethod.GENERAL)
            assert s_gen.get_attributes()["source"] == "GeneralLoadPower"

            s_tot = PlantConsumedPower(0, method=ConsumptionMethod.TOTAL)
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

    def test_finalise_binding_with_chargers(self):
        from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerChargingPower

        charger = MagicMock()
        # Create a dummy ACChargerChargingPower instance without calling its __init__
        ac_sensor = ACChargerChargingPower.__new__(ACChargerChargingPower)
        ac_sensor.unique_id = "ac_uid"
        ac_sensor.gain = 1.0
        ac_sensor.scan_interval = 10
        ac_sensor.protocol_version = Protocol.V1_8
        ac_sensor._publishable = True
        charger.get_all_sensors = MagicMock(return_value={"ac_uid": ac_sensor})
        charger.get_sensor = MagicMock(return_value=ac_sensor)

        sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
        sensor.debug_logging = True
        sensor.parent_device = type("Parent", (), {"protocol_version": Protocol.V1_8})()

        with patch("sigenergy2mqtt.devices.base.registry.DeviceRegistry.get", return_value=[charger]):
            result = sensor.finalise_binding(0)
            assert isinstance(result, bool)
            if result:
                assert "ac_uid" in sensor._sources

    def test_set_source_values_branches(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)

            # GridStatus restoration/detected
            gs = MagicMock(spec=GridStatus)
            gs.unique_id = "gs"

            # Initial status (sets _grid_status = 0)
            gs.latest_raw_state = 0
            sensor.set_source_values(gs)
            assert sensor._grid_status == 0

            # Off grid transition
            gs.latest_raw_state = 1
            sensor.set_source_values(gs)
            assert sensor._grid_status == 1
            assert "Off Grid detected" in caplog.text

            # Grid restored transition
            gs.latest_raw_state = 0
            sensor.set_source_values(gs)
            assert sensor._grid_status == 0
            assert "Grid restored" in caplog.text

            # Unrecognized sensor
            assert sensor.set_source_values(MagicMock(spec=Sensor)) is False


class TestTotalPVPowerCoverage:
    def test_value_repr(self):
        val = TotalPVPower.Value(gain=1.0, state=100.0)
        assert "state=100.0" in repr(val)

    @pytest.mark.asyncio
    async def test_publish_skipped(self):
        sensor = TotalPVPower(0)
        sensor.debug_logging = True
        sensor.configure_mqtt_topics("test_device")
        sensor._sources["t1"] = TotalPVPower.Value(gain=1.0, state=None)
        assert await sensor.publish(MagicMock(), None) is False

        sensor._sources["t1"].state = 100.0
        with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock):
            assert await sensor.publish(MagicMock(), None) is True

    def test_set_source_values_ignored(self, caplog):
        sensor = TotalPVPower(0)
        sensor.debug_logging = True
        # Not a PVPowerSensor
        ms = MagicMock(spec=Sensor)
        ms.unique_id = "ms_uid"
        assert sensor.set_source_values(ms) is False
        assert "not PVPowerSensor instance" in caplog.text

        # Not registered
        s1 = MagicMock(spec=PVPowerSensor)
        s1.unique_id = "unregistered"
        assert sensor.set_source_values(s1) is False
        assert "sensor is not registered" in caplog.text

    def test_set_source_values_debug(self, caplog):
        caplog.set_level(logging.DEBUG)
        s1 = MagicMock(spec=PVPowerSensor)
        s1.unique_id = "s1"
        s1.gain = 1.0
        s1.latest_raw_state = 100.0
        sensor = TotalPVPower(0, s1)
        sensor.debug_logging = True
        sensor.set_source_values(s1)

        assert "Updated from source 's1'" in caplog.text


class TestTotalLifetimePVEnergyCoverage:
    def test_get_discovery_components(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0, PlantPVTotalGeneration(0), ThirdPartyLifetimePVEnergy(0))
            sensor.get_attributes()
            comps = sensor.get_discovery_components()
            assert f"{sensor.unique_id}_reset" in comps

    @pytest.mark.asyncio
    async def test_publish_skipped_and_reset(self, caplog):
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0, PlantPVTotalGeneration(0), ThirdPartyLifetimePVEnergy(0))
            sensor.debug_logging = True
            sensor.configure_mqtt_topics("test_device")
            assert await sensor.publish(MagicMock(), None) is False
            assert "Publishing SKIPPED" in caplog.text

            sensor.plant_lifetime_pv_energy = 100.0
            sensor.plant_3rd_party_lifetime_pv_energy = 50.0
            with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock):
                assert await sensor.publish(MagicMock(), None) is True
                assert "Publishing READY" in caplog.text
                assert sensor.plant_lifetime_pv_energy is None
                assert sensor.plant_3rd_party_lifetime_pv_energy is None

    def test_set_source_values_branches(self, caplog):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0, PlantPVTotalGeneration(0), ThirdPartyLifetimePVEnergy(0))

            # PlantPVTotalGeneration
            sg = MagicMock(spec=PlantPVTotalGeneration)
            sg.latest_raw_state = 1000.0
            sensor.set_source_values(sg)
            assert sensor.plant_lifetime_pv_energy == 1000.0

            # ThirdPartyLifetimePVEnergy
            tp = MagicMock(spec=ThirdPartyLifetimePVEnergy)
            tp.latest_raw_state = 500.0
            sensor.set_source_values(tp)
            assert sensor.plant_3rd_party_lifetime_pv_energy == 500.0
            assert sensor.latest_raw_state == 1500.0

            # Unrecognized
            assert sensor.set_source_values(MagicMock(spec=Sensor)) is False
            assert "Attempt to call" in caplog.text


class TestPlantSelfConsumedPowerCoverage:
    def test_finalise_binding_no_sources(self, caplog):
        from sigenergy2mqtt.devices.base.registry import DeviceRegistry
        from sigenergy2mqtt.sensors.plant_derived import PlantSelfConsumedPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantSelfConsumedPower(0)
            DeviceRegistry.clear()

            # empty registry
            assert sensor.finalise_binding(0) is False
            assert "no publishable InverterSelfConsumedPower sensors found" in caplog.text

    def test_finalise_binding_with_sources(self):
        from sigenergy2mqtt.devices.base.device import Device
        from sigenergy2mqtt.devices.base.registry import DeviceRegistry
        from sigenergy2mqtt.sensors.inverter_derived import InverterSelfConsumedPower
        from sigenergy2mqtt.sensors.plant_derived import PlantSelfConsumedPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantSelfConsumedPower(0)
            DeviceRegistry.clear()

            dev = Device(name="Dev", plant_index=0, unique_id="uid", manufacturer="m", model="m", protocol_version=Protocol.V1_8)
            DeviceRegistry.add(0, dev)

            inv_sensor = MagicMock(spec=InverterSelfConsumedPower)
            inv_sensor.object_id = "inv_sensor"
            inv_sensor.publishable = True

            # mock dev.get_all_sensors
            dev.get_all_sensors = MagicMock(return_value={"inv_sensor": inv_sensor})

            # We mock the parent finalise_binding which calls bind_cross_device_sensors logic,
            # here we can just test if the cross_device sources are declared.
            with patch("sigenergy2mqtt.sensors.base.CrossDeviceDerivedSensor.finalise_binding", return_value=True):
                assert sensor.finalise_binding(0) is True
                assert "inv_sensor" in sensor._values

    def test_get_attributes(self):
        from sigenergy2mqtt.sensors.plant_derived import PlantSelfConsumedPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantSelfConsumedPower(0)
            assert "∑ of InverterSelfConsumedPower" in sensor.get_attributes()["source"]

    @pytest.mark.asyncio
    async def test_publish_skipped_and_ready(self, caplog):
        import logging

        from sigenergy2mqtt.sensors.plant_derived import PlantSelfConsumedPower

        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantSelfConsumedPower(0)
            sensor.debug_logging = True
            sensor._values = {"s1": None}

            assert await sensor.publish(MagicMock(), None) is False
            assert "Publishing SKIPPED" in caplog.text

            sensor._values = {"s1": 100}
            with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock):
                assert await sensor.publish(MagicMock(), None) is True
                assert "Publishing READY" in caplog.text
                assert sensor._values["s1"] is None

    def test_set_source_values(self, caplog):
        from sigenergy2mqtt.sensors.inverter_derived import InverterSelfConsumedPower
        from sigenergy2mqtt.sensors.plant_derived import PlantSelfConsumedPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantSelfConsumedPower(0)
            sensor.debug_logging = True
            sensor._values = {"inv_sensor": None}

            assert sensor.set_source_values(MagicMock(spec=Sensor)) is False
            assert "Attempt to call" in caplog.text

            inv_sensor = MagicMock(spec=InverterSelfConsumedPower)
            inv_sensor.object_id = "inv_sensor"
            inv_sensor.latest_raw_state = 250

            sensor.set_source_values(inv_sensor)
            assert sensor._values["inv_sensor"] == 250
            assert sensor.latest_raw_state == 250


class TestPlantDailySelfConsumedEnergyCoverage:
    def test_daily_self_consumed_energy(self):
        from sigenergy2mqtt.sensors.plant_derived import PlantDailySelfConsumedEnergy, PlantSelfConsumedPower

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            source = MagicMock(spec=PlantSelfConsumedPower)
            source.unique_id = "source_uid"

            sensor = PlantDailySelfConsumedEnergy(0, source)
            assert "Riemann ∑ of PlantSelfConsumedPower" in sensor.get_attributes()["source"]
