# MQTT Topics

Topics prefixed with `homeassistant/` are used when the `home-assistant` configuration `enabled` option in the configuration file,
or the `SIGENERGY2MQTT_HASS_ENABLED` environment variable, are set to true, or the `--hass-enabled` command line option is specified.
Otherwise, the topics prefixed with `sigenergy2mqtt/` are used.

The number after the `sigen_` prefix represents the host index from the configuration file, starting from 0. (Home Assistant configuration may change the `sigen` topic prefix.)
Inverter, AC Charger and DC Charger indexes use the device address (slave ID) as specified in the configuration file.

Scan Intervals are shown in seconds. Intervals for derived sensors are dependent on the source sensors.

## Published Topics

### Plant
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| SystemTime | sigenergy2mqtt/sigen_0_plant_system_time/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time/state | Modbus Register 30000 | 60 ||
| SystemTimeZone | sigenergy2mqtt/sigen_0_plant_system_time_zone/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time_zone/state | Modbus Register 30002 | 600 ||
| EMSWorkMode | sigenergy2mqtt/sigen_0_plant_ems_work_mode/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_ems_work_mode/state | Modbus Register 30003 | 10 ||
| MaxActivePower | sigenergy2mqtt/sigen_0_plant_max_active_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_active_power/state | Modbus Register 30010 | 600 ||
| MaxApparentPower | sigenergy2mqtt/sigen_0_plant_max_apparent_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_apparent_power/state | Modbus Register 30012 | 600 ||
| PlantBatterySoC | sigenergy2mqtt/sigen_0_plant_battery_soc/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soc/state | Modbus Register 30014 | 60 ||
| PlantPhaseAActivePower | sigenergy2mqtt/sigen_0_plant_phase_a_active_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power/state | Modbus Register 30015 | 10 ||
| PlantPhaseAReactivePower | sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power/state | Modbus Register 30021 | 10 ||
| PlantPhaseBActivePower | sigenergy2mqtt/sigen_0_plant_phase_b_active_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power/state | Modbus Register 30017 | 10 ||
| PlantPhaseBReactivePower | sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power/state | Modbus Register 30023 | 10 ||
| PlantPhaseCActivePower | sigenergy2mqtt/sigen_0_plant_phase_c_active_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power/state | Modbus Register 30019 | 10 ||
| PlantPhaseCReactivePower | sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power/state | Modbus Register 30025 | 10 ||
| GeneralPCSAlarm | sigenergy2mqtt/sigen_0_general_pcs_alarm/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_pcs_alarm/state | Modbus Registers 30027 and 30028| 10 ||
| GeneralAlarm3 | sigenergy2mqtt/sigen_0_general_alarm_3/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_3/state | Modbus Register 30029 | 10 ||
| GeneralAlarm4 | sigenergy2mqtt/sigen_0_general_alarm_4/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_4/state | Modbus Register 30030 | 10 ||
| GeneralAlarm5 | sigenergy2mqtt/sigen_0_general_alarm_5/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_5/state | Modbus Register 30072 | 10 ||
| PlantActivePower | sigenergy2mqtt/sigen_0_plant_active_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_active_power/state | Modbus Register 30031 | 5 ||
| PlantReactivePower | sigenergy2mqtt/sigen_0_plant_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_reactive_power/state | Modbus Register 30033 | 5 ||
| PlantPVPower | sigenergy2mqtt/sigen_0_plant_pv_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_pv_power/state | Modbus Register 30035 | 5 ||
| TotalPVPower | sigenergy2mqtt/sigen_0_total_pv_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_pv_power/state | PlantPVPower &plus; &sum; of all configured SmartPort MQTT sources and SmartPort modules|||
| PlantConsumedPower | sigenergy2mqtt/sigen_0_consumed_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_consumed_power/state | (either PlantPVPower _or_ TotalPVPower) &plus; GridSensorActivePower &minus; BatteryPower|||
| PlantLifetimeConsumedEnergy | sigenergy2mqtt/sigen_0_lifetime_consumed_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_consumed_energy/state | Riemann &sum; of PlantConsumedPower|||
| PlantDailyConsumedEnergy | sigenergy2mqtt/sigen_0_daily_consumed_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_consumed_energy/state | PlantLifetimeConsumedEnergy &minus; PlantLifetimeConsumedEnergy at last midnight|||
| PlantLifetimePVEnergy | sigenergy2mqtt/sigen_0_lifetime_pv_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_pv_energy/state | Riemann &sum; of (either PlantPVPower _or_ TotalPVPower)|||
| PlantDailyPVEnergy | sigenergy2mqtt/sigen_0_daily_pv_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_pv_energy/state | PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight|||
| BatteryPower | sigenergy2mqtt/sigen_0_plant_battery_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_power/state | Modbus Register 30037 | 5 ||
| BatteryChargingPower | sigenergy2mqtt/sigen_0_battery_charging_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_charging_power/state | BatteryPower &gt; 0|||
| BatteryDischargingPower | sigenergy2mqtt/sigen_0_battery_discharging_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_discharging_power/state | BatteryPower &lt; 0|||
| AvailableMaxActivePower | sigenergy2mqtt/sigen_0_plant_available_max_active_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_active_power/state | Modbus Register 30039 | 600 ||
| AvailableMinActivePower | sigenergy2mqtt/sigen_0_plant_available_min_active_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_active_power/state | Modbus Register 30041 | 600 ||
| AvailableMaxReactivePower | sigenergy2mqtt/sigen_0_plant_available_max_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_reactive_power/state | Modbus Register 30043 | 600 ||
| AvailableMinReactivePower | sigenergy2mqtt/sigen_0_plant_available_min_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_reactive_power/state | Modbus Register 30045 | 600 ||
| AvailableMaxChargingPower | sigenergy2mqtt/sigen_0_plant_available_max_charging_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_power/state | Modbus Register 30047 | 600 ||
| AvailableMaxDischargingPower | sigenergy2mqtt/sigen_0_plant_available_max_discharging_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_power/state | Modbus Register 30049 | 600 ||
| PlantRunningState | sigenergy2mqtt/sigen_0_plant_running_state/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_running_state/state | Modbus Register 30051 | 10 ||
| AvailableMaxChargingCapacity | sigenergy2mqtt/sigen_0_plant_available_max_charging_capacity/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_capacity/state | Modbus Register 30064 | 60 ||
| AvailableMaxDischargingCapacity | sigenergy2mqtt/sigen_0_plant_available_max_discharging_capacity/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_capacity/state | Modbus Register 30066 | 60 ||
| PlantRatedChargingPower | sigenergy2mqtt/sigen_0_plant_rated_charging_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_charging_power/state | Modbus Register 30068 | 600 ||
| PlantRatedDischargingPower | sigenergy2mqtt/sigen_0_plant_rated_discharging_power/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_discharging_power/state | Modbus Register 30070 | 600 ||
| PlantRatedEnergyCapacity | sigenergy2mqtt/sigen_0_plant_rated_energy_capacity/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_energy_capacity/state | Modbus Register 30083 | 600 ||
| ChargeCutOffSoC | sigenergy2mqtt/sigen_0_plant_charge_cut_off_soc/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_charge_cut_off_soc/state | Modbus Register 30085 | 60 ||
| DischargeCutOffSoC | sigenergy2mqtt/sigen_0_plant_discharge_cut_off_soc/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_discharge_cut_off_soc/state | Modbus Register 30086 | 60 ||
| PlantBatterySoH | sigenergy2mqtt/sigen_0_plant_battery_soh/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soh/state | Modbus Register 30087 | 60 ||
| RemoteEMS | sigenergy2mqtt/sigen_0_plant_remote_ems/state <br/> homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_remote_ems/state | Modbus Register 40029 | 10 ||
| RemoteEMSControlMode | sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/state <br/> homeassistant/select/sigen_0_247_powerplant/sigen_0_plant_remote_ems_control_mode/state | Modbus Register 40031 | 60 ||
| ActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_fixed_adjustment_target_value/state | Modbus Register 40001 | 60 ||
| ReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40003 | 60 ||
| ActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_percentage_adjustment_target_value/state | Modbus Register 40005 | 60 ||
| QSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_q_s_adjustment_target_value/state | Modbus Register 40006 | 60 ||
| PowerFactorAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_power_factor_adjustment_target_value/state | Modbus Register 40007 | 60 ||
| PhaseAActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state | Modbus Register 40008 | 60 ||
| PhaseAReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40014 | 60 ||
| PhaseAActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state | Modbus Register 40020 | 60 ||
| PhaseAQSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state | Modbus Register 40023 | 60 ||
| PhaseBActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state | Modbus Register 40010 | 60 ||
| PhaseBReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40016 | 60 ||
| PhaseBActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state | Modbus Register 40021 | 60 ||
| PhaseBQSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state | Modbus Register 40024 | 60 ||
| IndependentPhasePowerControl | sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/state <br/> homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_independent_phase_power_control/state | Modbus Register 40030 | 60 ||
| PhaseCActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state | Modbus Register 40012 | 60 ||
| PhaseCReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40018 | 60 ||
| PhaseCActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state | Modbus Register 40022 | 60 ||
| PhaseCQSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state | Modbus Register 40025 | 60 ||
| MaxChargingLimit | sigenergy2mqtt/sigen_0_plant_max_charging_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_charging_limit/state | Modbus Register 40032 | 10 ||
| MaxDischargingLimit | sigenergy2mqtt/sigen_0_plant_max_discharging_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_discharging_limit/state | Modbus Register 40034 | 10 ||
| PVMaxPowerLimit | sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pv_max_power_limit/state | Modbus Register 40036 | 10 ||
| GridMaxExportLimit | sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_export_limit/state | Modbus Register 40038 | 10 ||
| GridMaxImportLimit | sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_import_limit/state | Modbus Register 40040 | 10 ||
| PCSMaxExportLimit | sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_export_limit/state | Modbus Register 40042 | 10 ||
| PCSMaxImportLimit | sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_import_limit/state | Modbus Register 40044 | 10 ||
| PlantDailyChargeEnergy | sigenergy2mqtt/sigen_0_daily_charge_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_charge_energy/state | &sum; of DailyChargeEnergy across all Inverters associated with the Plant| 25 ||
| PlantDailyDischargeEnergy | sigenergy2mqtt/sigen_0_daily_discharge_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_discharge_energy/state | &sum; of DailyDischargeEnergy across all Inverters associated with the Plant| 25 ||
| PlantAccumulatedChargeEnergy | sigenergy2mqtt/sigen_0_accumulated_charge_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_charge_energy/state | &sum; of AccumulatedChargeEnergy across all Inverters associated with the Plant| 25 ||
| PlantAccumulatedDischargeEnergy | sigenergy2mqtt/sigen_0_accumulated_discharge_energy/state <br/> homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_discharge_energy/state | &sum; of AccumulatedDischargeEnergy across all Inverters associated with the Plant| 25 ||

