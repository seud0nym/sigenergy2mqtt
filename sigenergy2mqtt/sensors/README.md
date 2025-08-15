# MQTT Topics

Topics prefixed with `homeassistant/` are used when the `home-assistant` configuration `enabled` option in the configuration file,
or the `SIGENERGY2MQTT_HASS_ENABLED` environment variable, are set to true, or the `--hass-enabled` command line option is specified
Otherwise, the topics prefixed with `sigenergy2mqtt/` are used.

You can also enable the `sigenergy2mqtt/` topics when Home Assistant discovery is enabled by setting the `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` environment variable to true,
or by specifying the `--hass-use-simplified-topics` command line option.

The number after the `sigen_` prefix represents the host index from the configuration file, starting from 0. (Home Assistant configuration may change the `sigen` topic prefix.)
Inverter, AC Charger and DC Charger indexes use the device ID as specified in the configuration file.

Default Scan Intervals are shown in seconds, but may be overridden via configuration. Intervals for derived sensors are dependent on the source sensors.

## Published Topics

### Plant
<details>
<summary>
Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power/state</td></tr>
<tr><td>Source</td><td>30031</td></tr>
</table>
</details>
<details>
<summary>
Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40001</td></tr>
</table>
</details>
<details>
<summary>
Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40005</td></tr>
<tr><td>Comment</td><td>Range: [-100.00,100.00]</td></tr>
</table>
</details>
<details>
<summary>
Available Max Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_active_power/state</td></tr>
<tr><td>Source</td><td>30039</td></tr>
<tr><td>Comment</td><td>Feed to the AC terminal. Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Available Max Charging Capacity
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_charging_capacity/state</td></tr>
<tr><td>Source</td><td>30064</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Available Max Charging Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_charging_power/state</td></tr>
<tr><td>Source</td><td>30047</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Available Max Discharging Capacity
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_discharging_capacity/state</td></tr>
<tr><td>Source</td><td>30066</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Available Max Discharging Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_discharging_power/state</td></tr>
<tr><td>Source</td><td>30049</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Available Max Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_reactive_power/state</td></tr>
<tr><td>Source</td><td>30043</td></tr>
<tr><td>Comment</td><td>Feed to the AC terminal. Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Available Min Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_min_active_power/state</td></tr>
<tr><td>Source</td><td>30041</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Available Min Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_min_reactive_power/state</td></tr>
<tr><td>Source</td><td>30045</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
</table>
</details>
<details>
<summary>
Backup SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Source</td><td>40046</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
</table>
</details>
<details>
<summary>
Battery Charging Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_battery_charging_power/state</td></tr>
<tr><td>Source</td><td>BatteryPower &gt; 0</td></tr>
</table>
</details>
<details>
<summary>
Battery Discharging Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_battery_discharging_power/state</td></tr>
<tr><td>Source</td><td>BatteryPower &lt; 0</td></tr>
</table>
</details>
<details>
<summary>
Battery Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_power/state</td></tr>
<tr><td>Source</td><td>30037</td></tr>
<tr><td>Comment</td><td>ESS Power: <0 = discharging >0 = charging</td></tr>
</table>
</details>
<details>
<summary>
Battery SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_soc/state</td></tr>
<tr><td>Source</td><td>30014</td></tr>
</table>
</details>
<details>
<summary>
Battery SoH
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soh/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_soh/state</td></tr>
<tr><td>Source</td><td>30087</td></tr>
<tr><td>Comment</td><td>This value is the weighted average of the SOH of all ESS devices in the power plant, with each rated capacity as the weight</td></tr>
</table>
</details>
<details>
<summary>
Charge Cut-Off SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_charge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>30085</td></tr>
</table>
</details>
<details>
<summary>
Charge Cut-Off SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>40047</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
</table>
</details>
<details>
<summary>
Consumed Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_consumed_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_consumed_power/state</td></tr>
<tr><td>Source</td><td>TotalPVPower &plus; GridSensorActivePower &minus; BatteryPower &minus; ACChargerChargingPower &minus; DCChargerOutputPower</td></tr>
</table>
</details>
<details>
<summary>
DC Charger Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_5/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_5/state</td></tr>
<tr><td>Source</td><td>30072</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
</details>
<details>
<summary>
Daily Charge Energy
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_charge_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of DailyChargeEnergy across all Inverters associated with the Plant</td></tr>
</table>
</details>
<details>
<summary>
Daily Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_consumed_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_consumed_energy/state</td></tr>
<tr><td>Source</td><td>30092</td></tr>
</table>
</details>
<details>
<summary>
Daily Discharge Energy
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_discharge_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of DailyDischargeEnergy across all Inverters associated with the Plant</td></tr>
</table>
</details>
<details>
<summary>
Daily PV Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight</td></tr>
</table>
</details>
<details>
<summary>
Daily Total PV Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_total_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>TotalLifetimePVEnergy &minus; TotalLifetimePVEnergy at last midnight</td></tr>
</table>
</details>
<details>
<summary>
Discharge Cut-Off SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_discharge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>30086</td></tr>
</table>
</details>
<details>
<summary>
Discharge Cut-Off SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>40048</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
</table>
</details>
<details>
<summary>
EMS Work Mode
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_ems_work_mode/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ems_work_mode/state</td></tr>
<tr><td>Source</td><td>30003</td></tr>
</table>
</details>
<details>
<summary>
ESS Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_3/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_3/state</td></tr>
<tr><td>Source</td><td>30029</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
</details>
<details>
<summary>
Gateway Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_4/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_4/state</td></tr>
<tr><td>Source</td><td>30030</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
</details>
<details>
<summary>
Grid Max Export Limit
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Source</td><td>40038</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
</details>
<details>
<summary>
Grid Max Import Limit
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Source</td><td>40040</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
</details>
<details>
<summary>
Independent Phase Power Control
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Source</td><td>40030</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_accumulated_charge_energy/state</td></tr>
<tr><td>Source</td><td>30200</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_consumed_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_lifetime_consumed_energy/state</td></tr>
<tr><td>Source</td><td>30094</td></tr>
</table>
</details>
<details>
<summary>
Lifetime DC EV Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_evdc_total_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_evdc_total_charge_energy/state</td></tr>
<tr><td>Source</td><td>30208</td></tr>
</table>
</details>
<details>
<summary>
Lifetime DC EV Discharge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_evdc_total_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_evdc_total_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30212</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Discharge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_accumulated_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30204</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Generator Output Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_total_generator_output_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_total_generator_output_energy/state</td></tr>
<tr><td>Source</td><td>30224</td></tr>
</table>
</details>
<details>
<summary>
Lifetime PV Production
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>30088</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Third-Party PV Production
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_third_party_pv_lifetime_production/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_third_party_pv_lifetime_production/state</td></tr>
<tr><td>Source</td><td>30196</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Total PV Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of PlantPVTotalGeneration and ThirdPartyLifetimePVEnergy</td></tr>
</table>
</details>
<details>
<summary>
Max Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_active_power/state</td></tr>
<tr><td>Source</td><td>30010</td></tr>
<tr><td>Comment</td><td>This should be the base value of all active power adjustment actions</td></tr>
</table>
</details>
<details>
<summary>
Max Apparent Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_apparent_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_apparent_power/state</td></tr>
<tr><td>Source</td><td>30012</td></tr>
<tr><td>Comment</td><td>This should be the base value of all reactive power adjustment actions</td></tr>
</table>
</details>
<details>
<summary>
Max Charging Limit
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Source</td><td>40032</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Charging</td></tr>
</table>
</details>
<details>
<summary>
Max Discharging Limit
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Source</td><td>40034</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Discharging</td></tr>
</table>
</details>
<details>
<summary>
PCS Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_pcs_alarm/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_pcs_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 30027 and 30028</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
</details>
<details>
<summary>
PCS Max Export Limit
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Source</td><td>40042</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
</table>
</details>
<details>
<summary>
PCS Max Import Limit
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Source</td><td>40044</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
</table>
</details>
<details>
<summary>
PV Max Power Limit
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Source</td><td>40036</td></tr>
<tr><td>Comment</td><td>Takes effect when Remote EMS control mode (40031) is set to Command Charging/Discharging</td></tr>
</table>
</details>
<details>
<summary>
PV Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_power/state</td></tr>
<tr><td>Source</td><td>30035</td></tr>
</table>
</details>
<details>
<summary>
Phase A Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power/state</td></tr>
<tr><td>Source</td><td>30015</td></tr>
</table>
</details>
<details>
<summary>
Phase A Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40008</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
</details>
<details>
<summary>
Phase A Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40020</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
</table>
</details>
<details>
<summary>
Phase A Q/S Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40023</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
</table>
</details>
<details>
<summary>
Phase A Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power/state</td></tr>
<tr><td>Source</td><td>30021</td></tr>
</table>
</details>
<details>
<summary>
Phase A Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40014</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
</details>
<details>
<summary>
Phase B Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power/state</td></tr>
<tr><td>Source</td><td>30017</td></tr>
</table>
</details>
<details>
<summary>
Phase B Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40010</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
</details>
<details>
<summary>
Phase B Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40021</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
</table>
</details>
<details>
<summary>
Phase B Q/S Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40024</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
</table>
</details>
<details>
<summary>
Phase B Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power/state</td></tr>
<tr><td>Source</td><td>30023</td></tr>
</table>
</details>
<details>
<summary>
Phase B Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40016</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
</details>
<details>
<summary>
Phase C Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power/state</td></tr>
<tr><td>Source</td><td>30019</td></tr>
</table>
</details>
<details>
<summary>
Phase C Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40012</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
</details>
<details>
<summary>
Phase C Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40022</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
</table>
</details>
<details>
<summary>
Phase C Q/S Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40025</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
</table>
</details>
<details>
<summary>
Phase C Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power/state</td></tr>
<tr><td>Source</td><td>30025</td></tr>
</table>
</details>
<details>
<summary>
Phase C Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40018</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
</details>
<details>
<summary>
Power Factor Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40007</td></tr>
<tr><td>Comment</td><td>Range: (-1, -0.8] U [0.8, 1]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
</details>
<details>
<summary>
Q/S Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40006</td></tr>
<tr><td>Comment</td><td>Range: [-60.0,60.00]. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
</details>
<details>
<summary>
Rated Charging Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>30068</td></tr>
</table>
</details>
<details>
<summary>
Rated Discharging Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_discharging_power/state</td></tr>
<tr><td>Source</td><td>30070</td></tr>
</table>
</details>
<details>
<summary>
Rated Energy Capacity
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_energy_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_energy_capacity/state</td></tr>
<tr><td>Source</td><td>30083</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power/state</td></tr>
<tr><td>Source</td><td>30033</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40003</td></tr>
<tr><td>Comment</td><td>Range: [-60.00 * base value ,60.00 * base value]. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
</details>
<details>
<summary>
Remote EMS
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Source</td><td>40029</td></tr>
<tr><td>Comment</td><td>When needed to control EMS remotely, this register needs to be enabled. When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS</td></tr>
</table>
</details>
<details>
<summary>
Remote EMS Control Mode
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/select/sigen_0_247_powerplant/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Source</td><td>40031</td></tr>
</table>
</details>
<details>
<summary>
Running State
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_running_state/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_running_state/state</td></tr>
<tr><td>Source</td><td>30051</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 01 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_01_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_01_power/state</td></tr>
<tr><td>Source</td><td>30146</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 01 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_01_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_01_total_consumption/state</td></tr>
<tr><td>Source</td><td>30098</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 02 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_02_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_02_power/state</td></tr>
<tr><td>Source</td><td>30148</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 02 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_02_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_02_total_consumption/state</td></tr>
<tr><td>Source</td><td>30100</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 03 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_03_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_03_power/state</td></tr>
<tr><td>Source</td><td>30150</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 03 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_03_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_03_total_consumption/state</td></tr>
<tr><td>Source</td><td>30102</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 04 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_04_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_04_power/state</td></tr>
<tr><td>Source</td><td>30152</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 04 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_04_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_04_total_consumption/state</td></tr>
<tr><td>Source</td><td>30104</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 05 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_05_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_05_power/state</td></tr>
<tr><td>Source</td><td>30154</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 05 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_05_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_05_total_consumption/state</td></tr>
<tr><td>Source</td><td>30106</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 06 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_06_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_06_power/state</td></tr>
<tr><td>Source</td><td>30156</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 06 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_06_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_06_total_consumption/state</td></tr>
<tr><td>Source</td><td>30108</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 07 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_07_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_07_power/state</td></tr>
<tr><td>Source</td><td>30158</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 07 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_07_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_07_total_consumption/state</td></tr>
<tr><td>Source</td><td>30110</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 08 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_08_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_08_power/state</td></tr>
<tr><td>Source</td><td>30160</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 08 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_08_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_08_total_consumption/state</td></tr>
<tr><td>Source</td><td>30112</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 09 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_09_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_09_power/state</td></tr>
<tr><td>Source</td><td>30162</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 09 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_09_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_09_total_consumption/state</td></tr>
<tr><td>Source</td><td>30114</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 10 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_10_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_10_power/state</td></tr>
<tr><td>Source</td><td>30164</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 10 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_10_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_10_total_consumption/state</td></tr>
<tr><td>Source</td><td>30116</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 11 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_11_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_11_power/state</td></tr>
<tr><td>Source</td><td>30166</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 11 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_11_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_11_total_consumption/state</td></tr>
<tr><td>Source</td><td>30118</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 12 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_12_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_12_power/state</td></tr>
<tr><td>Source</td><td>30168</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 12 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_12_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_12_total_consumption/state</td></tr>
<tr><td>Source</td><td>30120</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 13 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_13_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_13_power/state</td></tr>
<tr><td>Source</td><td>30170</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 13 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_13_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_13_total_consumption/state</td></tr>
<tr><td>Source</td><td>30122</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 14 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_14_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_14_power/state</td></tr>
<tr><td>Source</td><td>30172</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 14 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_14_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_14_total_consumption/state</td></tr>
<tr><td>Source</td><td>30124</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 15 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_15_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_15_power/state</td></tr>
<tr><td>Source</td><td>30174</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 15 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_15_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_15_total_consumption/state</td></tr>
<tr><td>Source</td><td>30126</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 16 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_16_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_16_power/state</td></tr>
<tr><td>Source</td><td>30176</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 16 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_16_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_16_total_consumption/state</td></tr>
<tr><td>Source</td><td>30128</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 17 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_17_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_17_power/state</td></tr>
<tr><td>Source</td><td>30178</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 17 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_17_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_17_total_consumption/state</td></tr>
<tr><td>Source</td><td>30130</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 18 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_18_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_18_power/state</td></tr>
<tr><td>Source</td><td>30180</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 18 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_18_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_18_total_consumption/state</td></tr>
<tr><td>Source</td><td>30132</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 19 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_19_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_19_power/state</td></tr>
<tr><td>Source</td><td>30182</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 19 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_19_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_19_total_consumption/state</td></tr>
<tr><td>Source</td><td>30134</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 20 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_20_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_20_power/state</td></tr>
<tr><td>Source</td><td>30184</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 20 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_20_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_20_total_consumption/state</td></tr>
<tr><td>Source</td><td>30136</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 21 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_21_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_21_power/state</td></tr>
<tr><td>Source</td><td>30186</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 21 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_21_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_21_total_consumption/state</td></tr>
<tr><td>Source</td><td>30138</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 22 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_22_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_22_power/state</td></tr>
<tr><td>Source</td><td>30188</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 22 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_22_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_22_total_consumption/state</td></tr>
<tr><td>Source</td><td>30140</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 23 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_23_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_23_power/state</td></tr>
<tr><td>Source</td><td>30190</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 23 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_23_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_23_total_consumption/state</td></tr>
<tr><td>Source</td><td>30142</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 24 Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_24_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_24_power/state</td></tr>
<tr><td>Source</td><td>30192</td></tr>
</table>
</details>
<details>
<summary>
Smart Load 24 Total Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_24_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_24_total_consumption/state</td></tr>
<tr><td>Source</td><td>30144</td></tr>
</table>
</details>
<details>
<summary>
System Time
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_system_time/state</td></tr>
<tr><td>Source</td><td>30000</td></tr>
</table>
</details>
<details>
<summary>
System Time Zone
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time_zone/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_system_time_zone/state</td></tr>
<tr><td>Source</td><td>30002</td></tr>
</table>
</details>
<details>
<summary>
Third-Party PV Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_third_party_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_third_party_pv_power/state</td></tr>
<tr><td>Source</td><td>30194</td></tr>
</table>
</details>
<details>
<summary>
Total PV Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_total_pv_power/state</td></tr>
<tr><td>Source</td><td>PV Power + (sum of all Smart-Port PV Power sensors)</td></tr>
</table>
</details>

