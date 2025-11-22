# Home Assistant Sensors

The following is a list of the Modbus sensors published by the <a href='https://github.com/TypQxQ/Sigenergy-Local-Modbus'>TypQxQ Sigenergy-Local-Modbus</a> HACS integration,
and the corresponding sensor in `sigenergy2mqtt`. You can click on the `sigenergy2mqtt` sensor for more information.


#### Naming Convention for Sensors in `sigenergy2mqtt`


- Sensor names begin with a prefix. The default is `sigen`, but this may be changed via configuration.
- _ separator
- The index of the Modbus host from the configuration file (or auto-discovery), starting from 0.
- _ separator
##### Plant Sensors


- The sensor description.
  - Plant sensors have no device type or device ID, but the description _may_ be prefixed with `plant_` for clarity.
  - The description for Smart Load sensors will be prefixed by `smart_load_` (not `plant_`).
  - The description for Statistics Interface sensors will be prefixed by `si_` (not `plant_`).
##### Device Sensors


- The device type (inverter, ac_charger, or dc_charger).
- _ separator
- The Modbus device ID. Normally 1 for the Inverter and DC Charger and 2 for an AC Charger, but depends on how the installer configured the Modbus interface.
- _ separator
- The sensor description.

| Sigenergy-Local-Modbus | `sigenergy2mqtt` |
|------------------------|------------------|
| sigen_ac_charger_alarm1 | <a href='./TOPICS.md#sigen_0_ac_charger_2_alarm'>sigen_0_ac_charger_2_alarm (Combined Alarm)</a><br><a href='./TOPICS.md#sigen_0_002_32012'>sigen_0_ac_charger_2_alarm_1</a><br> |
| sigen_ac_charger_alarm2 | <a href='./TOPICS.md#sigen_0_002_32013'>sigen_0_ac_charger_2_alarm_2</a><br> |
| sigen_ac_charger_alarm3 | <a href='./TOPICS.md#sigen_0_002_32014'>sigen_0_ac_charger_2_alarm_3</a><br> |
| sigen_ac_charger_charging_power | <a href='./TOPICS.md#sigen_0_002_32003'>sigen_0_ac_charger_2_rated_charging_power</a><br> |
| sigen_ac_charger_input_breaker_rated_current | <a href='./TOPICS.md#sigen_0_002_32010'>sigen_0_ac_charger_2_input_breaker</a><br> |
| sigen_ac_charger_output_current | <a href='./TOPICS.md#sigen_0_002_42001'>sigen_0_ac_charger_2_output_current</a><br> |
| sigen_ac_charger_rated_current | <a href='./TOPICS.md#sigen_0_002_32007'>sigen_0_ac_charger_2_rated_current</a><br> |
| sigen_ac_charger_rated_power | <a href='./TOPICS.md#sigen_0_002_32005'>sigen_0_ac_charger_2_rated_power</a><br> |
| sigen_ac_charger_rated_voltage | <a href='./TOPICS.md#sigen_0_002_32009'>sigen_0_ac_charger_2_rated_voltage</a><br> |
| sigen_ac_charger_start_stop | <a href='./TOPICS.md#sigen_0_002_42000'>sigen_0_ac_charger_2</a><br> |
| sigen_ac_charger_system_state | <a href='./TOPICS.md#sigen_0_002_32000'>sigen_0_ac_charger_2_running_state</a><br> |
| sigen_ac_charger_total_energy_consumed | <a href='./TOPICS.md#sigen_0_002_32001'>sigen_0_ac_charger_2_total_energy_consumed</a><br> |
| sigen_dc_charger_charging_current | <a href='./TOPICS.md#sigen_0_001_31501'>sigen_0_plant_vehicle_charging_current</a><br> |
| sigen_dc_charger_current_charging_capacity | <a href='./TOPICS.md#sigen_0_001_31505'>sigen_0_plant_dc_charger_current_charging_capacity</a><br> |
| sigen_dc_charger_current_charging_duration | <a href='./TOPICS.md#sigen_0_001_31507'>sigen_0_plant_dc_charger_current_charging_duration</a><br> |
| sigen_dc_charger_output_power | <a href='./TOPICS.md#sigen_0_001_31502'>sigen_0_plant_dc_charger_output_power</a><br> |
| sigen_dc_charger_start_stop | <a href='./TOPICS.md#sigen_0_001_41000'>sigen_0_dc_charger_1</a><br> |
| sigen_dc_charger_vehicle_battery_voltage | <a href='./TOPICS.md#sigen_0_001_31500'>sigen_0_plant_vehicle_battery_voltage</a><br> |
| sigen_dc_charger_vehicle_soc | <a href='./TOPICS.md#sigen_0_001_31504'>sigen_0_plant_vehicle_soc</a><br> |
| sigen_inverter_ab_line_voltage | <a href='./TOPICS.md#sigen_0_001_31005'>sigen_0_inverter_1_a_b_line_voltage</a><br> |
| sigen_inverter_accumulated_pv_energy | <a href='./TOPICS.md#sigen_0_inverter_1_lifetime_pv_energy'>sigen_0_inverter_1_lifetime_pv_energy</a><br> |
| sigen_inverter_active_power | <a href='./TOPICS.md#sigen_0_001_30587'>sigen_0_inverter_1_active_power</a><br> |
| sigen_inverter_active_power_fixed_adjustment | <a href='./TOPICS.md#sigen_0_001_41501'>sigen_0_inverter_1_active_power_fixed_value_adjustment</a><br> |
| sigen_inverter_active_power_fixed_value_adjustment_feedback | <a href='./TOPICS.md#sigen_0_001_30613'>sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback</a><br> |
| sigen_inverter_active_power_percentage_adjustment | <a href='./TOPICS.md#sigen_0_001_41505'>sigen_0_inverter_1_active_power_percentage_adjustment</a><br> |
| sigen_inverter_active_power_percentage_adjustment_feedback | <a href='./TOPICS.md#sigen_0_001_30617'>sigen_0_inverter_1_active_power_percentage_adjustment_feedback</a><br> |
| sigen_inverter_alarm1 | <a href='./TOPICS.md#sigen_0_inverter_1_pcs_alarm'>sigen_0_inverter_1_pcs_alarm (Combined Alarm)</a><br><a href='./TOPICS.md#sigen_0_001_30605'>sigen_0_inverter_1_alarm_1</a><br> |
| sigen_inverter_alarm2 | <a href='./TOPICS.md#sigen_0_001_30606'>sigen_0_inverter_1_alarm_2</a><br> |
| sigen_inverter_alarm3 | <a href='./TOPICS.md#sigen_0_001_30607'>sigen_0_inverter_1_alarm_3</a><br> |
| sigen_inverter_alarm4 | <a href='./TOPICS.md#sigen_0_001_30608'>sigen_0_inverter_1_alarm_4</a><br> |
| sigen_inverter_alarm5 | <a href='./TOPICS.md#sigen_0_001_30609'>sigen_0_inverter_1_alarm_5</a><br> |
| sigen_inverter_bc_line_voltage | <a href='./TOPICS.md#sigen_0_001_31007'>sigen_0_inverter_1_b_c_line_voltage</a><br> |
| sigen_inverter_ca_line_voltage | <a href='./TOPICS.md#sigen_0_001_31009'>sigen_0_inverter_1_c_a_line_voltage</a><br> |
| sigen_inverter_daily_pv_energy | <a href='./TOPICS.md#sigen_0_inverter_1_daily_pv_energy'>sigen_0_inverter_1_daily_pv_energy</a><br> |
| sigen_inverter_ess_accumulated_charge_energy | <a href='./TOPICS.md#sigen_0_001_30568'>sigen_0_inverter_1_accumulated_charge_energy</a><br> |
| sigen_inverter_ess_accumulated_discharge_energy | <a href='./TOPICS.md#sigen_0_001_30574'>sigen_0_inverter_1_accumulated_discharge_energy</a><br> |
| sigen_inverter_ess_available_battery_charge_energy | <a href='./TOPICS.md#sigen_0_001_30595'>sigen_0_inverter_1_available_battery_charge_energy</a><br> |
| sigen_inverter_ess_available_battery_discharge_energy | <a href='./TOPICS.md#sigen_0_001_30597'>sigen_0_inverter_1_available_battery_discharge_energy</a><br> |
| sigen_inverter_ess_average_cell_temperature | <a href='./TOPICS.md#sigen_0_001_30603'>sigen_0_inverter_1_average_cell_temperature</a><br> |
| sigen_inverter_ess_average_cell_voltage | <a href='./TOPICS.md#sigen_0_001_30604'>sigen_0_inverter_1_average_cell_voltage</a><br> |
| sigen_inverter_ess_battery_soc | <a href='./TOPICS.md#sigen_0_001_30601'>sigen_0_inverter_1_battery_soc</a><br> |
| sigen_inverter_ess_battery_soh | <a href='./TOPICS.md#sigen_0_001_30602'>sigen_0_inverter_1_battery_soh</a><br> |
| sigen_inverter_ess_charge_discharge_power | <a href='./TOPICS.md#sigen_0_001_30599'>sigen_0_inverter_1_charge_discharge_power</a><br> |
| sigen_inverter_ess_daily_charge_energy | <a href='./TOPICS.md#sigen_0_001_30566'>sigen_0_inverter_1_daily_charge_energy</a><br> |
| sigen_inverter_ess_daily_discharge_energy | <a href='./TOPICS.md#sigen_0_001_30572'>sigen_0_inverter_1_daily_discharge_energy</a><br> |
| sigen_inverter_ess_max_battery_charge_power | <a href='./TOPICS.md#sigen_0_001_30591'>sigen_0_inverter_1_max_battery_charge_power</a><br> |
| sigen_inverter_ess_max_battery_discharge_power | <a href='./TOPICS.md#sigen_0_001_30593'>sigen_0_inverter_1_max_battery_discharge_power</a><br> |
| sigen_inverter_ess_maximum_battery_cell_voltage | <a href='./TOPICS.md#sigen_0_001_30622'>sigen_0_inverter_1_max_cell_voltage</a><br> |
| sigen_inverter_ess_maximum_battery_temperature | <a href='./TOPICS.md#sigen_0_001_30620'>sigen_0_inverter_1_max_battery_temperature</a><br> |
| sigen_inverter_ess_minimum_battery_cell_voltage | <a href='./TOPICS.md#sigen_0_001_30623'>sigen_0_inverter_1_min_cell_voltage</a><br> |
| sigen_inverter_ess_minimum_battery_temperature | <a href='./TOPICS.md#sigen_0_001_30621'>sigen_0_inverter_1_min_battery_temperature</a><br> |
| sigen_inverter_ess_rated_charge_power | <a href='./TOPICS.md#sigen_0_001_30550'>sigen_0_inverter_1_rated_charging_power</a><br> |
| sigen_inverter_ess_rated_discharge_power | <a href='./TOPICS.md#sigen_0_001_30552'>sigen_0_inverter_1_rated_discharging_power</a><br> |
| sigen_inverter_grid_frequency | <a href='./TOPICS.md#sigen_0_001_31002'>sigen_0_inverter_1_grid_frequency</a><br> |
| sigen_inverter_insulation_resistance | <a href='./TOPICS.md#sigen_0_001_31037'>sigen_0_inverter_1_insulation_resistance</a><br> |
| sigen_inverter_machine_firmware_version | <a href='./TOPICS.md#sigen_0_001_30525'>sigen_0_inverter_1_firmware_version</a><br> |
| sigen_inverter_max_absorption_power | <a href='./TOPICS.md#sigen_0_001_30546'>sigen_0_inverter_1_max_absorption_power</a><br> |
| sigen_inverter_max_active_power | <a href='./TOPICS.md#sigen_0_001_30544'>sigen_0_inverter_1_max_active_power</a><br> |
| sigen_inverter_max_active_power_adjustment_value | <a href='./TOPICS.md#sigen_0_001_30579'>sigen_0_inverter_1_max_active_power_adjustment</a><br> |
| sigen_inverter_max_apparent_power | <a href='./TOPICS.md#sigen_0_001_30542'>sigen_0_inverter_1_max_rated_apparent_power</a><br> |
| sigen_inverter_max_reactive_power_adjustment_value_absorbed | <a href='./TOPICS.md#sigen_0_001_30585'>sigen_0_inverter_1_min_reactive_power_adjustment</a><br> |
| sigen_inverter_max_reactive_power_adjustment_value_fed | <a href='./TOPICS.md#sigen_0_001_30583'>sigen_0_inverter_1_max_reactive_power_adjustment</a><br> |
| sigen_inverter_min_active_power_adjustment_value | <a href='./TOPICS.md#sigen_0_001_30581'>sigen_0_inverter_1_min_active_power_adjustment</a><br> |
| sigen_inverter_model_type | <a href='./TOPICS.md#sigen_0_001_30500'>sigen_0_inverter_1_model</a><br> |
| sigen_inverter_mppt_count | <a href='./TOPICS.md#sigen_0_001_31026'>sigen_0_inverter_1_mptt_count</a><br> |
| sigen_inverter_output_type | <a href='./TOPICS.md#sigen_0_001_31004'>sigen_0_inverter_1_output_type</a><br> |
| sigen_inverter_pack_count | <a href='./TOPICS.md#sigen_0_001_31024'>sigen_0_inverter_1_pack_bcu_count</a><br> |
| sigen_inverter_pcs_internal_temperature | <a href='./TOPICS.md#sigen_0_001_31003'>sigen_0_inverter_1_temperature</a><br> |
| sigen_inverter_phase_a_current | <a href='./TOPICS.md#sigen_0_001_31017'>sigen_0_inverter_1_phase_a_current</a><br> |
| sigen_inverter_phase_a_voltage | <a href='./TOPICS.md#sigen_0_001_31011'>sigen_0_inverter_1_phase_a_voltage</a><br> |
| sigen_inverter_phase_b_current | <a href='./TOPICS.md#sigen_0_001_31019'>sigen_0_inverter_1_phase_b_current</a><br> |
| sigen_inverter_phase_b_voltage | <a href='./TOPICS.md#sigen_0_001_31013'>sigen_0_inverter_1_phase_b_voltage</a><br> |
| sigen_inverter_phase_c_current | <a href='./TOPICS.md#sigen_0_001_31021'>sigen_0_inverter_1_phase_c_current</a><br> |
| sigen_inverter_phase_c_voltage | <a href='./TOPICS.md#sigen_0_001_31015'>sigen_0_inverter_1_phase_c_voltage</a><br> |
| sigen_inverter_power_factor | <a href='./TOPICS.md#sigen_0_001_31023'>sigen_0_inverter_1_power_factor</a><br> |
| sigen_inverter_power_factor_adjustment | <a href='./TOPICS.md#sigen_0_001_41507'>sigen_0_inverter_1_power_factor_adjustment</a><br> |
| sigen_inverter_power_factor_adjustment_feedback | <a href='./TOPICS.md#sigen_0_001_30619'>sigen_0_inverter_1_power_factor_adjustment_feedback</a><br> |
| sigen_inverter_pv10_current | <a href='./TOPICS.md#sigen_0_001_31053'>sigen_0_inverter_1_pv10_current</a><br> |
| sigen_inverter_pv10_voltage | <a href='./TOPICS.md#sigen_0_001_31052'>sigen_0_inverter_1_pv10_voltage</a><br> |
| sigen_inverter_pv11_current | <a href='./TOPICS.md#sigen_0_001_31055'>sigen_0_inverter_1_pv11_current</a><br> |
| sigen_inverter_pv11_voltage | <a href='./TOPICS.md#sigen_0_001_31054'>sigen_0_inverter_1_pv11_voltage</a><br> |
| sigen_inverter_pv12_current | <a href='./TOPICS.md#sigen_0_001_31057'>sigen_0_inverter_1_pv12_current</a><br> |
| sigen_inverter_pv12_voltage | <a href='./TOPICS.md#sigen_0_001_31056'>sigen_0_inverter_1_pv12_voltage</a><br> |
| sigen_inverter_pv13_current | <a href='./TOPICS.md#sigen_0_001_31059'>sigen_0_inverter_1_pv13_current</a><br> |
| sigen_inverter_pv13_voltage | <a href='./TOPICS.md#sigen_0_001_31058'>sigen_0_inverter_1_pv13_voltage</a><br> |
| sigen_inverter_pv14_current | <a href='./TOPICS.md#sigen_0_001_31061'>sigen_0_inverter_1_pv14_current</a><br> |
| sigen_inverter_pv14_voltage | <a href='./TOPICS.md#sigen_0_001_31060'>sigen_0_inverter_1_pv14_voltage</a><br> |
| sigen_inverter_pv15_current | <a href='./TOPICS.md#sigen_0_001_31063'>sigen_0_inverter_1_pv15_current</a><br> |
| sigen_inverter_pv15_voltage | <a href='./TOPICS.md#sigen_0_001_31062'>sigen_0_inverter_1_pv15_voltage</a><br> |
| sigen_inverter_pv16_current | <a href='./TOPICS.md#sigen_0_001_31065'>sigen_0_inverter_1_pv16_current</a><br> |
| sigen_inverter_pv16_voltage | <a href='./TOPICS.md#sigen_0_001_31064'>sigen_0_inverter_1_pv16_voltage</a><br> |
| sigen_inverter_pv1_current | <a href='./TOPICS.md#sigen_0_001_31028'>sigen_0_inverter_1_pv1_current</a><br> |
| sigen_inverter_pv1_voltage | <a href='./TOPICS.md#sigen_0_001_31027'>sigen_0_inverter_1_pv1_voltage</a><br> |
| sigen_inverter_pv2_current | <a href='./TOPICS.md#sigen_0_001_31030'>sigen_0_inverter_1_pv2_current</a><br> |
| sigen_inverter_pv2_voltage | <a href='./TOPICS.md#sigen_0_001_31029'>sigen_0_inverter_1_pv2_voltage</a><br> |
| sigen_inverter_pv3_current | <a href='./TOPICS.md#sigen_0_001_31032'>sigen_0_inverter_1_pv3_current</a><br> |
| sigen_inverter_pv3_voltage | <a href='./TOPICS.md#sigen_0_001_31031'>sigen_0_inverter_1_pv3_voltage</a><br> |
| sigen_inverter_pv4_current | <a href='./TOPICS.md#sigen_0_001_31034'>sigen_0_inverter_1_pv4_current</a><br> |
| sigen_inverter_pv4_voltage | <a href='./TOPICS.md#sigen_0_001_31033'>sigen_0_inverter_1_pv4_voltage</a><br> |
| sigen_inverter_pv5_current | <a href='./TOPICS.md#sigen_0_001_31043'>sigen_0_inverter_1_pv5_current</a><br> |
| sigen_inverter_pv5_voltage | <a href='./TOPICS.md#sigen_0_001_31042'>sigen_0_inverter_1_pv5_voltage</a><br> |
| sigen_inverter_pv6_current | <a href='./TOPICS.md#sigen_0_001_31045'>sigen_0_inverter_1_pv6_current</a><br> |
| sigen_inverter_pv6_voltage | <a href='./TOPICS.md#sigen_0_001_31044'>sigen_0_inverter_1_pv6_voltage</a><br> |
| sigen_inverter_pv7_current | <a href='./TOPICS.md#sigen_0_001_31047'>sigen_0_inverter_1_pv7_current</a><br> |
| sigen_inverter_pv7_voltage | <a href='./TOPICS.md#sigen_0_001_31046'>sigen_0_inverter_1_pv7_voltage</a><br> |
| sigen_inverter_pv8_current | <a href='./TOPICS.md#sigen_0_001_31049'>sigen_0_inverter_1_pv8_current</a><br> |
| sigen_inverter_pv8_voltage | <a href='./TOPICS.md#sigen_0_001_31048'>sigen_0_inverter_1_pv8_voltage</a><br> |
| sigen_inverter_pv9_current | <a href='./TOPICS.md#sigen_0_001_31051'>sigen_0_inverter_1_pv9_current</a><br> |
| sigen_inverter_pv9_voltage | <a href='./TOPICS.md#sigen_0_001_31050'>sigen_0_inverter_1_pv9_voltage</a><br> |
| sigen_inverter_pv_power | <a href='./TOPICS.md#sigen_0_001_31035'>sigen_0_inverter_1_pv_power</a><br> |
| sigen_inverter_pv_string_count | <a href='./TOPICS.md#sigen_0_001_31025'>sigen_0_inverter_1_pv_string_count</a><br> |
| sigen_inverter_rated_active_power | <a href='./TOPICS.md#sigen_0_001_30540'>sigen_0_inverter_1_rated_active_power</a><br> |
| sigen_inverter_rated_battery_capacity | <a href='./TOPICS.md#sigen_0_001_30548'>sigen_0_inverter_1_rated_battery_capacity</a><br> |
| sigen_inverter_rated_grid_frequency | <a href='./TOPICS.md#sigen_0_001_31001'>sigen_0_inverter_1_rated_grid_frequency</a><br> |
| sigen_inverter_rated_grid_voltage | <a href='./TOPICS.md#sigen_0_001_31000'>sigen_0_inverter_1_rated_grid_voltage</a><br> |
| sigen_inverter_reactive_power | <a href='./TOPICS.md#sigen_0_001_30589'>sigen_0_inverter_1_reactive_power</a><br> |
| sigen_inverter_reactive_power_fixed_adjustment | <a href='./TOPICS.md#sigen_0_001_41503'>sigen_0_inverter_1_reactive_power_fixed_value_adjustment</a><br> |
| sigen_inverter_reactive_power_fixed_value_adjustment_feedback | <a href='./TOPICS.md#sigen_0_001_30615'>sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback</a><br> |
| sigen_inverter_reactive_power_qs_adjustment | <a href='./TOPICS.md#sigen_0_001_41506'>sigen_0_inverter_1_reactive_power_q_s_adjustment</a><br> |
| sigen_inverter_reactive_power_qs_adjustment_feedback | <a href='./TOPICS.md#sigen_0_001_30618'>sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback</a><br> |
| sigen_inverter_remote_ems_dispatch_enable | <a href='./TOPICS.md#sigen_0_001_41500'>sigen_0_inverter_1_remote_ems_dispatch</a><br> |
| sigen_inverter_running_state | <a href='./TOPICS.md#sigen_0_001_30578'>sigen_0_inverter_1_running_state</a><br> |
| sigen_inverter_serial_number | <a href='./TOPICS.md#sigen_0_001_30515'>sigen_0_inverter_1_serial_number</a><br> |
| sigen_inverter_shutdown_time | <a href='./TOPICS.md#sigen_0_001_31040'>sigen_0_inverter_1_shutdown_time</a><br> |
| sigen_inverter_start_stop | <a href='./TOPICS.md#sigen_0_001_40500'>sigen_0_inverter_1_status</a><br> |
| sigen_inverter_startup_time | <a href='./TOPICS.md#sigen_0_001_31038'>sigen_0_inverter_1_startup_time</a><br> |
| sigen_plant_accumulated_battery_charge_energy | <a href='./TOPICS.md#sigen_0_accumulated_charge_energy'>sigen_0_accumulated_charge_energy</a><br> |
| sigen_plant_accumulated_battery_discharge_energy | <a href='./TOPICS.md#sigen_0_accumulated_discharge_energy'>sigen_0_accumulated_discharge_energy</a><br> |
| sigen_plant_accumulated_consumed_energy | <a href='./TOPICS.md#sigen_0_lifetime_consumed_energy'>sigen_0_lifetime_consumed_energy</a><br> |
| sigen_plant_accumulated_grid_export_energy | <a href='./TOPICS.md#sigen_0_grid_sensor_lifetime_export_energy'>sigen_0_grid_sensor_lifetime_export_energy</a><br> |
| sigen_plant_accumulated_grid_import_energy | <a href='./TOPICS.md#sigen_0_grid_sensor_lifetime_import_energy'>sigen_0_grid_sensor_lifetime_import_energy</a><br> |
| sigen_plant_accumulated_pv_energy | <a href='./TOPICS.md#sigen_0_247_30088'>sigen_0_plant_lifetime_pv_energy</a><br> |
| sigen_plant_active_power | <a href='./TOPICS.md#sigen_0_247_30031'>sigen_0_plant_active_power</a><br> |
| sigen_plant_active_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40001'>sigen_0_plant_active_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_active_power_percentage_target | <a href='./TOPICS.md#sigen_0_247_40005'>sigen_0_plant_active_power_percentage_adjustment_target_value</a><br> |
| sigen_plant_available_max_active_power | <a href='./TOPICS.md#sigen_0_247_30039'>sigen_0_plant_available_max_active_power</a><br> |
| sigen_plant_available_max_reactive_power | <a href='./TOPICS.md#sigen_0_247_30043'>sigen_0_plant_available_max_reactive_power</a><br> |
| sigen_plant_available_min_active_power | <a href='./TOPICS.md#sigen_0_247_30041'>sigen_0_plant_available_min_active_power</a><br> |
| sigen_plant_available_min_reactive_power | <a href='./TOPICS.md#sigen_0_247_30045'>sigen_0_plant_available_min_reactive_power</a><br> |
| sigen_plant_backup_soc | <a href='./TOPICS.md#sigen_0_247_40046'>sigen_0_plant_ess_backup_soc</a><br> |
| sigen_plant_charge_cut_off_soc | <a href='./TOPICS.md#sigen_0_247_40047'>sigen_0_plant_ess_charge_cut_off_soc</a><br> |
| sigen_plant_daily_consumed_energy | <a href='./TOPICS.md#sigen_0_daily_consumed_energy'>sigen_0_daily_consumed_energy</a><br> |
| sigen_plant_discharge_cut_off_soc | <a href='./TOPICS.md#sigen_0_247_40048'>sigen_0_plant_ess_discharge_cut_off_soc</a><br> |
| sigen_plant_ems_work_mode | <a href='./TOPICS.md#sigen_0_247_30003'>sigen_0_plant_ems_work_mode</a><br> |
| sigen_plant_ess_available_max_charging_capacity | <a href='./TOPICS.md#sigen_0_247_30064'>sigen_0_plant_available_max_charging_capacity</a><br> |
| sigen_plant_ess_available_max_charging_power | <a href='./TOPICS.md#sigen_0_247_30047'>sigen_0_plant_available_max_charging_power</a><br> |
| sigen_plant_ess_available_max_discharging_capacity | <a href='./TOPICS.md#sigen_0_247_30066'>sigen_0_plant_available_max_discharging_capacity</a><br> |
| sigen_plant_ess_available_max_discharging_power | <a href='./TOPICS.md#sigen_0_247_30049'>sigen_0_plant_available_max_discharging_power</a><br> |
| sigen_plant_ess_charge_cut_off_soc | <a href='./TOPICS.md#sigen_0_247_30085'>sigen_0_plant_charge_cut_off_soc</a><br> |
| sigen_plant_ess_discharge_cut_off_soc | <a href='./TOPICS.md#sigen_0_247_30086'>sigen_0_plant_discharge_cut_off_soc</a><br> |
| sigen_plant_ess_max_charging_limit | <a href='./TOPICS.md#sigen_0_247_40032'>sigen_0_plant_max_charging_limit</a><br> |
| sigen_plant_ess_max_discharging_limit | <a href='./TOPICS.md#sigen_0_247_40034'>sigen_0_plant_max_discharging_limit</a><br> |
| sigen_plant_ess_power | <a href='./TOPICS.md#sigen_0_247_30037'>sigen_0_plant_battery_power</a><br> |
| sigen_plant_ess_rated_charging_power | <a href='./TOPICS.md#sigen_0_247_30068'>sigen_0_plant_rated_charging_power</a><br> |
| sigen_plant_ess_rated_discharging_power | <a href='./TOPICS.md#sigen_0_247_30070'>sigen_0_plant_rated_discharging_power</a><br> |
| sigen_plant_ess_rated_energy_capacity | <a href='./TOPICS.md#sigen_0_247_30083'>sigen_0_plant_rated_energy_capacity</a><br> |
| sigen_plant_ess_soc | <a href='./TOPICS.md#sigen_0_247_30014'>sigen_0_plant_battery_soc</a><br> |
| sigen_plant_ess_soh | <a href='./TOPICS.md#sigen_0_247_30087'>sigen_0_plant_battery_soh</a><br> |
| sigen_plant_general_alarm1 | <a href='./TOPICS.md#sigen_0_general_pcs_alarm'>sigen_0_general_pcs_alarm (Combined Alarm)</a><br><a href='./TOPICS.md#sigen_0_247_30027'>sigen_0_general_alarm_1</a><br> |
| sigen_plant_general_alarm2 | <a href='./TOPICS.md#sigen_0_247_30028'>sigen_0_general_alarm_2</a><br> |
| sigen_plant_general_alarm3 | <a href='./TOPICS.md#sigen_0_247_30029'>sigen_0_general_alarm_3</a><br> |
| sigen_plant_general_alarm4 | <a href='./TOPICS.md#sigen_0_247_30030'>sigen_0_general_alarm_4</a><br> |
| sigen_plant_general_alarm5 | <a href='./TOPICS.md#sigen_0_247_30072'>sigen_0_general_alarm_5</a><br> |
| sigen_plant_grid_maximum_import_limitation | <a href='./TOPICS.md#sigen_0_247_40040'>sigen_0_plant_grid_max_import_limit</a><br> |
| sigen_plant_grid_point_maximum_export_limitation | <a href='./TOPICS.md#sigen_0_247_40038'>sigen_0_plant_grid_max_export_limit</a><br> |
| sigen_plant_grid_sensor_active_power | <a href='./TOPICS.md#sigen_0_247_30005'>sigen_0_plant_grid_sensor_active_power</a><br> |
| sigen_plant_grid_sensor_phase_a_active_power | <a href='./TOPICS.md#sigen_0_247_30052'>sigen_0_plant_grid_phase_a_active_power</a><br> |
| sigen_plant_grid_sensor_phase_a_reactive_power | <a href='./TOPICS.md#sigen_0_247_30058'>sigen_0_plant_grid_phase_a_reactive_power</a><br> |
| sigen_plant_grid_sensor_phase_b_active_power | <a href='./TOPICS.md#sigen_0_247_30054'>sigen_0_plant_grid_phase_b_active_power</a><br> |
| sigen_plant_grid_sensor_phase_b_reactive_power | <a href='./TOPICS.md#sigen_0_247_30060'>sigen_0_plant_grid_phase_b_reactive_power</a><br> |
| sigen_plant_grid_sensor_phase_c_active_power | <a href='./TOPICS.md#sigen_0_247_30056'>sigen_0_plant_grid_phase_c_active_power</a><br> |
| sigen_plant_grid_sensor_phase_c_reactive_power | <a href='./TOPICS.md#sigen_0_247_30062'>sigen_0_plant_grid_phase_c_reactive_power</a><br> |
| sigen_plant_grid_sensor_reactive_power | <a href='./TOPICS.md#sigen_0_247_30007'>sigen_0_plant_grid_sensor_reactive_power</a><br> |
| sigen_plant_grid_sensor_status | <a href='./TOPICS.md#sigen_0_247_30004'>sigen_0_plant_grid_sensor_status</a><br> |
| sigen_plant_independent_phase_power_control_enable | <a href='./TOPICS.md#sigen_0_247_40030'>sigen_0_plant_independent_phase_power_control</a><br> |
| sigen_plant_max_active_power | <a href='./TOPICS.md#sigen_0_247_30010'>sigen_0_plant_max_active_power</a><br> |
| sigen_plant_max_apparent_power | <a href='./TOPICS.md#sigen_0_247_30012'>sigen_0_plant_max_apparent_power</a><br> |
| sigen_plant_on_off_grid_status | <a href='./TOPICS.md#sigen_0_247_30009'>sigen_0_plant_grid_status</a><br> |
| sigen_plant_pcs_maximum_export_limitation | <a href='./TOPICS.md#sigen_0_247_40042'>sigen_0_plant_pcs_max_export_limit</a><br> |
| sigen_plant_pcs_maximum_import_limitation | <a href='./TOPICS.md#sigen_0_247_40044'>sigen_0_plant_pcs_max_import_limit</a><br> |
| sigen_plant_phase_a_active_power | <a href='./TOPICS.md#sigen_0_247_30015'>sigen_0_plant_phase_a_active_power</a><br> |
| sigen_plant_phase_a_active_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40008'>sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_a_active_power_percentage_target | <a href='./TOPICS.md#sigen_0_247_40020'>sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value</a><br> |
| sigen_plant_phase_a_qs_ratio_target | <a href='./TOPICS.md#sigen_0_247_40023'>sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_a_reactive_power | <a href='./TOPICS.md#sigen_0_247_30021'>sigen_0_plant_phase_a_reactive_power</a><br> |
| sigen_plant_phase_a_reactive_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40014'>sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_b_active_power | <a href='./TOPICS.md#sigen_0_247_30017'>sigen_0_plant_phase_b_active_power</a><br> |
| sigen_plant_phase_b_active_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40010'>sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_b_active_power_percentage_target | <a href='./TOPICS.md#sigen_0_247_40021'>sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value</a><br> |
| sigen_plant_phase_b_qs_ratio_target | <a href='./TOPICS.md#sigen_0_247_40024'>sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_b_reactive_power | <a href='./TOPICS.md#sigen_0_247_30023'>sigen_0_plant_phase_b_reactive_power</a><br> |
| sigen_plant_phase_b_reactive_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40016'>sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_c_active_power | <a href='./TOPICS.md#sigen_0_247_30019'>sigen_0_plant_phase_c_active_power</a><br> |
| sigen_plant_phase_c_active_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40012'>sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_c_active_power_percentage_target | <a href='./TOPICS.md#sigen_0_247_40022'>sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value</a><br> |
| sigen_plant_phase_c_qs_ratio_target | <a href='./TOPICS.md#sigen_0_247_40025'>sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value</a><br> |
| sigen_plant_phase_c_reactive_power | <a href='./TOPICS.md#sigen_0_247_30025'>sigen_0_plant_phase_c_reactive_power</a><br> |
| sigen_plant_phase_c_reactive_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40018'>sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_power_factor_target | <a href='./TOPICS.md#sigen_0_247_40007'>sigen_0_plant_power_factor_adjustment_target_value</a><br> |
| sigen_plant_pv_max_power_limit | <a href='./TOPICS.md#sigen_0_247_40036'>sigen_0_plant_pv_max_power_limit</a><br> |
| sigen_plant_qs_ratio_target | <a href='./TOPICS.md#sigen_0_247_40006'>sigen_0_plant_q_s_adjustment_target_value</a><br> |
| sigen_plant_reactive_power | <a href='./TOPICS.md#sigen_0_247_30033'>sigen_0_plant_reactive_power</a><br> |
| sigen_plant_reactive_power_fixed_target | <a href='./TOPICS.md#sigen_0_247_40003'>sigen_0_plant_reactive_power_fixed_adjustment_target_value</a><br> |
| sigen_plant_remote_ems_control_mode | <a href='./TOPICS.md#sigen_0_247_40031'>sigen_0_plant_remote_ems_control_mode</a><br> |
| sigen_plant_remote_ems_enable | <a href='./TOPICS.md#sigen_0_247_40029'>sigen_0_plant_remote_ems</a><br> |
| sigen_plant_running_state | <a href='./TOPICS.md#sigen_0_247_30051'>sigen_0_plant_running_state</a><br> |
| sigen_plant_sigen_photovoltaic_power | <a href='./TOPICS.md#sigen_0_247_30035'>sigen_0_plant_pv_power</a><br> |
| sigen_plant_smart_load_10_power | <a href='./TOPICS.md#sigen_0_247_30164'>sigen_0_smart_load_10_power</a><br> |
| sigen_plant_smart_load_10_total_consumption | <a href='./TOPICS.md#sigen_0_247_30116'>sigen_0_smart_load_10_total_consumption</a><br> |
| sigen_plant_smart_load_11_power | <a href='./TOPICS.md#sigen_0_247_30166'>sigen_0_smart_load_11_power</a><br> |
| sigen_plant_smart_load_11_total_consumption | <a href='./TOPICS.md#sigen_0_247_30118'>sigen_0_smart_load_11_total_consumption</a><br> |
| sigen_plant_smart_load_12_power | <a href='./TOPICS.md#sigen_0_247_30168'>sigen_0_smart_load_12_power</a><br> |
| sigen_plant_smart_load_12_total_consumption | <a href='./TOPICS.md#sigen_0_247_30120'>sigen_0_smart_load_12_total_consumption</a><br> |
| sigen_plant_smart_load_13_power | <a href='./TOPICS.md#sigen_0_247_30170'>sigen_0_smart_load_13_power</a><br> |
| sigen_plant_smart_load_13_total_consumption | <a href='./TOPICS.md#sigen_0_247_30122'>sigen_0_smart_load_13_total_consumption</a><br> |
| sigen_plant_smart_load_14_power | <a href='./TOPICS.md#sigen_0_247_30172'>sigen_0_smart_load_14_power</a><br> |
| sigen_plant_smart_load_14_total_consumption | <a href='./TOPICS.md#sigen_0_247_30124'>sigen_0_smart_load_14_total_consumption</a><br> |
| sigen_plant_smart_load_15_power | <a href='./TOPICS.md#sigen_0_247_30174'>sigen_0_smart_load_15_power</a><br> |
| sigen_plant_smart_load_15_total_consumption | <a href='./TOPICS.md#sigen_0_247_30126'>sigen_0_smart_load_15_total_consumption</a><br> |
| sigen_plant_smart_load_16_power | <a href='./TOPICS.md#sigen_0_247_30176'>sigen_0_smart_load_16_power</a><br> |
| sigen_plant_smart_load_16_total_consumption | <a href='./TOPICS.md#sigen_0_247_30128'>sigen_0_smart_load_16_total_consumption</a><br> |
| sigen_plant_smart_load_17_power | <a href='./TOPICS.md#sigen_0_247_30178'>sigen_0_smart_load_17_power</a><br> |
| sigen_plant_smart_load_17_total_consumption | <a href='./TOPICS.md#sigen_0_247_30130'>sigen_0_smart_load_17_total_consumption</a><br> |
| sigen_plant_smart_load_18_power | <a href='./TOPICS.md#sigen_0_247_30180'>sigen_0_smart_load_18_power</a><br> |
| sigen_plant_smart_load_18_total_consumption | <a href='./TOPICS.md#sigen_0_247_30132'>sigen_0_smart_load_18_total_consumption</a><br> |
| sigen_plant_smart_load_19_power | <a href='./TOPICS.md#sigen_0_247_30182'>sigen_0_smart_load_19_power</a><br> |
| sigen_plant_smart_load_19_total_consumption | <a href='./TOPICS.md#sigen_0_247_30134'>sigen_0_smart_load_19_total_consumption</a><br> |
| sigen_plant_smart_load_1_power | <a href='./TOPICS.md#sigen_0_247_30146'>sigen_0_smart_load_01_power</a><br> |
| sigen_plant_smart_load_1_total_consumption | <a href='./TOPICS.md#sigen_0_247_30098'>sigen_0_smart_load_01_total_consumption</a><br> |
| sigen_plant_smart_load_20_power | <a href='./TOPICS.md#sigen_0_247_30184'>sigen_0_smart_load_20_power</a><br> |
| sigen_plant_smart_load_20_total_consumption | <a href='./TOPICS.md#sigen_0_247_30136'>sigen_0_smart_load_20_total_consumption</a><br> |
| sigen_plant_smart_load_21_power | <a href='./TOPICS.md#sigen_0_247_30186'>sigen_0_smart_load_21_power</a><br> |
| sigen_plant_smart_load_21_total_consumption | <a href='./TOPICS.md#sigen_0_247_30138'>sigen_0_smart_load_21_total_consumption</a><br> |
| sigen_plant_smart_load_22_power | <a href='./TOPICS.md#sigen_0_247_30188'>sigen_0_smart_load_22_power</a><br> |
| sigen_plant_smart_load_22_total_consumption | <a href='./TOPICS.md#sigen_0_247_30140'>sigen_0_smart_load_22_total_consumption</a><br> |
| sigen_plant_smart_load_23_power | <a href='./TOPICS.md#sigen_0_247_30190'>sigen_0_smart_load_23_power</a><br> |
| sigen_plant_smart_load_23_total_consumption | <a href='./TOPICS.md#sigen_0_247_30142'>sigen_0_smart_load_23_total_consumption</a><br> |
| sigen_plant_smart_load_24_power | <a href='./TOPICS.md#sigen_0_247_30192'>sigen_0_smart_load_24_power</a><br> |
| sigen_plant_smart_load_24_total_consumption | <a href='./TOPICS.md#sigen_0_247_30144'>sigen_0_smart_load_24_total_consumption</a><br> |
| sigen_plant_smart_load_2_power | <a href='./TOPICS.md#sigen_0_247_30148'>sigen_0_smart_load_02_power</a><br> |
| sigen_plant_smart_load_2_total_consumption | <a href='./TOPICS.md#sigen_0_247_30100'>sigen_0_smart_load_02_total_consumption</a><br> |
| sigen_plant_smart_load_3_power | <a href='./TOPICS.md#sigen_0_247_30150'>sigen_0_smart_load_03_power</a><br> |
| sigen_plant_smart_load_3_total_consumption | <a href='./TOPICS.md#sigen_0_247_30102'>sigen_0_smart_load_03_total_consumption</a><br> |
| sigen_plant_smart_load_4_power | <a href='./TOPICS.md#sigen_0_247_30152'>sigen_0_smart_load_04_power</a><br> |
| sigen_plant_smart_load_4_total_consumption | <a href='./TOPICS.md#sigen_0_247_30104'>sigen_0_smart_load_04_total_consumption</a><br> |
| sigen_plant_smart_load_5_power | <a href='./TOPICS.md#sigen_0_247_30154'>sigen_0_smart_load_05_power</a><br> |
| sigen_plant_smart_load_5_total_consumption | <a href='./TOPICS.md#sigen_0_247_30106'>sigen_0_smart_load_05_total_consumption</a><br> |
| sigen_plant_smart_load_6_power | <a href='./TOPICS.md#sigen_0_247_30156'>sigen_0_smart_load_06_power</a><br> |
| sigen_plant_smart_load_6_total_consumption | <a href='./TOPICS.md#sigen_0_247_30108'>sigen_0_smart_load_06_total_consumption</a><br> |
| sigen_plant_smart_load_7_power | <a href='./TOPICS.md#sigen_0_247_30158'>sigen_0_smart_load_07_power</a><br> |
| sigen_plant_smart_load_7_total_consumption | <a href='./TOPICS.md#sigen_0_247_30110'>sigen_0_smart_load_07_total_consumption</a><br> |
| sigen_plant_smart_load_8_power | <a href='./TOPICS.md#sigen_0_247_30160'>sigen_0_smart_load_08_power</a><br> |
| sigen_plant_smart_load_8_total_consumption | <a href='./TOPICS.md#sigen_0_247_30112'>sigen_0_smart_load_08_total_consumption</a><br> |
| sigen_plant_smart_load_9_power | <a href='./TOPICS.md#sigen_0_247_30162'>sigen_0_smart_load_09_power</a><br> |
| sigen_plant_smart_load_9_total_consumption | <a href='./TOPICS.md#sigen_0_247_30114'>sigen_0_smart_load_09_total_consumption</a><br> |
| sigen_plant_start_stop | <a href='./TOPICS.md#sigen_0_247_40000'>sigen_0_plant_status</a><br> |
| sigen_plant_system_time | <a href='./TOPICS.md#sigen_0_247_30000'>sigen_0_plant_system_time</a><br> |
| sigen_plant_system_timezone | <a href='./TOPICS.md#sigen_0_247_30002'>sigen_0_plant_system_time_zone</a><br> |
| sigen_plant_third_party_photovoltaic_power | <a href='./TOPICS.md#sigen_0_247_30194'>sigen_0_third_party_pv_power</a><br> |
| sigen_plant_total_charged_energy_of_the_ess_2 | <a href='./TOPICS.md#sigen_0_247_30244'>sigen_0_si_total_charged_energy</a><br> |
| sigen_plant_total_charged_energy_of_the_evac | <a href='./TOPICS.md#sigen_0_247_30232'>sigen_0_si_total_ev_ac_charged_energy</a><br> |
| sigen_plant_total_charged_energy_of_the_evdc | <a href='./TOPICS.md#sigen_0_247_30208'>sigen_0_evdc_total_charge_energy</a><br> |
| sigen_plant_total_charged_energy_of_the_evdc_2 | <a href='./TOPICS.md#sigen_0_247_30252'>sigen_0_si_evdc_total_charge_energy</a><br> |
| sigen_plant_total_discharged_energy_of_the_ess_2 | <a href='./TOPICS.md#sigen_0_247_30248'>sigen_0_si_total_discharged_energy</a><br> |
| sigen_plant_total_discharged_energy_of_the_evdc | <a href='./TOPICS.md#sigen_0_247_30212'>sigen_0_evdc_total_discharge_energy</a><br> |
| sigen_plant_total_discharged_energy_of_the_evdc_2 | <a href='./TOPICS.md#sigen_0_247_30256'>sigen_0_si_evdc_total_discharge_energy</a><br> |
| sigen_plant_total_energy_consumption_of_common_loads | <a href='./TOPICS.md#sigen_0_247_30228'>sigen_0_si_total_common_load_consumption</a><br> |
| sigen_plant_total_energy_output_of_oil_fueled_generator | <a href='./TOPICS.md#sigen_0_247_30224'>sigen_0_plant_total_generator_output_energy</a><br> |
| sigen_plant_total_energy_output_of_oil_fueled_generator_2 | <a href='./TOPICS.md#sigen_0_247_30268'>sigen_0_si_total_generator_output_energy</a><br> |
| sigen_plant_total_exported_energy_2 | <a href='./TOPICS.md#sigen_0_247_30264'>sigen_0_si_total_exported_energy</a><br> |
| sigen_plant_total_generation_of_self_pv | <a href='./TOPICS.md#sigen_0_247_30236'>sigen_0_si_total_self_pv_generation</a><br> |
| sigen_plant_total_generation_of_third_party_inverter | <a href='./TOPICS.md#sigen_0_247_30196'>sigen_0_third_party_pv_lifetime_production</a><br> |
| sigen_plant_total_generation_of_third_party_inverter_2 | <a href='./TOPICS.md#sigen_0_247_30240'>sigen_0_si_total_third_party_pv_generation</a><br> |
| sigen_plant_total_imported_energy_2 | <a href='./TOPICS.md#sigen_0_247_30260'>sigen_0_si_total_imported_energy</a><br> |