#### Grid Sensor
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| GridSensorStatus | sigenergy2mqtt/sigen_0_plant_grid_sensor_status/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_status/state | Modbus Register 30004 | 10 ||
| GridSensorActivePower | sigenergy2mqtt/sigen_0_plant_grid_sensor_active_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_active_power/state | Modbus Register 30005 | 5 ||
| GridSensorExportPower | sigenergy2mqtt/sigen_0_grid_sensor_export_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_export_power/state | GridSensorActivePower &lt; 0 &times; -1|||
| GridSensorLifetimeExportEnergy | sigenergy2mqtt/sigen_0_grid_sensor_lifetime_export_energy/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_export_energy/state | Riemann &sum; of GridSensorExportPower|||
| GridSensorDailyExportEnergy | sigenergy2mqtt/sigen_0_grid_sensor_daily_export_energy/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_export_energy/state | GridSensorLifetimeExportEnergy &minus; GridSensorLifetimeExportEnergy at last midnight|||
| GridSensorImportPower | sigenergy2mqtt/sigen_0_grid_sensor_import_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_import_power/state | GridSensorActivePower &gt; 0|||
| GridSensorLifetimeImportEnergy | sigenergy2mqtt/sigen_0_grid_sensor_lifetime_import_energy/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_import_energy/state | Riemann &sum; of GridSensorImportPower|||
| GridSensorDailyImportEnergy | sigenergy2mqtt/sigen_0_grid_sensor_daily_import_energy/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_import_energy/state | GridSensorLifetimeImportEnergy &minus; GridSensorLifetimeImportEnergy at last midnight|||
| GridSensorReactivePower | sigenergy2mqtt/sigen_0_plant_grid_sensor_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_reactive_power/state | Modbus Register 30007 | 5 ||
| GridPhaseAActivePower | sigenergy2mqtt/sigen_0_plant_grid_phase_a_active_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_active_power/state | Modbus Register 30052 | 10 ||
| GridPhaseAReactivePower | sigenergy2mqtt/sigen_0_plant_grid_phase_a_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_reactive_power/state | Modbus Register 30058 | 10 ||
| GridPhaseBActivePower | sigenergy2mqtt/sigen_0_plant_grid_phase_b_active_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_active_power/state | Modbus Register 30054 | 10 ||
| GridPhaseBReactivePower | sigenergy2mqtt/sigen_0_plant_grid_phase_b_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_reactive_power/state | Modbus Register 30060 | 10 ||
| GridPhaseCActivePower | sigenergy2mqtt/sigen_0_plant_grid_phase_c_active_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_active_power/state | Modbus Register 30056 | 10 ||
| GridPhaseCReactivePower | sigenergy2mqtt/sigen_0_plant_grid_phase_c_reactive_power/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_reactive_power/state | Modbus Register 30062 | 10 ||
| GridStatus | sigenergy2mqtt/sigen_0_plant_grid_status/state <br/> homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_status/state | Modbus Register 30009 | 10 ||