#### Grid Sensor
<details>
<summary>
Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_active_power/state</td></tr>
<tr><td>Source</td><td>30005</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
</details>
<details>
<summary>
Daily Exported Energy
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_export_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_daily_export_energy/state</td></tr>
<tr><td>Source</td><td>PlantTotalExportedEnergy &minus; PlantTotalExportedEnergy at last midnight</td></tr>
</table>
</details>
<details>
<summary>
Daily Imported Energy
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_import_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_daily_import_energy/state</td></tr>
<tr><td>Source</td><td>PlantTotalImportedEnergy &minus; PlantTotalImportedEnergy at last midnight</td></tr>
</table>
</details>
<details>
<summary>
Export Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_export_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_export_power/state</td></tr>
<tr><td>Source</td><td>GridSensorActivePower &lt; 0 &times; -1</td></tr>
</table>
</details>
<details>
<summary>
Grid Sensor Status
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_status/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_status/state</td></tr>
<tr><td>Source</td><td>30004</td></tr>
<tr><td>Comment</td><td>Gateway or meter connection status</td></tr>
</table>
</details>
<details>
<summary>
Grid Status
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_status/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_status/state</td></tr>
<tr><td>Source</td><td>30009</td></tr>
</table>
</details>
<details>
<summary>
Import Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_import_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_import_power/state</td></tr>
<tr><td>Source</td><td>GridSensorActivePower &gt; 0</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Exported Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_export_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_lifetime_export_energy/state</td></tr>
<tr><td>Source</td><td>30220</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Imported Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_import_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_lifetime_import_energy/state</td></tr>
<tr><td>Source</td><td>30216</td></tr>
</table>
</details>
<details>
<summary>
Phase A Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_a_active_power/state</td></tr>
<tr><td>Source</td><td>30052</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
</details>
<details>
<summary>
Phase A Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_a_reactive_power/state</td></tr>
<tr><td>Source</td><td>30058</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>
</details>
<details>
<summary>
Phase B Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_b_active_power/state</td></tr>
<tr><td>Source</td><td>30054</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
</details>
<details>
<summary>
Phase B Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_b_reactive_power/state</td></tr>
<tr><td>Source</td><td>30060</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>
</details>
<details>
<summary>
Phase C Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_c_active_power/state</td></tr>
<tr><td>Source</td><td>30056</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
</details>
<details>
<summary>
Phase C Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_c_reactive_power/state</td></tr>
<tr><td>Source</td><td>30062</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>var</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_reactive_power/state</td></tr>
<tr><td>Source</td><td>30007</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>
</details>

