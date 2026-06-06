import pytest
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor
from unittest.mock import patch

@pytest.fixture(autouse=True)
def plant_config():
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    with _swap_active_config(cfg):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            yield cfg
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()

PLANT_INDEX = 0

class TestPlantReadOnlySensors:

    def test_system_time(self):
        from sigenergy2mqtt.sensors.plant_read_only import SystemTime
        from datetime import timezone, timedelta
        s = SystemTime(PLANT_INDEX, timezone(timedelta(hours=1)))
        assert s.address == 30000

    def test_system_time_zone(self):
        from sigenergy2mqtt.sensors.plant_read_only import SystemTimeZone
        s = SystemTimeZone(PLANT_INDEX)
        assert s.address == 30002

    def test_e_m_s_work_mode(self):
        from sigenergy2mqtt.sensors.plant_read_only import EMSWorkMode
        s = EMSWorkMode(PLANT_INDEX)
        assert s.address == 30003

    def test_grid_sensor_status(self):
        from sigenergy2mqtt.sensors.plant_read_only import GridSensorStatus
        s = GridSensorStatus(PLANT_INDEX)
        assert s.address == 30004

    def test_grid_sensor_active_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import GridSensorActivePower
        s = GridSensorActivePower(PLANT_INDEX)
        assert s.address == 30005

    def test_grid_sensor_reactive_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import GridSensorReactivePower
        s = GridSensorReactivePower(PLANT_INDEX)
        assert s.address == 30007

    def test_grid_status(self):
        from sigenergy2mqtt.sensors.plant_read_only import GridStatus
        s = GridStatus(PLANT_INDEX)
        assert s.address == 30009

    def test_max_active_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import MaxActivePower
        s = MaxActivePower(PLANT_INDEX)
        assert s.address == 30010

    def test_max_apparent_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import MaxApparentPower
        s = MaxApparentPower(PLANT_INDEX)
        assert s.address == 30012

    def test_plant_battery_so_c(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantBatterySoC
        s = PlantBatterySoC(PLANT_INDEX)
        assert s.address == 30014

    def test_plant_active_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantActivePower
        s = PlantActivePower(PLANT_INDEX)
        assert s.address == 30031

    def test_plant_reactive_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantReactivePower
        s = PlantReactivePower(PLANT_INDEX)
        assert s.address == 30033

    def test_plant_p_v_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantPVPower
        s = PlantPVPower(PLANT_INDEX)
        assert s.address == 30035

    def test_battery_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import BatteryPower
        s = BatteryPower(PLANT_INDEX)
        assert s.address == 30037

    def test_available_max_active_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMaxActivePower
        s = AvailableMaxActivePower(PLANT_INDEX)
        assert s.address == 30039

    def test_available_min_active_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMinActivePower
        s = AvailableMinActivePower(PLANT_INDEX)
        assert s.address == 30041

    def test_available_max_reactive_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMaxReactivePower
        s = AvailableMaxReactivePower(PLANT_INDEX)
        assert s.address == 30043

    def test_available_min_reactive_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMinReactivePower
        s = AvailableMinReactivePower(PLANT_INDEX)
        assert s.address == 30045

    def test_available_max_charging_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMaxChargingPower
        s = AvailableMaxChargingPower(PLANT_INDEX)
        assert s.address == 30047

    def test_available_max_discharging_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMaxDischargingPower
        s = AvailableMaxDischargingPower(PLANT_INDEX)
        assert s.address == 30049

    def test_available_max_charging_capacity(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMaxChargingCapacity
        s = AvailableMaxChargingCapacity(PLANT_INDEX)
        assert s.address == 30064

    def test_available_max_discharging_capacity(self):
        from sigenergy2mqtt.sensors.plant_read_only import AvailableMaxDischargingCapacity
        s = AvailableMaxDischargingCapacity(PLANT_INDEX)
        assert s.address == 30066

    def test_plant_rated_charging_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantRatedChargingPower
        s = PlantRatedChargingPower(PLANT_INDEX)
        assert s.address == 30068

    def test_plant_rated_discharging_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantRatedDischargingPower
        s = PlantRatedDischargingPower(PLANT_INDEX)
        assert s.address == 30070

    def test_reserved30073(self):
        from sigenergy2mqtt.sensors.plant_read_only import Reserved30073
        s = Reserved30073(PLANT_INDEX)
        assert s.address == 30073

    def test_plant_rated_energy_capacity(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantRatedEnergyCapacity
        s = PlantRatedEnergyCapacity(PLANT_INDEX)
        assert s.address == 30083

    def test_charge_cut_off_so_c(self):
        from sigenergy2mqtt.sensors.plant_read_only import ChargeCutOffSoC
        s = ChargeCutOffSoC(PLANT_INDEX)
        assert s.address == 30085

    def test_discharge_cut_off_so_c(self):
        from sigenergy2mqtt.sensors.plant_read_only import DischargeCutOffSoC
        s = DischargeCutOffSoC(PLANT_INDEX)
        assert s.address == 30086

    def test_plant_battery_so_h(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantBatterySoH
        s = PlantBatterySoH(PLANT_INDEX)
        assert s.address == 30087

    def test_plant_p_v_total_generation(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantPVTotalGeneration
        s = PlantPVTotalGeneration(PLANT_INDEX)
        assert s.address == 30088

    def test_total_load_daily_consumption(self):
        from sigenergy2mqtt.sensors.plant_read_only import TotalLoadDailyConsumption
        s = TotalLoadDailyConsumption(PLANT_INDEX)
        assert s.address == 30092

    def test_total_load_consumption(self):
        from sigenergy2mqtt.sensors.plant_read_only import TotalLoadConsumption
        s = TotalLoadConsumption(PLANT_INDEX)
        assert s.address == 30094

    def test_third_party_p_v_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import ThirdPartyPVPower
        s = ThirdPartyPVPower(PLANT_INDEX)
        assert s.address == 30194

    def test_third_party_lifetime_p_v_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import ThirdPartyLifetimePVEnergy
        s = ThirdPartyLifetimePVEnergy(PLANT_INDEX)
        assert s.address == 30196

    def test_e_s_s_total_charged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import ESSTotalChargedEnergy
        s = ESSTotalChargedEnergy(PLANT_INDEX)
        assert s.address == 30200

    def test_e_s_s_total_discharged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import ESSTotalDischargedEnergy
        s = ESSTotalDischargedEnergy(PLANT_INDEX)
        assert s.address == 30204

    def test_e_v_d_c_total_charged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import EVDCTotalChargedEnergy
        s = EVDCTotalChargedEnergy(PLANT_INDEX)
        assert s.address == 30208

    def test_e_v_d_c_total_discharged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import EVDCTotalDischargedEnergy
        s = EVDCTotalDischargedEnergy(PLANT_INDEX)
        assert s.address == 30212

    def test_plant_total_imported_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantTotalImportedEnergy
        s = PlantTotalImportedEnergy(PLANT_INDEX)
        assert s.address == 30216

    def test_plant_total_exported_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantTotalExportedEnergy
        s = PlantTotalExportedEnergy(PLANT_INDEX)
        assert s.address == 30220

    def test_plant_total_generator_output_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantTotalGeneratorOutputEnergy
        s = PlantTotalGeneratorOutputEnergy(PLANT_INDEX)
        assert s.address == 30224

    def test_s_i_total_common_load_consumption(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalCommonLoadConsumption
        s = SITotalCommonLoadConsumption(PLANT_INDEX)
        assert s.address == 30228

    def test_s_i_total_e_v_a_c_charged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalEVACChargedEnergy
        s = SITotalEVACChargedEnergy(PLANT_INDEX)
        assert s.address == 30232

    def test_s_i_total_self_p_v_generation(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalSelfPVGeneration
        s = SITotalSelfPVGeneration(PLANT_INDEX)
        assert s.address == 30236

    def test_s_i_total_third_party_p_v_generation(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalThirdPartyPVGeneration
        s = SITotalThirdPartyPVGeneration(PLANT_INDEX)
        assert s.address == 30240

    def test_s_i_total_charged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalChargedEnergy
        s = SITotalChargedEnergy(PLANT_INDEX)
        assert s.address == 30244

    def test_s_i_total_discharged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalDischargedEnergy
        s = SITotalDischargedEnergy(PLANT_INDEX)
        assert s.address == 30248

    def test_s_i_total_e_v_d_c_charged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalEVDCChargedEnergy
        s = SITotalEVDCChargedEnergy(PLANT_INDEX)
        assert s.address == 30252

    def test_s_i_total_e_v_d_c_discharged_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalEVDCDischargedEnergy
        s = SITotalEVDCDischargedEnergy(PLANT_INDEX)
        assert s.address == 30256

    def test_s_i_total_imported_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalImportedEnergy
        s = SITotalImportedEnergy(PLANT_INDEX)
        assert s.address == 30260

    def test_s_i_total_exported_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalExportedEnergy
        s = SITotalExportedEnergy(PLANT_INDEX)
        assert s.address == 30264

    def test_s_i_total_generator_output_energy(self):
        from sigenergy2mqtt.sensors.plant_read_only import SITotalGeneratorOutputEnergy
        s = SITotalGeneratorOutputEnergy(PLANT_INDEX)
        assert s.address == 30268

    def test_plant_p_v_total_generation_today(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantPVTotalGenerationToday
        s = PlantPVTotalGenerationToday(PLANT_INDEX)
        assert s.address == 30272

    def test_plant_p_v_total_generation_yesterday(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantPVTotalGenerationYesterday
        s = PlantPVTotalGenerationYesterday(PLANT_INDEX)
        assert s.address == 30274

    def test_grid_code_rated_frequency(self):
        from sigenergy2mqtt.sensors.plant_read_only import GridCodeRatedFrequency
        s = GridCodeRatedFrequency(PLANT_INDEX)
        assert s.address == 30276

    def test_grid_code_rated_voltage(self):
        from sigenergy2mqtt.sensors.plant_read_only import GridCodeRatedVoltage
        s = GridCodeRatedVoltage(PLANT_INDEX)
        assert s.address == 30277

    def test_current_control_command_value(self):
        from sigenergy2mqtt.sensors.plant_read_only import CurrentControlCommandValue
        s = CurrentControlCommandValue(PLANT_INDEX)
        assert s.address == 30279

    def test_alarm6(self):
        from sigenergy2mqtt.sensors.plant_read_only import Alarm6
        s = Alarm6(PLANT_INDEX)
        assert s.address == 30280

    def test_alarm7(self):
        from sigenergy2mqtt.sensors.plant_read_only import Alarm7
        s = Alarm7(PLANT_INDEX)
        assert s.address == 30281

    def test_general_load_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import GeneralLoadPower
        s = GeneralLoadPower(PLANT_INDEX)
        assert s.address == 30282

    def test_total_load_power(self):
        from sigenergy2mqtt.sensors.plant_read_only import TotalLoadPower
        s = TotalLoadPower(PLANT_INDEX)
        assert s.address == 30284

    def test_e_s_s_average_cell_temperature(self):
        from sigenergy2mqtt.sensors.plant_read_only import ESSAverageCellTemperature
        s = ESSAverageCellTemperature(PLANT_INDEX)
        assert s.address == 30286