#### Smart-Port
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| EnphasePVPower | sigenergy2mqtt/sigen_0_enphase_123456789012_active_power/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_active_power/state | Enphase Envoy API| 5 ||
| EnphaseLifetimePVEnergy | sigenergy2mqtt/sigen_0_enphase_123456789012_lifetime_pv_energy/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_lifetime_pv_energy/state | Enphase Envoy API when EnphasePVPower derived|||
| EnphaseDailyPVEnergy | sigenergy2mqtt/sigen_0_enphase_123456789012_daily_pv_energy/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_daily_pv_energy/state | Enphase Envoy API when EnphasePVPower derived|||
| EnphaseCurrent | sigenergy2mqtt/sigen_0_enphase_123456789012_current/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_current/state | Enphase Envoy API when EnphasePVPower derived|||
| EnphaseFrequency | sigenergy2mqtt/sigen_0_enphase_123456789012_frequency/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_frequency/state | Enphase Envoy API when EnphasePVPower derived|||
| EnphasePowerFactor | sigenergy2mqtt/sigen_0_enphase_123456789012_power_factor/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_power_factor/state | Enphase Envoy API when EnphasePVPower derived|||
| EnphaseReactivePower | sigenergy2mqtt/sigen_0_enphase_123456789012_reactive_power/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_reactive_power/state | Enphase Envoy API when EnphasePVPower derived|||
| EnphaseVoltage | sigenergy2mqtt/sigen_0_enphase_123456789012_voltage/state <br/> homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_voltage/state | Enphase Envoy API when EnphasePVPower derived|||