#### Smart-Port (Enphase Envoy only)
<details>
<summary>
Current
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_current/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
</details>
<details>
<summary>
Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
</details>
<details>
<summary>
Frequency
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_frequency/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_frequency/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
</details>
<details>
<summary>
PV Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_active_power/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API</td></tr>
</table>
</details>
<details>
<summary>
Power Factor
</summary>
<table>
<tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_power_factor/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_power_factor/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_reactive_power/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
</details>
<details>
<summary>
Voltage
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_voltage/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
</details>

#### Statistics
<details>
<summary>
Total AC EV Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_ev_ac_charged_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_ev_ac_charged_energy/state</td></tr>
<tr><td>Source</td><td>30232</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_charged_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_charged_energy/state</td></tr>
<tr><td>Source</td><td>30244</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total Common Load Consumption
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_common_load_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_common_load_consumption/state</td></tr>
<tr><td>Source</td><td>30228</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total DC EV Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_evdc_total_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_evdc_total_charge_energy/state</td></tr>
<tr><td>Source</td><td>30252</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total DC EV Discharge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_evdc_total_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_evdc_total_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30256</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total Discharge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_discharged_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_discharged_energy/state</td></tr>
<tr><td>Source</td><td>30248</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total Exported Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_exported_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_exported_energy/state</td></tr>
<tr><td>Source</td><td>30264</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total Generator Output Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_generator_output_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_generator_output_energy/state</td></tr>
<tr><td>Source</td><td>30268</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total Imported Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_imported_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_imported_energy/state</td></tr>
<tr><td>Source</td><td>30260</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total PV Production
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_self_pv_generation/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_self_pv_generation/state</td></tr>
<tr><td>Source</td><td>30236</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>
<details>
<summary>
Total Third-Party PV Production
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_third_party_pv_generation/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_third_party_pv_generation/state</td></tr>
<tr><td>Source</td><td>30240</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
</details>