### Inverter
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| InverterFirmwareVersion | sigenergy2mqtt/sigen_0_inverter_1_firmware_version/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_firmware_version/state | Modbus Register 30525 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| RatedActivePower | sigenergy2mqtt/sigen_0_inverter_1_rated_active_power/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_active_power/state | Modbus Register 30540 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| MaxRatedApparentPower | sigenergy2mqtt/sigen_0_inverter_1_max_rated_apparent_power/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_rated_apparent_power/state | Modbus Register 30542 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| InverterMaxActivePower | sigenergy2mqtt/sigen_0_inverter_1_max_active_power/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power/state | Modbus Register 30544 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| MaxAbsorptionPower | sigenergy2mqtt/sigen_0_inverter_1_max_absorption_power/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_absorption_power/state | Modbus Register 30546 | 600 | Hybrid&nbsp;Inverter |
| DailyExportEnergy | sigenergy2mqtt/sigen_0_inverter_1_daily_export_energy/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_daily_export_energy/state | Modbus Register 30554 | 10 | Hybrid&nbsp;Inverter |
| AccumulatedExportEnergy | sigenergy2mqtt/sigen_0_inverter_1_accumulated_export_energy/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_accumulated_export_energy/state | Modbus Register 30556 | 10 | Hybrid&nbsp;Inverter |
| DailyImportEnergy | sigenergy2mqtt/sigen_0_inverter_1_daily_import_energy/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_daily_import_energy/state | Modbus Register 30560 | 10 | Hybrid&nbsp;Inverter |
| AccumulatedImportEnergy | sigenergy2mqtt/sigen_0_inverter_1_accumulated_import_energy/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_accumulated_import_energy/state | Modbus Register 30562 | 10 | Hybrid&nbsp;Inverter |
| InverterRunningState | sigenergy2mqtt/sigen_0_inverter_1_running_state/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_running_state/state | Modbus Register 30578 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| MaxActivePowerAdjustment | sigenergy2mqtt/sigen_0_inverter_1_max_active_power_adjustment/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power_adjustment/state | Modbus Register 30579 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| MinActivePowerAdjustment | sigenergy2mqtt/sigen_0_inverter_1_min_active_power_adjustment/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_active_power_adjustment/state | Modbus Register 30581 | 600 | Hybrid&nbsp;Inverter |
| MaxReactivePowerAdjustment | sigenergy2mqtt/sigen_0_inverter_1_max_reactive_power_adjustment/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_reactive_power_adjustment/state | Modbus Register 30583 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| MinReactivePowerAdjustment | sigenergy2mqtt/sigen_0_inverter_1_min_reactive_power_adjustment/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_reactive_power_adjustment/state | Modbus Register 30585 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| ActivePower | sigenergy2mqtt/sigen_0_inverter_1_active_power/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power/state | Modbus Register 30587 | 5 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| ReactivePower | sigenergy2mqtt/sigen_0_inverter_1_reactive_power/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power/state | Modbus Register 30589 | 5 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| InverterPCSAlarm | sigenergy2mqtt/sigen_0_inverter_1_pcs_alarm/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pcs_alarm/state | Modbus Registers 30605 and 30606| 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| InverterAlarm4 | sigenergy2mqtt/sigen_0_inverter_1_alarm_4/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_alarm_4/state | Modbus Register 30608 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| RatedGridVoltage | sigenergy2mqtt/sigen_0_inverter_1_rated_grid_voltage/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_voltage/state | Modbus Register 31000 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| RatedGridFrequency | sigenergy2mqtt/sigen_0_inverter_1_rated_grid_frequency/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_frequency/state | Modbus Register 31001 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| GridFrequency | sigenergy2mqtt/sigen_0_inverter_1_grid_frequency/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_grid_frequency/state | Modbus Register 31002 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| InverterTemperature | sigenergy2mqtt/sigen_0_inverter_1_temperature/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_temperature/state | Modbus Register 31003 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| OutputType | sigenergy2mqtt/sigen_0_inverter_1_output_type/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_output_type/state | Modbus Register 31004 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PhaseAVoltage | sigenergy2mqtt/sigen_0_inverter_1_phase_a_voltage/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_voltage/state | Modbus Register 31011 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PhaseACurrent | sigenergy2mqtt/sigen_0_inverter_1_phase_a_current/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_current/state | Modbus Register 31017 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PhaseBVoltage | sigenergy2mqtt/sigen_0_inverter_1_phase_b_voltage/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_voltage/state | Modbus Register 31013 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PhaseBCurrent | sigenergy2mqtt/sigen_0_inverter_1_phase_b_current/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_current/state | Modbus Register 31019 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| ABLineVoltage | sigenergy2mqtt/sigen_0_inverter_1_a_b_line_voltage/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_a_b_line_voltage/state | Modbus Register 31005 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PhaseCVoltage | sigenergy2mqtt/sigen_0_inverter_1_phase_c_voltage/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_voltage/state | Modbus Register 31015 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PhaseCCurrent | sigenergy2mqtt/sigen_0_inverter_1_phase_c_current/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_current/state | Modbus Register 31021 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| BCLineVoltage | sigenergy2mqtt/sigen_0_inverter_1_b_c_line_voltage/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_b_c_line_voltage/state | Modbus Register 31007 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| CALineVoltage | sigenergy2mqtt/sigen_0_inverter_1_c_a_line_voltage/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_c_a_line_voltage/state | Modbus Register 31009 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PowerFactor | sigenergy2mqtt/sigen_0_inverter_1_power_factor/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_power_factor/state | Modbus Register 31023 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PACKBCUCount | sigenergy2mqtt/sigen_0_inverter_1_pack_bcu_count/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pack_bcu_count/state | Modbus Register 31024 | 60 | Hybrid&nbsp;Inverter |
| MPTTCount | sigenergy2mqtt/sigen_0_inverter_1_mptt_count/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_mptt_count/state | Modbus Register 31026 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVStringCount | sigenergy2mqtt/sigen_0_inverter_1_pv_string_count/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_string_count/state | Modbus Register 31025 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| InverterPVPower | sigenergy2mqtt/sigen_0_inverter_1_pv_power/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_power/state | Modbus Register 31035 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| InverterLifetimePVEnergy | sigenergy2mqtt/sigen_0_inverter_1_lifetime_pv_energy/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_lifetime_pv_energy/state | Riemann &sum; of InverterPVPower|||
| InverterDailyPVEnergy | sigenergy2mqtt/sigen_0_inverter_1_daily_pv_energy/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_daily_pv_energy/state | InverterLifetimePVEnergy &minus; InverterLifetimePVEnergy at last midnight|||
| InsulationResistance | sigenergy2mqtt/sigen_0_inverter_1_insulation_resistance/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_insulation_resistance/state | Modbus Register 31037 | 60 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| StartupTime | sigenergy2mqtt/sigen_0_inverter_1_startup_time/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_startup_time/state | Modbus Register 31038 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| ShutdownTime | sigenergy2mqtt/sigen_0_inverter_1_shutdown_time/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_shutdown_time/state | Modbus Register 31040 | 600 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| GridCode | sigenergy2mqtt/sigen_0_inverter_1_grid_code/state <br/> homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_grid_code/state | Modbus Register 40501 | 60 | Hybrid&nbsp;Inverter |
| InverterRemoteEMSDispatch | sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/state <br/> homeassistant/switch/sigen_0_001_inverter/sigen_0_inverter_1_remote_ems_dispatch/state | Modbus Register 41500 | 10 | PV&nbsp;Inverter |
| InverterActivePowerFixedValueAdjustment | sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment/state | Modbus Register 41501 | 60 | PV&nbsp;Inverter |
| InverterReactivePowerFixedValueAdjustment | sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state | Modbus Register 41503 | 60 | PV&nbsp;Inverter |
| InverterActivePowerPercentageAdjustment | sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment/state | Modbus Register 41505 | 60 | PV&nbsp;Inverter |
| InverterReactivePowerQSAdjustment | sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_q_s_adjustment/state | Modbus Register 41506 | 60 | PV&nbsp;Inverter |
| InverterPowerFactorAdjustment | sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment/state | Modbus Register 41507 | 60 | PV&nbsp;Inverter |

#### Energy Storage System
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| RatedChargingPower | sigenergy2mqtt/sigen_0_inverter_1_rated_charging_power/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_charging_power/state | Modbus Register 30550 | 600 | Hybrid&nbsp;Inverter |
| RatedDischargingPower | sigenergy2mqtt/sigen_0_inverter_1_rated_discharging_power/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_discharging_power/state | Modbus Register 30552 | 600 | Hybrid&nbsp;Inverter |
| MaxBatteryChargePower | sigenergy2mqtt/sigen_0_inverter_1_max_battery_charge_power/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_charge_power/state | Modbus Register 30591 | 600 | Hybrid&nbsp;Inverter |
| MaxBatteryDischargePower | sigenergy2mqtt/sigen_0_inverter_1_max_battery_discharge_power/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_discharge_power/state | Modbus Register 30593 | 600 | Hybrid&nbsp;Inverter |
| AvailableBatteryChargeEnergy | sigenergy2mqtt/sigen_0_inverter_1_available_battery_charge_energy/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_charge_energy/state | Modbus Register 30595 | 600 | Hybrid&nbsp;Inverter |
| AvailableBatteryDischargeEnergy | sigenergy2mqtt/sigen_0_inverter_1_available_battery_discharge_energy/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_discharge_energy/state | Modbus Register 30597 | 600 | Hybrid&nbsp;Inverter |
| InverterBatterySoC | sigenergy2mqtt/sigen_0_inverter_1_battery_soc/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soc/state | Modbus Register 30601 | 60 | Hybrid&nbsp;Inverter |
| InverterBatterySoH | sigenergy2mqtt/sigen_0_inverter_1_battery_soh/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soh/state | Modbus Register 30602 | 60 | Hybrid&nbsp;Inverter |
| AverageCellTemperature | sigenergy2mqtt/sigen_0_inverter_1_average_cell_temperature/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_temperature/state | Modbus Register 30603 | 10 | Hybrid&nbsp;Inverter |
| AverageCellVoltage | sigenergy2mqtt/sigen_0_inverter_1_average_cell_voltage/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_voltage/state | Modbus Register 30604 | 10 | Hybrid&nbsp;Inverter |
| InverterAlarm3 | sigenergy2mqtt/sigen_0_inverter_1_alarm_3/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_alarm_3/state | Modbus Register 30607 | 10 | Hybrid&nbsp;Inverter |
| InverterMaxBatteryTemperature | sigenergy2mqtt/sigen_0_inverter_1_max_battery_temperature/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_temperature/state | Modbus Register 30620 | 60 | Hybrid&nbsp;Inverter |
| InverterMinBatteryTemperature | sigenergy2mqtt/sigen_0_inverter_1_min_battery_temperature/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_min_battery_temperature/state | Modbus Register 30621 | 60 | Hybrid&nbsp;Inverter |
| InverterMaxCellVoltage | sigenergy2mqtt/sigen_0_inverter_1_max_cell_voltage/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_cell_voltage/state | Modbus Register 30622 | 60 | Hybrid&nbsp;Inverter |
| InverterMinCellVoltage | sigenergy2mqtt/sigen_0_inverter_1_min_cell_voltage/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_min_cell_voltage/state | Modbus Register 30623 | 60 | Hybrid&nbsp;Inverter |
| DailyChargeEnergy | sigenergy2mqtt/sigen_0_inverter_1_daily_charge_energy/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_charge_energy/state | Modbus Register 30566 | 10 | Hybrid&nbsp;Inverter |
| AccumulatedChargeEnergy | sigenergy2mqtt/sigen_0_inverter_1_accumulated_charge_energy/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_charge_energy/state | Modbus Register 30568 | 10 | Hybrid&nbsp;Inverter |
| DailyDischargeEnergy | sigenergy2mqtt/sigen_0_inverter_1_daily_discharge_energy/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_discharge_energy/state | Modbus Register 30572 | 10 | Hybrid&nbsp;Inverter |
| AccumulatedDischargeEnergy | sigenergy2mqtt/sigen_0_inverter_1_accumulated_discharge_energy/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_discharge_energy/state | Modbus Register 30574 | 10 | Hybrid&nbsp;Inverter |
| RatedBatteryCapacity | sigenergy2mqtt/sigen_0_inverter_1_rated_battery_capacity/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_battery_capacity/state | Modbus Register 30548 | 600 | Hybrid&nbsp;Inverter |
| ChargeDischargePower | sigenergy2mqtt/sigen_0_inverter_1_charge_discharge_power/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_charge_discharge_power/state | Modbus Register 30599 | 5 | Hybrid&nbsp;Inverter |
| InverterBatteryChargingPower | sigenergy2mqtt/sigen_0_inverter_1_battery_charging_power/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_charging_power/state | ChargeDischargePower &gt; 0|||
| InverterBatteryDischargingPower | sigenergy2mqtt/sigen_0_inverter_1_battery_discharging_power/state <br/> homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_discharging_power/state | ChargeDischargePower &lt; 0 &times; -1|||