### Inverter
<details>
<summary>
A-B Line Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_a_b_line_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_a_b_line_voltage/state</td></tr>
<tr><td>Source</td><td>31005</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power/state</td></tr>
<tr><td>Source</td><td>30587</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Active Power Fixed Value Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Source</td><td>41501</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Active Power Fixed Value Adjustment Feedback
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30613</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Active Power Percentage Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Source</td><td>41505</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Active Power Percentage Adjustment Feedback
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30617</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
B-C Line Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_b_c_line_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_b_c_line_voltage/state</td></tr>
<tr><td>Source</td><td>31007</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
C-A Line Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_c_a_line_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_c_a_line_voltage/state</td></tr>
<tr><td>Source</td><td>31009</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Daily Production
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>31509</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Firmware Version
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_firmware_version/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_firmware_version/state</td></tr>
<tr><td>Source</td><td>30525</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Gateway Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_alarm_4/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_4/state</td></tr>
<tr><td>Source</td><td>30608</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Grid Frequency
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_grid_frequency/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_grid_frequency/state</td></tr>
<tr><td>Source</td><td>31002</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Insulation Resistance
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>MΩ</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_insulation_resistance/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_insulation_resistance/state</td></tr>
<tr><td>Source</td><td>31037</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Lifetime Production
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>31511</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
MPTT Count
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_mptt_count/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_mptt_count/state</td></tr>
<tr><td>Source</td><td>31026</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Max Absorption Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_absorption_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_absorption_power/state</td></tr>
<tr><td>Source</td><td>30546</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Max Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_active_power/state</td></tr>
<tr><td>Source</td><td>30544</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Max Active Power Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_active_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30579</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Max Rated Apparent Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kVA</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_rated_apparent_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_rated_apparent_power/state</td></tr>
<tr><td>Source</td><td>30542</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Max Reactive Power Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_reactive_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_reactive_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30583</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Min Active Power Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_active_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_active_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30581</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Min Reactive Power Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_reactive_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_reactive_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30585</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Output Type
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_output_type/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_output_type/state</td></tr>
<tr><td>Source</td><td>31004</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PACK/BCU Count
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pack_bcu_count/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pack_bcu_count/state</td></tr>
<tr><td>Source</td><td>31024</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
PCS Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pcs_alarm/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pcs_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 30605 and 30606</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv_power/state</td></tr>
<tr><td>Source</td><td>31035</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String Count
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_string_count/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv_string_count/state</td></tr>
<tr><td>Source</td><td>31025</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Phase A Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_a_current/state</td></tr>
<tr><td>Source</td><td>31017</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Phase A Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_a_voltage/state</td></tr>
<tr><td>Source</td><td>31011</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Phase B Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_b_current/state</td></tr>
<tr><td>Source</td><td>31019</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Phase B Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_b_voltage/state</td></tr>
<tr><td>Source</td><td>31013</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Phase C Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_c_current/state</td></tr>
<tr><td>Source</td><td>31021</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Phase C Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_c_voltage/state</td></tr>
<tr><td>Source</td><td>31015</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Power Factor
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_power_factor/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor/state</td></tr>
<tr><td>Source</td><td>31023</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Power Factor Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Source</td><td>41507</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Rated Active Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_active_power/state</td></tr>
<tr><td>Source</td><td>30540</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Rated Grid Frequency
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_frequency/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_grid_frequency/state</td></tr>
<tr><td>Source</td><td>31001</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Rated Grid Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_grid_voltage/state</td></tr>
<tr><td>Source</td><td>31000</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Reactive Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power/state</td></tr>
<tr><td>Source</td><td>30589</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Fixed Value Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Source</td><td>41503</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Fixed Value Adjustment Feedback
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30615</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Percentage Adjustment Feedback
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30618</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Q/S Adjustment
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Source</td><td>41506</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Remote EMS Dispatch
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/switch/sigen_0_001_inverter/sigen_0_inverter_1_remote_ems_dispatch/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/state</td></tr>
<tr><td>Source</td><td>41500</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Running State
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_running_state/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_running_state/state</td></tr>
<tr><td>Source</td><td>30578</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Shutdown Time
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_shutdown_time/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_shutdown_time/state</td></tr>
<tr><td>Source</td><td>31040</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Startup Time
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_startup_time/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_startup_time/state</td></tr>
<tr><td>Source</td><td>31038</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Temperature
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_temperature/state</td></tr>
<tr><td>Source</td><td>31003</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>