#### PV String
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv1_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_voltage/state | Modbus Register 31027 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVStringPower | sigenergy2mqtt/sigen_0_inverter_1_pv1_power/state <br/> homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_power/state | PVVoltageSensor &times; PVCurrentSensor|||
| PVStringLifetimeEnergy | sigenergy2mqtt/sigen_0_inverter_1_pv1_lifetime_energy/state <br/> homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_lifetime_energy/state | Riemann &sum; of PVStringPower|||
| PVStringDailyEnergy | sigenergy2mqtt/sigen_0_inverter_1_pv1_daily_energy/state <br/> homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_daily_energy/state | PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight|||
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv1_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_current/state | Modbus Register 31028 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv2_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_voltage/state | Modbus Register 31029 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv2_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_current/state | Modbus Register 31030 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv3_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_voltage/state | Modbus Register 31031 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv3_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_current/state | Modbus Register 31032 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv4_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_voltage/state | Modbus Register 31033 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv4_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_current/state | Modbus Register 31034 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv5_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_voltage/state | Modbus Register 31042 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv5_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_current/state | Modbus Register 31043 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv6_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_voltage/state | Modbus Register 31044 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv6_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_current/state | Modbus Register 31045 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv7_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_voltage/state | Modbus Register 31046 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv7_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_current/state | Modbus Register 31047 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv8_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_voltage/state | Modbus Register 31048 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv8_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_current/state | Modbus Register 31049 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv9_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_voltage/state | Modbus Register 31050 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv9_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_current/state | Modbus Register 31051 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv10_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_voltage/state | Modbus Register 31052 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv10_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_current/state | Modbus Register 31053 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv11_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_voltage/state | Modbus Register 31054 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv11_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_current/state | Modbus Register 31055 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv12_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_voltage/state | Modbus Register 31056 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv12_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_current/state | Modbus Register 31057 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv13_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_voltage/state | Modbus Register 31058 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv13_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_current/state | Modbus Register 31059 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv14_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_voltage/state | Modbus Register 31060 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv14_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_current/state | Modbus Register 31061 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv15_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_voltage/state | Modbus Register 31062 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv15_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_current/state | Modbus Register 31063 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVVoltageSensor | sigenergy2mqtt/sigen_0_inverter_1_pv16_voltage/state <br/> homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_voltage/state | Modbus Register 31064 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |
| PVCurrentSensor | sigenergy2mqtt/sigen_0_inverter_1_pv16_current/state <br/> homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_current/state | Modbus Register 31065 | 10 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |

### AC Charger
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| ACChargerRunningState | sigenergy2mqtt/sigen_0_ac_charger_3_running_state/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_running_state/state | Modbus Register 32000 | 10 ||
| ACChargerTotalEnergyConsumed | sigenergy2mqtt/sigen_0_ac_charger_3_total_energy_consumed/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_total_energy_consumed/state | Modbus Register 32001 | 10 ||
| ACChargerChargingPower | sigenergy2mqtt/sigen_0_ac_charger_3_rated_charging_power/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_rated_charging_power/state | Modbus Register 32003 | 10 ||
| ACChargerRatedPower | sigenergy2mqtt/sigen_0_ac_charger_3_rated_power/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_rated_power/state | Modbus Register 32005 | 600 ||
| ACChargerInputBreaker | sigenergy2mqtt/sigen_0_ac_charger_3_input_breaker/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_input_breaker/state | Modbus Register 32010 | 600 ||
| ACChargerRatedVoltage | sigenergy2mqtt/sigen_0_ac_charger_3_rated_voltage/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_rated_voltage/state | Modbus Register 32009 | 600 ||
| ACChargerRatedCurrent | sigenergy2mqtt/sigen_0_ac_charger_3_rated_current/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_rated_current/state | Modbus Register 32007 | 600 ||
| ACChargerAlarms | sigenergy2mqtt/sigen_0_ac_charger_3_alarm/state <br/> homeassistant/sensor/sigen_0_003_accharger/sigen_0_ac_charger_3_alarm/state | Modbus Registers 32012, 32013, and 32014| 10 ||
| ACChargerOutputCurrent | sigenergy2mqtt/sigen_0_ac_charger_3_output_current/state <br/> homeassistant/number/sigen_0_003_accharger/sigen_0_ac_charger_3_output_current/state | Modbus Register 42001 | 60 ||

### DC Charger
| Sensor Class | State Topic | Source | Interval | Applicable To |
|--------------|-------------|--------|----------|---------------|
| DCChargerOutputPower | sigenergy2mqtt/sigen_0_plant_dc_charger_output_power/state <br/> homeassistant/sensor/sigen_0_002_dccharger/sigen_0_plant_dc_charger_output_power/state | Modbus Register 31502 | 10 ||
| DCChargerCurrentChargingCapacity | sigenergy2mqtt/sigen_0_plant_dc_charger_current_charging_capacity/state <br/> homeassistant/sensor/sigen_0_002_dccharger/sigen_0_plant_dc_charger_current_charging_capacity/state | Modbus Register 31505 | 600 ||
| DCChargerCurrentChargingDuration | sigenergy2mqtt/sigen_0_plant_dc_charger_current_charging_duration/state <br/> homeassistant/sensor/sigen_0_002_dccharger/sigen_0_plant_dc_charger_current_charging_duration/state | Modbus Register 31507 | 600 ||
| VehicleBatteryVoltage | sigenergy2mqtt/sigen_0_plant_vehicle_battery_voltage/state <br/> homeassistant/sensor/sigen_0_002_dccharger/sigen_0_plant_vehicle_battery_voltage/state | Modbus Register 31500 | 10 ||
| VehicleChargingCurrent | sigenergy2mqtt/sigen_0_plant_vehicle_charging_current/state <br/> homeassistant/sensor/sigen_0_002_dccharger/sigen_0_plant_vehicle_charging_current/state | Modbus Register 31501 | 10 ||
| VehicleSoC | sigenergy2mqtt/sigen_0_plant_vehicle_soc/state <br/> homeassistant/sensor/sigen_0_002_dccharger/sigen_0_plant_vehicle_soc/state | Modbus Register 31504 | 60 ||
| InverterAlarm5 | sigenergy2mqtt/sigen_0_inverter_2_alarm_5/state <br/> homeassistant/sensor/sigen_0_002_dccharger/sigen_0_inverter_2_alarm_5/state | Modbus Register 30609 | 10 ||