#### Energy Storage System
<details>
<summary>
Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_alarm_3/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_3/state</td></tr>
<tr><td>Source</td><td>30607</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Available Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_available_battery_charge_energy/state</td></tr>
<tr><td>Source</td><td>30595</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Available Discharge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_available_battery_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30597</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Average Cell Temperature
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_average_cell_temperature/state</td></tr>
<tr><td>Source</td><td>30603</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Average Cell Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_average_cell_voltage/state</td></tr>
<tr><td>Source</td><td>30604</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Battery Charging Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_charging_power/state</td></tr>
<tr><td>Source</td><td>ChargeDischargePower &gt; 0</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
Battery Discharging Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_discharging_power/state</td></tr>
<tr><td>Source</td><td>ChargeDischargePower &lt; 0 &times; -1</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
Battery Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_charge_discharge_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_charge_discharge_power/state</td></tr>
<tr><td>Source</td><td>30599</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Battery SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_soc/state</td></tr>
<tr><td>Source</td><td>30601</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Battery SoH
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soh/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_soh/state</td></tr>
<tr><td>Source</td><td>30602</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Daily Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_charge_energy/state</td></tr>
<tr><td>Source</td><td>30566</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Daily Discharge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30572</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Charge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_accumulated_charge_energy/state</td></tr>
<tr><td>Source</td><td>30568</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Lifetime Discharge Energy
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_accumulated_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30574</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Max Battery Temperature
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_temperature/state</td></tr>
<tr><td>Source</td><td>30620</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Max Charge Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_charge_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_charge_power/state</td></tr>
<tr><td>Source</td><td>30591</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Max Discharge Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_discharge_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_discharge_power/state</td></tr>
<tr><td>Source</td><td>30593</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Min Battery Temperature
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_min_battery_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_battery_temperature/state</td></tr>
<tr><td>Source</td><td>30621</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Rated Battery Capacity
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_battery_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_battery_capacity/state</td></tr>
<tr><td>Source</td><td>30548</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Rated Charging Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>30550</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Rated Discharging Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_discharging_power/state</td></tr>
<tr><td>Source</td><td>30552</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
</details>

#### PV String

The actual number of PV Strings is determined from `PV String Count` in the Inverter.
<details>
<summary>
PV String 1 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_current/state</td></tr>
<tr><td>Source</td><td>31028</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 2 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_current/state</td></tr>
<tr><td>Source</td><td>31030</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 3 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_current/state</td></tr>
<tr><td>Source</td><td>31032</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 4 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_current/state</td></tr>
<tr><td>Source</td><td>31034</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 5 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_current/state</td></tr>
<tr><td>Source</td><td>31043</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 6 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_current/state</td></tr>
<tr><td>Source</td><td>31045</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 7 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_current/state</td></tr>
<tr><td>Source</td><td>31047</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 8 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_current/state</td></tr>
<tr><td>Source</td><td>31049</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 9 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_current/state</td></tr>
<tr><td>Source</td><td>31051</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 10 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_current/state</td></tr>
<tr><td>Source</td><td>31053</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 11 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_current/state</td></tr>
<tr><td>Source</td><td>31055</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 12 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_current/state</td></tr>
<tr><td>Source</td><td>31057</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 13 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_current/state</td></tr>
<tr><td>Source</td><td>31059</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 14 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_current/state</td></tr>
<tr><td>Source</td><td>31061</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 15 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_current/state</td></tr>
<tr><td>Source</td><td>31063</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 16 Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_current/state</td></tr>
<tr><td>Source</td><td>31065</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 1 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 2 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 3 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 4 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 5 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 6 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 7 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 8 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 9 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 10 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 11 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 12 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 13 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 14 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 15 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 16 Daily Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 1 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 2 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 3 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 4 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 5 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 6 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 7 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 8 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 9 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 10 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 11 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 12 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 13 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 14 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 15 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 16 Lifetime Production
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 1 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 2 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 3 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 4 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 5 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 6 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 7 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 8 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 9 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 10 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 11 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 12 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 13 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 14 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 15 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 16 Power
</summary>
<table>
<tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
</details>
<details>
<summary>
PV String 1 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_voltage/state</td></tr>
<tr><td>Source</td><td>31027</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 2 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_voltage/state</td></tr>
<tr><td>Source</td><td>31029</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 3 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_voltage/state</td></tr>
<tr><td>Source</td><td>31031</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 4 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_voltage/state</td></tr>
<tr><td>Source</td><td>31033</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 5 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_voltage/state</td></tr>
<tr><td>Source</td><td>31042</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 6 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_voltage/state</td></tr>
<tr><td>Source</td><td>31044</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 7 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_voltage/state</td></tr>
<tr><td>Source</td><td>31046</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 8 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_voltage/state</td></tr>
<tr><td>Source</td><td>31048</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 9 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_voltage/state</td></tr>
<tr><td>Source</td><td>31050</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 10 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_voltage/state</td></tr>
<tr><td>Source</td><td>31052</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 11 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_voltage/state</td></tr>
<tr><td>Source</td><td>31054</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 12 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_voltage/state</td></tr>
<tr><td>Source</td><td>31056</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 13 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_voltage/state</td></tr>
<tr><td>Source</td><td>31058</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 14 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_voltage/state</td></tr>
<tr><td>Source</td><td>31060</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 15 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_voltage/state</td></tr>
<tr><td>Source</td><td>31062</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
PV String 16 Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_voltage/state</td></tr>
<tr><td>Source</td><td>31064</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>