## Subscribed Topics

### Plant
| Sensor Class | Command Topic | Target | Applicable To |
|--------------|---------------|--------|---------------|
| RemoteEMS | sigenergy2mqtt/sigen_0_plant_remote_ems/state <br/> homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_remote_ems/state | Modbus Register 40029 ||
| RemoteEMSControlMode | sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/state <br/> homeassistant/select/sigen_0_247_powerplant/sigen_0_plant_remote_ems_control_mode/state | Modbus Register 40031 ||
| ActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_fixed_adjustment_target_value/state | Modbus Register 40001 ||
| ReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40003 ||
| ActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_percentage_adjustment_target_value/state | Modbus Register 40005 ||
| QSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_q_s_adjustment_target_value/state | Modbus Register 40006 ||
| PowerFactorAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_power_factor_adjustment_target_value/state | Modbus Register 40007 ||
| PhaseAActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state | Modbus Register 40008 ||
| PhaseAReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40014 ||
| PhaseAActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state | Modbus Register 40020 ||
| PhaseAQSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state | Modbus Register 40023 ||
| PhaseBActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state | Modbus Register 40010 ||
| PhaseBReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40016 ||
| PhaseBActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state | Modbus Register 40021 ||
| PhaseBQSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state | Modbus Register 40024 ||
| IndependentPhasePowerControl | sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/state <br/> homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_independent_phase_power_control/state | Modbus Register 40030 ||
| PhaseCActivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state | Modbus Register 40012 ||
| PhaseCReactivePowerFixedAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state | Modbus Register 40018 ||
| PhaseCActivePowerPercentageAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state | Modbus Register 40022 ||
| PhaseCQSAdjustmentTargetValue | sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state | Modbus Register 40025 ||
| MaxChargingLimit | sigenergy2mqtt/sigen_0_plant_max_charging_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_charging_limit/state | Modbus Register 40032 ||
| MaxDischargingLimit | sigenergy2mqtt/sigen_0_plant_max_discharging_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_discharging_limit/state | Modbus Register 40034 ||
| PVMaxPowerLimit | sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pv_max_power_limit/state | Modbus Register 40036 ||
| GridMaxExportLimit | sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_export_limit/state | Modbus Register 40038 ||
| GridMaxImportLimit | sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_import_limit/state | Modbus Register 40040 ||
| PCSMaxExportLimit | sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_export_limit/state | Modbus Register 40042 ||
| PCSMaxImportLimit | sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/state <br/> homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_import_limit/state | Modbus Register 40044 ||
| PlantStatus | sigenergy2mqtt/sigen_0_plant_status/state <br/> homeassistant/button/sigen_0_247_powerplant/sigen_0_plant_status/state | Modbus Register 40000 ||

### Inverter
| Sensor Class | Command Topic | Target | Applicable To |
|--------------|---------------|--------|---------------|
| InverterRemoteEMSDispatch | sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/state <br/> homeassistant/switch/sigen_0_001_inverter/sigen_0_inverter_1_remote_ems_dispatch/state | Modbus Register 41500 | PV&nbsp;Inverter |
| InverterActivePowerFixedValueAdjustment | sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment/state | Modbus Register 41501 | PV&nbsp;Inverter |
| InverterReactivePowerFixedValueAdjustment | sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state | Modbus Register 41503 | PV&nbsp;Inverter |
| InverterActivePowerPercentageAdjustment | sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment/state | Modbus Register 41505 | PV&nbsp;Inverter |
| InverterReactivePowerQSAdjustment | sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_q_s_adjustment/state | Modbus Register 41506 | PV&nbsp;Inverter |
| InverterPowerFactorAdjustment | sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/state <br/> homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment/state | Modbus Register 41507 | PV&nbsp;Inverter |
| InverterStatus | sigenergy2mqtt/sigen_0_inverter_1_status/state <br/> homeassistant/button/sigen_0_001_inverter/sigen_0_inverter_1_status/state | Modbus Register 40500 | Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter |

### AC Charger
| Sensor Class | Command Topic | Target | Applicable To |
|--------------|---------------|--------|---------------|
| ACChargerOutputCurrent | sigenergy2mqtt/sigen_0_ac_charger_3_output_current/state <br/> homeassistant/number/sigen_0_003_accharger/sigen_0_ac_charger_3_output_current/state | Modbus Register 42001 ||
| ACChargerStatus | sigenergy2mqtt/sigen_0_ac_charger_3_status/state <br/> homeassistant/button/sigen_0_003_accharger/sigen_0_ac_charger_3_status/state | Modbus Register 42000 ||

### DC Charger
| Sensor Class | Command Topic | Target | Applicable To |
|--------------|---------------|--------|---------------|
| DCChargerStatus | sigenergy2mqtt/sigen_0_dc_charger_2_status/state <br/> homeassistant/button/sigen_0_002_dccharger/sigen_0_dc_charger_2_status/state | Modbus Register 41000 ||