### AC Charger
<details>
<summary>
Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_alarm/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 32012, 32013, and 32014</td></tr>
</table>
</details>
<details>
<summary>
Charging Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>32003</td></tr>
</table>
</details>
<details>
<summary>
Input Breaker
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_input_breaker/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_input_breaker/state</td></tr>
<tr><td>Source</td><td>32010</td></tr>
</table>
</details>
<details>
<summary>
Output Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_002_accharger/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Source</td><td>42001</td></tr>
</table>
</details>
<details>
<summary>
Rated Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_current/state</td></tr>
<tr><td>Source</td><td>32007</td></tr>
</table>
</details>
<details>
<summary>
Rated Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_power/state</td></tr>
<tr><td>Source</td><td>32005</td></tr>
</table>
</details>
<details>
<summary>
Rated Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_voltage/state</td></tr>
<tr><td>Source</td><td>32009</td></tr>
</table>
</details>
<details>
<summary>
Running State
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_running_state/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_running_state/state</td></tr>
<tr><td>Source</td><td>32000</td></tr>
</table>
</details>
<details>
<summary>
Total Energy Consumed
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_total_energy_consumed/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_total_energy_consumed/state</td></tr>
<tr><td>Source</td><td>32001</td></tr>
</table>
</details>

### DC Charger
<details>
<summary>
Alarms
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_inverter_1_alarm_5/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_5/state</td></tr>
<tr><td>Source</td><td>30609</td></tr>
</table>
</details>
<details>
<summary>
Current Charging Capacity
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_dc_charger_current_charging_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_dc_charger_current_charging_capacity/state</td></tr>
<tr><td>Source</td><td>31505</td></tr>
<tr><td>Comment</td><td>Single time</td></tr>
</table>
</details>
<details>
<summary>
Current Charging Duration
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>s</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_dc_charger_current_charging_duration/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_dc_charger_current_charging_duration/state</td></tr>
<tr><td>Source</td><td>31507</td></tr>
<tr><td>Comment</td><td>Single time</td></tr>
</table>
</details>
<details>
<summary>
Output Power
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_dc_charger_output_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_dc_charger_output_power/state</td></tr>
<tr><td>Source</td><td>31502</td></tr>
</table>
</details>
<details>
<summary>
Vehicle Battery Voltage
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_vehicle_battery_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_vehicle_battery_voltage/state</td></tr>
<tr><td>Source</td><td>31500</td></tr>
</table>
</details>
<details>
<summary>
Vehicle Charging Current
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_vehicle_charging_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_vehicle_charging_current/state</td></tr>
<tr><td>Source</td><td>31501</td></tr>
</table>
</details>
<details>
<summary>
Vehicle SoC
</summary>
<table>
<tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_vehicle_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_vehicle_soc/state</td></tr>
<tr><td>Source</td><td>31504</td></tr>
</table>
</details>

### Metrics

Metrics are _only_ published to the sigenergy2mqtt/metrics topics, even when Home Assistant discovery is enabled. The scan interval cannot be altered.
| Metric | Interval | Unit | State Topic|
|--------|---------:|------|-------------|
| Modbus Active Locks | 1 |  | sigenergy2mqtt/metrics/modbus_locks |
| Modbus Read Errors | 1 |  | sigenergy2mqtt/metrics/modbus_read_errors |
| Modbus Read Max | 1 | ms | sigenergy2mqtt/metrics/modbus_read_max |
| Modbus Read Mean | 1 | ms | sigenergy2mqtt/metrics/modbus_read_mean |
| Modbus Read Min | 1 | ms | sigenergy2mqtt/metrics/modbus_read_min |
| Modbus Reads/second | 1 |  | sigenergy2mqtt/metrics/modbus_reads_sec |
| Modbus Write Errors | 1 |  | sigenergy2mqtt/metrics/modbus_write_errors |
| Modbus Write Max | 1 | ms | sigenergy2mqtt/metrics/modbus_write_max |
| Modbus Write Mean | 1 | ms | sigenergy2mqtt/metrics/modbus_write_mean |
| Modbus Write Min | 1 | ms | sigenergy2mqtt/metrics/modbus_write_min |
| Protocol Published | 1 |  | sigenergy2mqtt/metrics/modbus_protocol_published |
| Protocol Version | 1 |  | sigenergy2mqtt/metrics/modbus_protocol |
| Started | 1 |  | sigenergy2mqtt/metrics/started |

## Subscribed Topics

### Plant
<details>
<summary>
Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Backup SoC
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/set</td></tr>
</table>
</details>
<details>
<summary>
Charge Cut-Off SoC
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/set</td></tr>
</table>
</details>
<details>
<summary>
Discharge Cut-Off SoC
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/set</td></tr>
</table>
</details>
<details>
<summary>
Grid Max Export Limit
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/set</td></tr>
</table>
</details>
<details>
<summary>
Grid Max Import Limit
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/set</td></tr>
</table>
</details>
<details>
<summary>
Independent Phase Power Control
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/set</td></tr>
</table>
</details>
<details>
<summary>
Max Charging Limit
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/set</td></tr>
</table>
</details>
<details>
<summary>
Max Discharging Limit
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/set</td></tr>
</table>
</details>
<details>
<summary>
PCS Max Export Limit
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/set</td></tr>
</table>
</details>
<details>
<summary>
PCS Max Import Limit
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/set</td></tr>
</table>
</details>
<details>
<summary>
PV Max Power Limit
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/set</td></tr>
</table>
</details>
<details>
<summary>
Phase A Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase A Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase A Q/S Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase A Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase B Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase B Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase B Q/S Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase B Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase C Active Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase C Active Power Percentage Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase C Q/S Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Phase C Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Power On/Off
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_status/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_status/set</td></tr>
</table>
</details>
<details>
<summary>
Power Factor Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Q/S Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Fixed Adjustment Target Value
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
</details>
<details>
<summary>
Remote EMS
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/set</td></tr>
</table>
</details>
<details>
<summary>
Remote EMS Control Mode
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/set</td></tr>
</table>
</details>

### Inverter
<details>
<summary>
Active Power Fixed Value Adjustment
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Active Power Percentage Adjustment
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Power On/Off
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_status/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_status/set</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
</details>
<details>
<summary>
Power Factor Adjustment
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Fixed Value Adjustment
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Reactive Power Q/S Adjustment
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>
<details>
<summary>
Remote EMS Dispatch
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
</details>

### AC Charger
<details>
<summary>
Output Current
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/set</td></tr>
</table>
</details>
<details>
<summary>
Power On/Off
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_status/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_status/set</td></tr>
</table>
</details>

### DC Charger
<details>
<summary>
DC Charger Status
</summary>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_status/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_status/set</td></tr>
</table>
</details>
