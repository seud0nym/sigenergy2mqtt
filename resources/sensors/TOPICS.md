# MQTT Topics

Topics prefixed with `homeassistant/` are used when the `home-assistant` configuration `enabled` option in the configuration file,
or the `SIGENERGY2MQTT_HASS_ENABLED` environment variable, are set to true, or the `--hass-enabled` command line option is specified
Otherwise, the topics prefixed with `sigenergy2mqtt/` are used.

You can also enable the `sigenergy2mqtt/` topics when Home Assistant discovery is enabled by setting the `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` environment variable to true,
or by specifying the `--hass-use-simplified-topics` command line option.

Default Scan Intervals are shown in seconds, but may be overridden via configuration. Intervals for derived sensors are dependent on the source sensors.

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

<table>
<tr><th>Published Topics</th><th>Subscribed Topics</th></tr>
<tr><td>

<h6>Plant</h6>
<a href='#sigen_0_247_30031' style='font-size:small;'>Active Power</a><br>
<a href='#sigen_0_247_40001' style='font-size:small;'>Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40005' style='font-size:small;'>Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_30039' style='font-size:small;'>Available Max Active Power</a><br>
<a href='#sigen_0_247_30064' style='font-size:small;'>Available Max Charging Capacity</a><br>
<a href='#sigen_0_247_30047' style='font-size:small;'>Available Max Charging Power</a><br>
<a href='#sigen_0_247_30066' style='font-size:small;'>Available Max Discharging Capacity</a><br>
<a href='#sigen_0_247_30049' style='font-size:small;'>Available Max Discharging Power</a><br>
<a href='#sigen_0_247_30043' style='font-size:small;'>Available Max Reactive Power</a><br>
<a href='#sigen_0_247_30041' style='font-size:small;'>Available Min Active Power</a><br>
<a href='#sigen_0_247_30045' style='font-size:small;'>Available Min Reactive Power</a><br>
<a href='#sigen_0_247_40046' style='font-size:small;'>Backup SoC</a><br>
<a href='#sigen_0_battery_charging_power' style='font-size:small;'>Battery Charging Power</a><br>
<a href='#sigen_0_battery_discharging_power' style='font-size:small;'>Battery Discharging Power</a><br>
<a href='#sigen_0_247_30037' style='font-size:small;'>Battery Power</a><br>
<a href='#sigen_0_247_30014' style='font-size:small;'>Battery SoC</a><br>
<a href='#sigen_0_247_30087' style='font-size:small;'>Battery SoH</a><br>
<a href='#sigen_0_247_30085' style='font-size:small;'>Charge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40047' style='font-size:small;'>Charge Cut-Off SoC</a><br>
<a href='#sigen_0_consumed_power' style='font-size:small;'>Consumed Power</a><br>
<a href='#sigen_0_247_30072' style='font-size:small;'>DC Charger Alarms</a><br>
<a href='#sigen_0_daily_charge_energy' style='font-size:small;'>Daily Charge Energy</a><br>
<a href='#sigen_0_daily_consumed_energy' style='font-size:small;'>Daily Consumption</a><br>
<a href='#sigen_0_daily_discharge_energy' style='font-size:small;'>Daily Discharge Energy</a><br>
<a href='#sigen_0_daily_pv_energy' style='font-size:small;'>Daily PV Production</a><br>
<a href='#sigen_0_total_daily_pv_energy' style='font-size:small;'>Daily Total PV Production</a><br>
<a href='#sigen_0_247_30086' style='font-size:small;'>Discharge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40048' style='font-size:small;'>Discharge Cut-Off SoC</a><br>
<a href='#sigen_0_247_30003' style='font-size:small;'>EMS Work Mode</a><br>
<a href='#sigen_0_247_30029' style='font-size:small;'>ESS Alarms</a><br>
<a href='#sigen_0_247_30030' style='font-size:small;'>Gateway Alarms</a><br>
<a href='#sigen_0_247_40038' style='font-size:small;'>Grid Max Export Limit</a><br>
<a href='#sigen_0_247_40040' style='font-size:small;'>Grid Max Import Limit</a><br>
<a href='#sigen_0_247_40030' style='font-size:small;'>Independent Phase Power Control</a><br>
<a href='#sigen_0_accumulated_charge_energy' style='font-size:small;'>Lifetime Charge Energy</a><br>
<a href='#sigen_0_lifetime_consumed_energy' style='font-size:small;'>Lifetime Consumption</a><br>
<a href='#sigen_0_247_30208' style='font-size:small;'>Lifetime DC EV Charge Energy</a><br>
<a href='#sigen_0_247_30212' style='font-size:small;'>Lifetime DC EV Discharge Energy</a><br>
<a href='#sigen_0_accumulated_discharge_energy' style='font-size:small;'>Lifetime Discharge Energy</a><br>
<a href='#sigen_0_247_30224' style='font-size:small;'>Lifetime Generator Output Energy</a><br>
<a href='#sigen_0_247_30088' style='font-size:small;'>Lifetime PV Production</a><br>
<a href='#sigen_0_247_30196' style='font-size:small;'>Lifetime Third-Party PV Production</a><br>
<a href='#sigen_0_lifetime_pv_energy' style='font-size:small;'>Lifetime Total PV Production</a><br>
<a href='#sigen_0_247_30010' style='font-size:small;'>Max Active Power</a><br>
<a href='#sigen_0_247_30012' style='font-size:small;'>Max Apparent Power</a><br>
<a href='#sigen_0_247_40032' style='font-size:small;'>Max Charging Limit</a><br>
<a href='#sigen_0_247_40034' style='font-size:small;'>Max Discharging Limit</a><br>
<a href='#sigen_0_general_pcs_alarm' style='font-size:small;'>PCS Alarms</a><br>
<a href='#sigen_0_247_40042' style='font-size:small;'>PCS Max Export Limit</a><br>
<a href='#sigen_0_247_40044' style='font-size:small;'>PCS Max Import Limit</a><br>
<a href='#sigen_0_247_40036' style='font-size:small;'>PV Max Power Limit</a><br>
<a href='#sigen_0_247_30035' style='font-size:small;'>PV Power</a><br>
<a href='#sigen_0_247_30015' style='font-size:small;'>Phase A Active Power</a><br>
<a href='#sigen_0_247_40008' style='font-size:small;'>Phase A Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40020' style='font-size:small;'>Phase A Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40023' style='font-size:small;'>Phase A Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30021' style='font-size:small;'>Phase A Reactive Power</a><br>
<a href='#sigen_0_247_40014' style='font-size:small;'>Phase A Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30017' style='font-size:small;'>Phase B Active Power</a><br>
<a href='#sigen_0_247_40010' style='font-size:small;'>Phase B Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40021' style='font-size:small;'>Phase B Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40024' style='font-size:small;'>Phase B Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30023' style='font-size:small;'>Phase B Reactive Power</a><br>
<a href='#sigen_0_247_40016' style='font-size:small;'>Phase B Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30019' style='font-size:small;'>Phase C Active Power</a><br>
<a href='#sigen_0_247_40012' style='font-size:small;'>Phase C Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40022' style='font-size:small;'>Phase C Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40025' style='font-size:small;'>Phase C Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30025' style='font-size:small;'>Phase C Reactive Power</a><br>
<a href='#sigen_0_247_40018' style='font-size:small;'>Phase C Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40007' style='font-size:small;'>Power Factor Adjustment Target Value</a><br>
<a href='#sigen_0_247_40006' style='font-size:small;'>Q/S Adjustment Target Value</a><br>
<a href='#sigen_0_247_30068' style='font-size:small;'>Rated Charging Power</a><br>
<a href='#sigen_0_247_30070' style='font-size:small;'>Rated Discharging Power</a><br>
<a href='#sigen_0_247_30083' style='font-size:small;'>Rated Energy Capacity</a><br>
<a href='#sigen_0_247_30033' style='font-size:small;'>Reactive Power</a><br>
<a href='#sigen_0_247_40003' style='font-size:small;'>Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40029' style='font-size:small;'>Remote EMS</a><br>
<a href='#sigen_0_247_40031' style='font-size:small;'>Remote EMS Control Mode</a><br>
<a href='#sigen_0_247_30051' style='font-size:small;'>Running State</a><br>
<a href='#sigen_0_247_30146' style='font-size:small;'>Smart Load 01 Power</a><br>
<a href='#sigen_0_247_30098' style='font-size:small;'>Smart Load 01 Total Consumption</a><br>
<a href='#sigen_0_247_30148' style='font-size:small;'>Smart Load 02 Power</a><br>
<a href='#sigen_0_247_30100' style='font-size:small;'>Smart Load 02 Total Consumption</a><br>
<a href='#sigen_0_247_30150' style='font-size:small;'>Smart Load 03 Power</a><br>
<a href='#sigen_0_247_30102' style='font-size:small;'>Smart Load 03 Total Consumption</a><br>
<a href='#sigen_0_247_30152' style='font-size:small;'>Smart Load 04 Power</a><br>
<a href='#sigen_0_247_30104' style='font-size:small;'>Smart Load 04 Total Consumption</a><br>
<a href='#sigen_0_247_30154' style='font-size:small;'>Smart Load 05 Power</a><br>
<a href='#sigen_0_247_30106' style='font-size:small;'>Smart Load 05 Total Consumption</a><br>
<a href='#sigen_0_247_30156' style='font-size:small;'>Smart Load 06 Power</a><br>
<a href='#sigen_0_247_30108' style='font-size:small;'>Smart Load 06 Total Consumption</a><br>
<a href='#sigen_0_247_30158' style='font-size:small;'>Smart Load 07 Power</a><br>
<a href='#sigen_0_247_30110' style='font-size:small;'>Smart Load 07 Total Consumption</a><br>
<a href='#sigen_0_247_30160' style='font-size:small;'>Smart Load 08 Power</a><br>
<a href='#sigen_0_247_30112' style='font-size:small;'>Smart Load 08 Total Consumption</a><br>
<a href='#sigen_0_247_30162' style='font-size:small;'>Smart Load 09 Power</a><br>
<a href='#sigen_0_247_30114' style='font-size:small;'>Smart Load 09 Total Consumption</a><br>
<a href='#sigen_0_247_30164' style='font-size:small;'>Smart Load 10 Power</a><br>
<a href='#sigen_0_247_30116' style='font-size:small;'>Smart Load 10 Total Consumption</a><br>
<a href='#sigen_0_247_30166' style='font-size:small;'>Smart Load 11 Power</a><br>
<a href='#sigen_0_247_30118' style='font-size:small;'>Smart Load 11 Total Consumption</a><br>
<a href='#sigen_0_247_30168' style='font-size:small;'>Smart Load 12 Power</a><br>
<a href='#sigen_0_247_30120' style='font-size:small;'>Smart Load 12 Total Consumption</a><br>
<a href='#sigen_0_247_30170' style='font-size:small;'>Smart Load 13 Power</a><br>
<a href='#sigen_0_247_30122' style='font-size:small;'>Smart Load 13 Total Consumption</a><br>
<a href='#sigen_0_247_30172' style='font-size:small;'>Smart Load 14 Power</a><br>
<a href='#sigen_0_247_30124' style='font-size:small;'>Smart Load 14 Total Consumption</a><br>
<a href='#sigen_0_247_30174' style='font-size:small;'>Smart Load 15 Power</a><br>
<a href='#sigen_0_247_30126' style='font-size:small;'>Smart Load 15 Total Consumption</a><br>
<a href='#sigen_0_247_30176' style='font-size:small;'>Smart Load 16 Power</a><br>
<a href='#sigen_0_247_30128' style='font-size:small;'>Smart Load 16 Total Consumption</a><br>
<a href='#sigen_0_247_30178' style='font-size:small;'>Smart Load 17 Power</a><br>
<a href='#sigen_0_247_30130' style='font-size:small;'>Smart Load 17 Total Consumption</a><br>
<a href='#sigen_0_247_30180' style='font-size:small;'>Smart Load 18 Power</a><br>
<a href='#sigen_0_247_30132' style='font-size:small;'>Smart Load 18 Total Consumption</a><br>
<a href='#sigen_0_247_30182' style='font-size:small;'>Smart Load 19 Power</a><br>
<a href='#sigen_0_247_30134' style='font-size:small;'>Smart Load 19 Total Consumption</a><br>
<a href='#sigen_0_247_30184' style='font-size:small;'>Smart Load 20 Power</a><br>
<a href='#sigen_0_247_30136' style='font-size:small;'>Smart Load 20 Total Consumption</a><br>
<a href='#sigen_0_247_30186' style='font-size:small;'>Smart Load 21 Power</a><br>
<a href='#sigen_0_247_30138' style='font-size:small;'>Smart Load 21 Total Consumption</a><br>
<a href='#sigen_0_247_30188' style='font-size:small;'>Smart Load 22 Power</a><br>
<a href='#sigen_0_247_30140' style='font-size:small;'>Smart Load 22 Total Consumption</a><br>
<a href='#sigen_0_247_30190' style='font-size:small;'>Smart Load 23 Power</a><br>
<a href='#sigen_0_247_30142' style='font-size:small;'>Smart Load 23 Total Consumption</a><br>
<a href='#sigen_0_247_30192' style='font-size:small;'>Smart Load 24 Power</a><br>
<a href='#sigen_0_247_30144' style='font-size:small;'>Smart Load 24 Total Consumption</a><br>
<a href='#sigen_0_247_30000' style='font-size:small;'>System Time</a><br>
<a href='#sigen_0_247_30002' style='font-size:small;'>System Time Zone</a><br>
<a href='#sigen_0_247_30194' style='font-size:small;'>Third-Party PV Power</a><br>
<a href='#sigen_0_total_pv_power' style='font-size:small;'>Total PV Power</a><br>

<h6>Grid Sensor</h6>
<a href='#sigen_0_247_30005' style='font-size:small;'>Active Power</a><br>
<a href='#sigen_0_grid_sensor_daily_export_energy' style='font-size:small;'>Daily Exported Energy</a><br>
<a href='#sigen_0_grid_sensor_daily_import_energy' style='font-size:small;'>Daily Imported Energy</a><br>
<a href='#sigen_0_grid_sensor_export_power' style='font-size:small;'>Export Power</a><br>
<a href='#sigen_0_247_30004' style='font-size:small;'>Grid Sensor Status</a><br>
<a href='#sigen_0_247_30009' style='font-size:small;'>Grid Status</a><br>
<a href='#sigen_0_grid_sensor_import_power' style='font-size:small;'>Import Power</a><br>
<a href='#sigen_0_grid_sensor_lifetime_export_energy' style='font-size:small;'>Lifetime Exported Energy</a><br>
<a href='#sigen_0_grid_sensor_lifetime_import_energy' style='font-size:small;'>Lifetime Imported Energy</a><br>
<a href='#sigen_0_247_30052' style='font-size:small;'>Phase A Active Power</a><br>
<a href='#sigen_0_247_30058' style='font-size:small;'>Phase A Reactive Power</a><br>
<a href='#sigen_0_247_30054' style='font-size:small;'>Phase B Active Power</a><br>
<a href='#sigen_0_247_30060' style='font-size:small;'>Phase B Reactive Power</a><br>
<a href='#sigen_0_247_30056' style='font-size:small;'>Phase C Active Power</a><br>
<a href='#sigen_0_247_30062' style='font-size:small;'>Phase C Reactive Power</a><br>
<a href='#sigen_0_247_30007' style='font-size:small;'>Reactive Power</a><br>

<h6>Statistics</h6>
<a href='#sigen_0_247_30232' style='font-size:small;'>Total AC EV Charge Energy</a><br>
<a href='#sigen_0_247_30244' style='font-size:small;'>Total Charge Energy</a><br>
<a href='#sigen_0_247_30228' style='font-size:small;'>Total Common Load Consumption</a><br>
<a href='#sigen_0_247_30252' style='font-size:small;'>Total DC EV Charge Energy</a><br>
<a href='#sigen_0_247_30256' style='font-size:small;'>Total DC EV Discharge Energy</a><br>
<a href='#sigen_0_247_30248' style='font-size:small;'>Total Discharge Energy</a><br>
<a href='#sigen_0_247_30264' style='font-size:small;'>Total Exported Energy</a><br>
<a href='#sigen_0_247_30268' style='font-size:small;'>Total Generator Output Energy</a><br>
<a href='#sigen_0_247_30260' style='font-size:small;'>Total Imported Energy</a><br>
<a href='#sigen_0_247_30236' style='font-size:small;'>Total PV Production</a><br>
<a href='#sigen_0_247_30240' style='font-size:small;'>Total Third-Party PV Production</a><br>

<h6>Inverter</h6>
<a href='#sigen_0_001_31005' style='font-size:small;'>A-B Line Voltage</a><br>
<a href='#sigen_0_001_30587' style='font-size:small;'>Active Power</a><br>
<a href='#sigen_0_001_41501' style='font-size:small;'>Active Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_30613' style='font-size:small;'>Active Power Fixed Value Adjustment Feedback</a><br>
<a href='#sigen_0_001_41505' style='font-size:small;'>Active Power Percentage Adjustment</a><br>
<a href='#sigen_0_001_30617' style='font-size:small;'>Active Power Percentage Adjustment Feedback</a><br>
<a href='#sigen_0_001_31007' style='font-size:small;'>B-C Line Voltage</a><br>
<a href='#sigen_0_001_31009' style='font-size:small;'>C-A Line Voltage</a><br>
<a href='#sigen_0_inverter_1_daily_pv_energy' style='font-size:small;'>Daily Production</a><br>
<a href='#sigen_0_001_30525' style='font-size:small;'>Firmware Version</a><br>
<a href='#sigen_0_001_30608' style='font-size:small;'>Gateway Alarms</a><br>
<a href='#sigen_0_001_31002' style='font-size:small;'>Grid Frequency</a><br>
<a href='#sigen_0_001_31037' style='font-size:small;'>Insulation Resistance</a><br>
<a href='#sigen_0_inverter_1_lifetime_pv_energy' style='font-size:small;'>Lifetime Production</a><br>
<a href='#sigen_0_001_31026' style='font-size:small;'>MPTT Count</a><br>
<a href='#sigen_0_001_30546' style='font-size:small;'>Max Absorption Power</a><br>
<a href='#sigen_0_001_30544' style='font-size:small;'>Max Active Power</a><br>
<a href='#sigen_0_001_30579' style='font-size:small;'>Max Active Power Adjustment</a><br>
<a href='#sigen_0_001_30542' style='font-size:small;'>Max Rated Apparent Power</a><br>
<a href='#sigen_0_001_30583' style='font-size:small;'>Max Reactive Power Adjustment</a><br>
<a href='#sigen_0_001_30581' style='font-size:small;'>Min Active Power Adjustment</a><br>
<a href='#sigen_0_001_30585' style='font-size:small;'>Min Reactive Power Adjustment</a><br>
<a href='#sigen_0_001_30500' style='font-size:small;'>Model</a><br>
<a href='#sigen_0_001_31004' style='font-size:small;'>Output Type</a><br>
<a href='#sigen_0_001_31024' style='font-size:small;'>PACK/BCU Count</a><br>
<a href='#sigen_0_inverter_1_pcs_alarm' style='font-size:small;'>PCS Alarms</a><br>
<a href='#sigen_0_001_31035' style='font-size:small;'>PV Power</a><br>
<a href='#sigen_0_001_31025' style='font-size:small;'>PV String Count</a><br>
<a href='#sigen_0_001_31017' style='font-size:small;'>Phase A Current</a><br>
<a href='#sigen_0_001_31011' style='font-size:small;'>Phase A Voltage</a><br>
<a href='#sigen_0_001_31019' style='font-size:small;'>Phase B Current</a><br>
<a href='#sigen_0_001_31013' style='font-size:small;'>Phase B Voltage</a><br>
<a href='#sigen_0_001_31021' style='font-size:small;'>Phase C Current</a><br>
<a href='#sigen_0_001_31015' style='font-size:small;'>Phase C Voltage</a><br>
<a href='#sigen_0_001_31023' style='font-size:small;'>Power Factor</a><br>
<a href='#sigen_0_001_41507' style='font-size:small;'>Power Factor Adjustment</a><br>
<a href='#sigen_0_001_30619' style='font-size:small;'>Power Factor Adjustment Feedback</a><br>
<a href='#sigen_0_001_30540' style='font-size:small;'>Rated Active Power</a><br>
<a href='#sigen_0_001_31001' style='font-size:small;'>Rated Grid Frequency</a><br>
<a href='#sigen_0_001_31000' style='font-size:small;'>Rated Grid Voltage</a><br>
<a href='#sigen_0_001_30589' style='font-size:small;'>Reactive Power</a><br>
<a href='#sigen_0_001_41503' style='font-size:small;'>Reactive Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_30615' style='font-size:small;'>Reactive Power Fixed Value Adjustment Feedback</a><br>
<a href='#sigen_0_001_30618' style='font-size:small;'>Reactive Power Percentage Adjustment Feedback</a><br>
<a href='#sigen_0_001_41506' style='font-size:small;'>Reactive Power Q/S Adjustment</a><br>
<a href='#sigen_0_001_41500' style='font-size:small;'>Remote EMS Dispatch</a><br>
<a href='#sigen_0_001_30578' style='font-size:small;'>Running State</a><br>
<a href='#sigen_0_001_30515' style='font-size:small;'>Serial Number</a><br>
<a href='#sigen_0_001_31040' style='font-size:small;'>Shutdown Time</a><br>
<a href='#sigen_0_001_31038' style='font-size:small;'>Startup Time</a><br>
<a href='#sigen_0_001_31003' style='font-size:small;'>Temperature</a><br>

<h6>Energy Storage System</h6>
<a href='#sigen_0_001_30607' style='font-size:small;'>Alarms</a><br>
<a href='#sigen_0_001_30595' style='font-size:small;'>Available Charge Energy</a><br>
<a href='#sigen_0_001_30597' style='font-size:small;'>Available Discharge Energy</a><br>
<a href='#sigen_0_001_30603' style='font-size:small;'>Average Cell Temperature</a><br>
<a href='#sigen_0_001_30604' style='font-size:small;'>Average Cell Voltage</a><br>
<a href='#sigen_0_inverter_1_battery_charging_power' style='font-size:small;'>Battery Charging Power</a><br>
<a href='#sigen_0_inverter_1_battery_discharging_power' style='font-size:small;'>Battery Discharging Power</a><br>
<a href='#sigen_0_001_30599' style='font-size:small;'>Battery Power</a><br>
<a href='#sigen_0_001_30601' style='font-size:small;'>Battery SoC</a><br>
<a href='#sigen_0_001_30602' style='font-size:small;'>Battery SoH</a><br>
<a href='#sigen_0_001_30566' style='font-size:small;'>Daily Charge Energy</a><br>
<a href='#sigen_0_001_30572' style='font-size:small;'>Daily Discharge Energy</a><br>
<a href='#sigen_0_001_30568' style='font-size:small;'>Lifetime Charge Energy</a><br>
<a href='#sigen_0_001_30574' style='font-size:small;'>Lifetime Discharge Energy</a><br>
<a href='#sigen_0_001_30620' style='font-size:small;'>Max Battery Temperature</a><br>
<a href='#sigen_0_001_30591' style='font-size:small;'>Max Charge Power</a><br>
<a href='#sigen_0_001_30593' style='font-size:small;'>Max Discharge Power</a><br>
<a href='#sigen_0_001_30621' style='font-size:small;'>Min Battery Temperature</a><br>
<a href='#sigen_0_001_30548' style='font-size:small;'>Rated Battery Capacity</a><br>
<a href='#sigen_0_001_30550' style='font-size:small;'>Rated Charging Power</a><br>
<a href='#sigen_0_001_30552' style='font-size:small;'>Rated Discharging Power</a><br>

<h6>PV String</h6>
<a href='#sigen_0_001_31028' style='font-size:small;'>PV String 1 Current</a><br>
<a href='#sigen_0_001_31030' style='font-size:small;'>PV String 2 Current</a><br>
<a href='#sigen_0_001_31032' style='font-size:small;'>PV String 3 Current</a><br>
<a href='#sigen_0_001_31034' style='font-size:small;'>PV String 4 Current</a><br>
<a href='#sigen_0_001_31043' style='font-size:small;'>PV String 5 Current</a><br>
<a href='#sigen_0_001_31045' style='font-size:small;'>PV String 6 Current</a><br>
<a href='#sigen_0_001_31047' style='font-size:small;'>PV String 7 Current</a><br>
<a href='#sigen_0_001_31049' style='font-size:small;'>PV String 8 Current</a><br>
<a href='#sigen_0_001_31051' style='font-size:small;'>PV String 9 Current</a><br>
<a href='#sigen_0_001_31053' style='font-size:small;'>PV String 10 Current</a><br>
<a href='#sigen_0_001_31055' style='font-size:small;'>PV String 11 Current</a><br>
<a href='#sigen_0_001_31057' style='font-size:small;'>PV String 12 Current</a><br>
<a href='#sigen_0_001_31059' style='font-size:small;'>PV String 13 Current</a><br>
<a href='#sigen_0_001_31061' style='font-size:small;'>PV String 14 Current</a><br>
<a href='#sigen_0_001_31063' style='font-size:small;'>PV String 15 Current</a><br>
<a href='#sigen_0_001_31065' style='font-size:small;'>PV String 16 Current</a><br>
<a href='#sigen_0_inverter_1_pv1_daily_energy' style='font-size:small;'>PV String 1 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv2_daily_energy' style='font-size:small;'>PV String 2 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv3_daily_energy' style='font-size:small;'>PV String 3 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv4_daily_energy' style='font-size:small;'>PV String 4 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv5_daily_energy' style='font-size:small;'>PV String 5 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv6_daily_energy' style='font-size:small;'>PV String 6 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv7_daily_energy' style='font-size:small;'>PV String 7 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv8_daily_energy' style='font-size:small;'>PV String 8 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv9_daily_energy' style='font-size:small;'>PV String 9 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv10_daily_energy' style='font-size:small;'>PV String 10 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv11_daily_energy' style='font-size:small;'>PV String 11 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv12_daily_energy' style='font-size:small;'>PV String 12 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv13_daily_energy' style='font-size:small;'>PV String 13 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv14_daily_energy' style='font-size:small;'>PV String 14 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv15_daily_energy' style='font-size:small;'>PV String 15 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv16_daily_energy' style='font-size:small;'>PV String 16 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv1_lifetime_energy' style='font-size:small;'>PV String 1 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv2_lifetime_energy' style='font-size:small;'>PV String 2 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv3_lifetime_energy' style='font-size:small;'>PV String 3 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv4_lifetime_energy' style='font-size:small;'>PV String 4 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv5_lifetime_energy' style='font-size:small;'>PV String 5 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv6_lifetime_energy' style='font-size:small;'>PV String 6 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv7_lifetime_energy' style='font-size:small;'>PV String 7 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv8_lifetime_energy' style='font-size:small;'>PV String 8 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv9_lifetime_energy' style='font-size:small;'>PV String 9 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv10_lifetime_energy' style='font-size:small;'>PV String 10 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv11_lifetime_energy' style='font-size:small;'>PV String 11 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv12_lifetime_energy' style='font-size:small;'>PV String 12 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv13_lifetime_energy' style='font-size:small;'>PV String 13 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv14_lifetime_energy' style='font-size:small;'>PV String 14 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv15_lifetime_energy' style='font-size:small;'>PV String 15 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv16_lifetime_energy' style='font-size:small;'>PV String 16 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv1_power' style='font-size:small;'>PV String 1 Power</a><br>
<a href='#sigen_0_inverter_1_pv2_power' style='font-size:small;'>PV String 2 Power</a><br>
<a href='#sigen_0_inverter_1_pv3_power' style='font-size:small;'>PV String 3 Power</a><br>
<a href='#sigen_0_inverter_1_pv4_power' style='font-size:small;'>PV String 4 Power</a><br>
<a href='#sigen_0_inverter_1_pv5_power' style='font-size:small;'>PV String 5 Power</a><br>
<a href='#sigen_0_inverter_1_pv6_power' style='font-size:small;'>PV String 6 Power</a><br>
<a href='#sigen_0_inverter_1_pv7_power' style='font-size:small;'>PV String 7 Power</a><br>
<a href='#sigen_0_inverter_1_pv8_power' style='font-size:small;'>PV String 8 Power</a><br>
<a href='#sigen_0_inverter_1_pv9_power' style='font-size:small;'>PV String 9 Power</a><br>
<a href='#sigen_0_inverter_1_pv10_power' style='font-size:small;'>PV String 10 Power</a><br>
<a href='#sigen_0_inverter_1_pv11_power' style='font-size:small;'>PV String 11 Power</a><br>
<a href='#sigen_0_inverter_1_pv12_power' style='font-size:small;'>PV String 12 Power</a><br>
<a href='#sigen_0_inverter_1_pv13_power' style='font-size:small;'>PV String 13 Power</a><br>
<a href='#sigen_0_inverter_1_pv14_power' style='font-size:small;'>PV String 14 Power</a><br>
<a href='#sigen_0_inverter_1_pv15_power' style='font-size:small;'>PV String 15 Power</a><br>
<a href='#sigen_0_inverter_1_pv16_power' style='font-size:small;'>PV String 16 Power</a><br>
<a href='#sigen_0_001_31027' style='font-size:small;'>PV String 1 Voltage</a><br>
<a href='#sigen_0_001_31029' style='font-size:small;'>PV String 2 Voltage</a><br>
<a href='#sigen_0_001_31031' style='font-size:small;'>PV String 3 Voltage</a><br>
<a href='#sigen_0_001_31033' style='font-size:small;'>PV String 4 Voltage</a><br>
<a href='#sigen_0_001_31042' style='font-size:small;'>PV String 5 Voltage</a><br>
<a href='#sigen_0_001_31044' style='font-size:small;'>PV String 6 Voltage</a><br>
<a href='#sigen_0_001_31046' style='font-size:small;'>PV String 7 Voltage</a><br>
<a href='#sigen_0_001_31048' style='font-size:small;'>PV String 8 Voltage</a><br>
<a href='#sigen_0_001_31050' style='font-size:small;'>PV String 9 Voltage</a><br>
<a href='#sigen_0_001_31052' style='font-size:small;'>PV String 10 Voltage</a><br>
<a href='#sigen_0_001_31054' style='font-size:small;'>PV String 11 Voltage</a><br>
<a href='#sigen_0_001_31056' style='font-size:small;'>PV String 12 Voltage</a><br>
<a href='#sigen_0_001_31058' style='font-size:small;'>PV String 13 Voltage</a><br>
<a href='#sigen_0_001_31060' style='font-size:small;'>PV String 14 Voltage</a><br>
<a href='#sigen_0_001_31062' style='font-size:small;'>PV String 15 Voltage</a><br>
<a href='#sigen_0_001_31064' style='font-size:small;'>PV String 16 Voltage</a><br>

<h6>AC Charger</h6>
<a href='#sigen_0_ac_charger_2_alarm' style='font-size:small;'>Alarms</a><br>
<a href='#sigen_0_002_32003' style='font-size:small;'>Charging Power</a><br>
<a href='#sigen_0_002_32010' style='font-size:small;'>Input Breaker</a><br>
<a href='#sigen_0_002_42001' style='font-size:small;'>Output Current</a><br>
<a href='#sigen_0_002_32007' style='font-size:small;'>Rated Current</a><br>
<a href='#sigen_0_002_32005' style='font-size:small;'>Rated Power</a><br>
<a href='#sigen_0_002_32009' style='font-size:small;'>Rated Voltage</a><br>
<a href='#sigen_0_002_32000' style='font-size:small;'>Running State</a><br>
<a href='#sigen_0_002_32001' style='font-size:small;'>Total Energy Consumed</a><br>

<h6>DC Charger</h6>
<a href='#sigen_0_001_30609' style='font-size:small;'>Alarms</a><br>
<a href='#sigen_0_001_31505' style='font-size:small;'>Current Charging Capacity</a><br>
<a href='#sigen_0_001_31507' style='font-size:small;'>Current Charging Duration</a><br>
<a href='#sigen_0_001_31502' style='font-size:small;'>Output Power</a><br>
<a href='#sigen_0_001_31500' style='font-size:small;'>Vehicle Battery Voltage</a><br>
<a href='#sigen_0_001_31501' style='font-size:small;'>Vehicle Charging Current</a><br>
<a href='#sigen_0_001_31504' style='font-size:small;'>Vehicle SoC</a><br>

<h6>Smart-Port (Enphase Envoy only)</h6>
<a href='#sigen_0_enphase_123456789012_current' style='font-size:small;'>Current</a><br>
<a href='#sigen_0_enphase_123456789012_daily_pv_energy' style='font-size:small;'>Daily Production</a><br>
<a href='#sigen_0_enphase_123456789012_frequency' style='font-size:small;'>Frequency</a><br>
<a href='#sigen_0_enphase_123456789012_lifetime_pv_energy' style='font-size:small;'>Lifetime Production</a><br>
<a href='#sigen_0_enphase_123456789012_active_power' style='font-size:small;'>PV Power</a><br>
<a href='#sigen_0_enphase_123456789012_power_factor' style='font-size:small;'>Power Factor</a><br>
<a href='#sigen_0_enphase_123456789012_reactive_power' style='font-size:small;'>Reactive Power</a><br>
<a href='#sigen_0_enphase_123456789012_voltage' style='font-size:small;'>Voltage</a><br>

<h6>Metrics</h6>
<li><a href='#sigenergy2mqtt_modbus_locks'>Modbus Active Locks</a></li>
<li><a href='#sigenergy2mqtt_modbus_read_errors'>Modbus Read Errors</a></li>
<li><a href='#sigenergy2mqtt_modbus_read_max'>Modbus Read Max</a></li>
<li><a href='#sigenergy2mqtt_modbus_read_mean'>Modbus Read Mean</a></li>
<li><a href='#sigenergy2mqtt_modbus_read_min'>Modbus Read Min</a></li>
<li><a href='#sigenergy2mqtt_modbus_reads_sec'>Modbus Reads/second</a></li>
<li><a href='#sigenergy2mqtt_modbus_write_errors'>Modbus Write Errors</a></li>
<li><a href='#sigenergy2mqtt_modbus_write_max'>Modbus Write Max</a></li>
<li><a href='#sigenergy2mqtt_modbus_write_mean'>Modbus Write Mean</a></li>
<li><a href='#sigenergy2mqtt_modbus_write_min'>Modbus Write Min</a></li>
<li><a href='#sigenergy2mqtt_modbus_protocol_published'>Protocol Published</a></li>
<li><a href='#sigenergy2mqtt_modbus_protocol'>Protocol Version</a></li>
<li><a href='#sigenergy2mqtt_started'>Started</a></li>
</td><td style='vertical-align: top;'>

<h6>Plant</h6>
<a href='#sigen_0_247_40001' style='font-size:small;'>Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40005' style='font-size:small;'>Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40046' style='font-size:small;'>Backup SoC</a><br>
<a href='#sigen_0_247_40047' style='font-size:small;'>Charge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40048' style='font-size:small;'>Discharge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40038' style='font-size:small;'>Grid Max Export Limit</a><br>
<a href='#sigen_0_247_40040' style='font-size:small;'>Grid Max Import Limit</a><br>
<a href='#sigen_0_247_40030' style='font-size:small;'>Independent Phase Power Control</a><br>
<a href='#sigen_0_247_40032' style='font-size:small;'>Max Charging Limit</a><br>
<a href='#sigen_0_247_40034' style='font-size:small;'>Max Discharging Limit</a><br>
<a href='#sigen_0_247_40042' style='font-size:small;'>PCS Max Export Limit</a><br>
<a href='#sigen_0_247_40044' style='font-size:small;'>PCS Max Import Limit</a><br>
<a href='#sigen_0_247_40036' style='font-size:small;'>PV Max Power Limit</a><br>
<a href='#sigen_0_247_40008' style='font-size:small;'>Phase A Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40020' style='font-size:small;'>Phase A Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40023' style='font-size:small;'>Phase A Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40014' style='font-size:small;'>Phase A Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40010' style='font-size:small;'>Phase B Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40021' style='font-size:small;'>Phase B Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40024' style='font-size:small;'>Phase B Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40016' style='font-size:small;'>Phase B Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40012' style='font-size:small;'>Phase C Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40022' style='font-size:small;'>Phase C Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40025' style='font-size:small;'>Phase C Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40018' style='font-size:small;'>Phase C Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40000' style='font-size:small;'>Power</a><br>
<a href='#sigen_0_247_40007' style='font-size:small;'>Power Factor Adjustment Target Value</a><br>
<a href='#sigen_0_247_40006' style='font-size:small;'>Q/S Adjustment Target Value</a><br>
<a href='#sigen_0_247_40003' style='font-size:small;'>Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40029' style='font-size:small;'>Remote EMS</a><br>
<a href='#sigen_0_247_40031' style='font-size:small;'>Remote EMS Control Mode</a><br>

<h6>Inverter</h6>
<a href='#sigen_0_001_41501' style='font-size:small;'>Active Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_41505' style='font-size:small;'>Active Power Percentage Adjustment</a><br>
<a href='#sigen_0_001_40500' style='font-size:small;'>Power</a><br>
<a href='#sigen_0_001_41507' style='font-size:small;'>Power Factor Adjustment</a><br>
<a href='#sigen_0_001_41503' style='font-size:small;'>Reactive Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_41506' style='font-size:small;'>Reactive Power Q/S Adjustment</a><br>
<a href='#sigen_0_001_41500' style='font-size:small;'>Remote EMS Dispatch</a><br>

<h6>AC Charger</h6>
<a href='#sigen_0_002_42000' style='font-size:small;'>AC Charger Stop/Start</a><br>
<a href='#sigen_0_002_42001' style='font-size:small;'>Output Current</a><br>

<h6>DC Charger</h6>
<a href='#sigen_0_001_41000' style='font-size:small;'>DC Charger Stop/Start</a><br>
</td></tr>
</table>

## Published Topics

### Plant
<h5><a id='sigen_0_247_30031'>Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantActivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power/state</td></tr>
<tr><td>Source</td><td>30031</td></tr>
</table>
<h5><a id='sigen_0_247_40001'>Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>ActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40001</td></tr>
</table>
<h5><a id='sigen_0_247_40005'>Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>ActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40005</td></tr>
<tr><td>Comment</td><td>Range: [-100.00,100.00]</td></tr>
</table>
<h5><a id='sigen_0_247_30039'>Available Max Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMaxActivePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_max_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_active_power/state</td></tr>
<tr><td>Source</td><td>30039</td></tr>
<tr><td>Comment</td><td>Feed to the AC terminal. Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_30064'>Available Max Charging Capacity</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMaxChargingCapacity</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_max_charging_capacity</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_charging_capacity/state</td></tr>
<tr><td>Source</td><td>30064</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_30047'>Available Max Charging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMaxChargingPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_max_charging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_charging_power/state</td></tr>
<tr><td>Source</td><td>30047</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_30066'>Available Max Discharging Capacity</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMaxDischargingCapacity</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_max_discharging_capacity</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_discharging_capacity/state</td></tr>
<tr><td>Source</td><td>30066</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_30049'>Available Max Discharging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMaxDischargingPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_max_discharging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_discharging_power/state</td></tr>
<tr><td>Source</td><td>30049</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_30043'>Available Max Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMaxReactivePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_max_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_reactive_power/state</td></tr>
<tr><td>Source</td><td>30043</td></tr>
<tr><td>Comment</td><td>Feed to the AC terminal. Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_30041'>Available Min Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMinActivePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_min_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_min_active_power/state</td></tr>
<tr><td>Source</td><td>30041</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_30045'>Available Min Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableMinReactivePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_available_min_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_min_reactive_power/state</td></tr>
<tr><td>Source</td><td>30045</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
</table>
<h5><a id='sigen_0_247_40046'>Backup SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>ESSBackupSOC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_ess_backup_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Source</td><td>40046</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
</table>
<h5><a id='sigen_0_battery_charging_power'>Battery Charging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>BatteryChargingPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_battery_charging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_battery_charging_power/state</td></tr>
<tr><td>Source</td><td>BatteryPower &gt; 0</td></tr>
</table>
<h5><a id='sigen_0_battery_discharging_power'>Battery Discharging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>BatteryDischargingPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_battery_discharging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_battery_discharging_power/state</td></tr>
<tr><td>Source</td><td>BatteryPower &lt; 0</td></tr>
</table>
<h5><a id='sigen_0_247_30037'>Battery Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>BatteryPower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_battery_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_power/state</td></tr>
<tr><td>Source</td><td>30037</td></tr>
<tr><td>Comment</td><td>ESS Power: <0 = discharging >0 = charging</td></tr>
</table>
<h5><a id='sigen_0_247_30014'>Battery SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantBatterySoC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_battery_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_soc/state</td></tr>
<tr><td>Source</td><td>30014</td></tr>
</table>
<h5><a id='sigen_0_247_30087'>Battery SoH</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantBatterySoH</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_battery_soh</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soh/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_soh/state</td></tr>
<tr><td>Source</td><td>30087</td></tr>
<tr><td>Comment</td><td>This value is the weighted average of the SOH of all ESS devices in the power plant, with each rated capacity as the weight</td></tr>
</table>
<h5><a id='sigen_0_247_30085'>Charge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>ChargeCutOffSoC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_charge_cut_off_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_charge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>30085</td></tr>
</table>
<h5><a id='sigen_0_247_40047'>Charge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>ESSChargeCutOffSOC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_ess_charge_cut_off_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>40047</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
</table>
<h5><a id='sigen_0_consumed_power'>Consumed Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantConsumedPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_consumed_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_consumed_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_consumed_power/state</td></tr>
<tr><td>Source</td><td>TotalPVPower &plus; GridSensorActivePower &minus; BatteryPower &minus; ACChargerChargingPower &minus; DCChargerOutputPower</td></tr>
</table>
<h5><a id='sigen_0_247_30072'>DC Charger Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>GeneralAlarm5</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_general_alarm_5</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_5/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_5/state</td></tr>
<tr><td>Source</td><td>30072</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
<h5><a id='sigen_0_daily_charge_energy'>Daily Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantDailyChargeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_daily_charge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_charge_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of DailyChargeEnergy across all Inverters associated with the Plant</td></tr>
</table>
<h5><a id='sigen_0_daily_consumed_energy'>Daily Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>TotalLoadDailyConsumption</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_daily_consumed_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_consumed_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_consumed_energy/state</td></tr>
<tr><td>Source</td><td>30092</td></tr>
</table>
<h5><a id='sigen_0_daily_discharge_energy'>Daily Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantDailyDischargeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_daily_discharge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_discharge_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of DailyDischargeEnergy across all Inverters associated with the Plant</td></tr>
</table>
<h5><a id='sigen_0_daily_pv_energy'>Daily PV Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantDailyPVEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_daily_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight</td></tr>
</table>
<h5><a id='sigen_0_total_daily_pv_energy'>Daily Total PV Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>TotalDailyPVEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_total_daily_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_total_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>TotalLifetimePVEnergy &minus; TotalLifetimePVEnergy at last midnight</td></tr>
</table>
<h5><a id='sigen_0_247_30086'>Discharge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>DischargeCutOffSoC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_discharge_cut_off_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_discharge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>30086</td></tr>
</table>
<h5><a id='sigen_0_247_40048'>Discharge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>ESSDischargeCutOffSOC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_ess_discharge_cut_off_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>40048</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
</table>
<h5><a id='sigen_0_247_30003'>EMS Work Mode</a></h5>
<table>
<tr><td>Sensor Class</td><td>EMSWorkMode</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_ems_work_mode</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_ems_work_mode/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ems_work_mode/state</td></tr>
<tr><td>Source</td><td>30003</td></tr>
</table>
<h5><a id='sigen_0_247_30029'>ESS Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>GeneralAlarm3</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_general_alarm_3</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_3/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_3/state</td></tr>
<tr><td>Source</td><td>30029</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
<h5><a id='sigen_0_247_30030'>Gateway Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>GeneralAlarm4</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_general_alarm_4</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_4/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_4/state</td></tr>
<tr><td>Source</td><td>30030</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
<h5><a id='sigen_0_247_40038'>Grid Max Export Limit</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridMaxExportLimit</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_max_export_limit</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Source</td><td>40038</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
<h5><a id='sigen_0_247_40040'>Grid Max Import Limit</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridMaxImportLimit</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_max_import_limit</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Source</td><td>40040</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
<h5><a id='sigen_0_247_40030'>Independent Phase Power Control</a></h5>
<table>
<tr><td>Sensor Class</td><td>IndependentPhasePowerControl</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_independent_phase_power_control</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Source</td><td>40030</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled</td></tr>
</table>
<h5><a id='sigen_0_accumulated_charge_energy'>Lifetime Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>ESSTotalChargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_accumulated_charge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_accumulated_charge_energy/state</td></tr>
<tr><td>Source</td><td>30200</td></tr>
</table>
<h5><a id='sigen_0_lifetime_consumed_energy'>Lifetime Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>TotalLoadConsumption</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_lifetime_consumed_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_consumed_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_lifetime_consumed_energy/state</td></tr>
<tr><td>Source</td><td>30094</td></tr>
</table>
<h5><a id='sigen_0_247_30208'>Lifetime DC EV Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>EVDCTotalChargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_evdc_total_charge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_evdc_total_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_evdc_total_charge_energy/state</td></tr>
<tr><td>Source</td><td>30208</td></tr>
</table>
<h5><a id='sigen_0_247_30212'>Lifetime DC EV Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>EVDCTotalDischargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_evdc_total_discharge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_evdc_total_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_evdc_total_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30212</td></tr>
</table>
<h5><a id='sigen_0_accumulated_discharge_energy'>Lifetime Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>ESSTotalDischargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_accumulated_discharge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_accumulated_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30204</td></tr>
</table>
<h5><a id='sigen_0_247_30224'>Lifetime Generator Output Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantTotalGeneratorOutputEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_total_generator_output_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_total_generator_output_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_total_generator_output_energy/state</td></tr>
<tr><td>Source</td><td>30224</td></tr>
</table>
<h5><a id='sigen_0_247_30088'>Lifetime PV Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPVTotalGeneration</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_lifetime_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>30088</td></tr>
</table>
<h5><a id='sigen_0_247_30196'>Lifetime Third-Party PV Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>ThirdPartyLifetimePVEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_third_party_pv_lifetime_production</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_third_party_pv_lifetime_production/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_third_party_pv_lifetime_production/state</td></tr>
<tr><td>Source</td><td>30196</td></tr>
</table>
<h5><a id='sigen_0_lifetime_pv_energy'>Lifetime Total PV Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>TotalLifetimePVEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_lifetime_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of PlantPVTotalGeneration and ThirdPartyLifetimePVEnergy</td></tr>
</table>
<h5><a id='sigen_0_247_30010'>Max Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxActivePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_max_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_active_power/state</td></tr>
<tr><td>Source</td><td>30010</td></tr>
<tr><td>Comment</td><td>This should be the base value of all active power adjustment actions</td></tr>
</table>
<h5><a id='sigen_0_247_30012'>Max Apparent Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxApparentPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_max_apparent_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_apparent_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_apparent_power/state</td></tr>
<tr><td>Source</td><td>30012</td></tr>
<tr><td>Comment</td><td>This should be the base value of all reactive power adjustment actions</td></tr>
</table>
<h5><a id='sigen_0_247_40032'>Max Charging Limit</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxChargingLimit</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_max_charging_limit</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Source</td><td>40032</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Charging</td></tr>
</table>
<h5><a id='sigen_0_247_40034'>Max Discharging Limit</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxDischargingLimit</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_max_discharging_limit</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Source</td><td>40034</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Discharging</td></tr>
</table>
<h5><a id='sigen_0_general_pcs_alarm'>PCS Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>GeneralPCSAlarm</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_general_pcs_alarm</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_pcs_alarm/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_general_pcs_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 30027 and 30028</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
</table>
<h5><a id='sigen_0_247_40042'>PCS Max Export Limit</a></h5>
<table>
<tr><td>Sensor Class</td><td>PCSMaxExportLimit</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_pcs_max_export_limit</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Source</td><td>40042</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
</table>
<h5><a id='sigen_0_247_40044'>PCS Max Import Limit</a></h5>
<table>
<tr><td>Sensor Class</td><td>PCSMaxImportLimit</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_pcs_max_import_limit</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Source</td><td>40044</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
</table>
<h5><a id='sigen_0_247_40036'>PV Max Power Limit</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVMaxPowerLimit</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_pv_max_power_limit</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Source</td><td>40036</td></tr>
<tr><td>Comment</td><td>Takes effect when Remote EMS control mode (40031) is set to Command Charging/Discharging</td></tr>
</table>
<h5><a id='sigen_0_247_30035'>PV Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPVPower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_pv_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_power/state</td></tr>
<tr><td>Source</td><td>30035</td></tr>
</table>
<h5><a id='sigen_0_247_30015'>Phase A Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPhaseActivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_a_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power/state</td></tr>
<tr><td>Source</td><td>30015</td></tr>
</table>
<h5><a id='sigen_0_247_40008'>Phase A Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40008</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
<h5><a id='sigen_0_247_40020'>Phase A Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40020</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
</table>
<h5><a id='sigen_0_247_40023'>Phase A Q/S Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseQSAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40023</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
</table>
<h5><a id='sigen_0_247_30021'>Phase A Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPhaseReactivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_a_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power/state</td></tr>
<tr><td>Source</td><td>30021</td></tr>
</table>
<h5><a id='sigen_0_247_40014'>Phase A Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40014</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
<h5><a id='sigen_0_247_30017'>Phase B Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPhaseActivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_b_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power/state</td></tr>
<tr><td>Source</td><td>30017</td></tr>
</table>
<h5><a id='sigen_0_247_40010'>Phase B Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40010</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
<h5><a id='sigen_0_247_40021'>Phase B Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40021</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
</table>
<h5><a id='sigen_0_247_40024'>Phase B Q/S Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseQSAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40024</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
</table>
<h5><a id='sigen_0_247_30023'>Phase B Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPhaseReactivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_b_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power/state</td></tr>
<tr><td>Source</td><td>30023</td></tr>
</table>
<h5><a id='sigen_0_247_40016'>Phase B Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40016</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
<h5><a id='sigen_0_247_30019'>Phase C Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPhaseActivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_c_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power/state</td></tr>
<tr><td>Source</td><td>30019</td></tr>
</table>
<h5><a id='sigen_0_247_40012'>Phase C Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40012</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
<h5><a id='sigen_0_247_40022'>Phase C Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40022</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
</table>
<h5><a id='sigen_0_247_40025'>Phase C Q/S Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseQSAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40025</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
</table>
<h5><a id='sigen_0_247_30025'>Phase C Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantPhaseReactivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_c_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power/state</td></tr>
<tr><td>Source</td><td>30025</td></tr>
</table>
<h5><a id='sigen_0_247_40018'>Phase C Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40018</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
</table>
<h5><a id='sigen_0_247_40007'>Power Factor Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>PowerFactorAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_power_factor_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40007</td></tr>
<tr><td>Comment</td><td>Range: (-1, -0.8] U [0.8, 1]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
<h5><a id='sigen_0_247_40006'>Q/S Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>QSAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_q_s_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40006</td></tr>
<tr><td>Comment</td><td>Range: [-60.0,60.00]. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
<h5><a id='sigen_0_247_30068'>Rated Charging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantRatedChargingPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_rated_charging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>30068</td></tr>
</table>
<h5><a id='sigen_0_247_30070'>Rated Discharging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantRatedDischargingPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_rated_discharging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_discharging_power/state</td></tr>
<tr><td>Source</td><td>30070</td></tr>
</table>
<h5><a id='sigen_0_247_30083'>Rated Energy Capacity</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantRatedEnergyCapacity</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_rated_energy_capacity</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_energy_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_energy_capacity/state</td></tr>
<tr><td>Source</td><td>30083</td></tr>
</table>
<h5><a id='sigen_0_247_30033'>Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantReactivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power/state</td></tr>
<tr><td>Source</td><td>30033</td></tr>
</table>
<h5><a id='sigen_0_247_40003'>Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor Class</td><td>ReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40003</td></tr>
<tr><td>Comment</td><td>Range: [-60.00 * base value ,60.00 * base value]. Takes effect globally regardless of the EMS operating mode</td></tr>
</table>
<h5><a id='sigen_0_247_40029'>Remote EMS</a></h5>
<table>
<tr><td>Sensor Class</td><td>RemoteEMS</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_remote_ems</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Source</td><td>40029</td></tr>
<tr><td>Comment</td><td>When needed to control EMS remotely, this register needs to be enabled. When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS</td></tr>
</table>
<h5><a id='sigen_0_247_40031'>Remote EMS Control Mode</a></h5>
<table>
<tr><td>Sensor Class</td><td>RemoteEMSControlMode</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_remote_ems_control_mode</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/select/sigen_0_247_powerplant/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Source</td><td>40031</td></tr>
</table>
<h5><a id='sigen_0_247_30051'>Running State</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantRunningState</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_running_state</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_running_state/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_running_state/state</td></tr>
<tr><td>Source</td><td>30051</td></tr>
</table>
<h5><a id='sigen_0_247_30146'>Smart Load 01 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_01_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_01_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_01_power/state</td></tr>
<tr><td>Source</td><td>30146</td></tr>
</table>
<h5><a id='sigen_0_247_30098'>Smart Load 01 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_01_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_01_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_01_total_consumption/state</td></tr>
<tr><td>Source</td><td>30098</td></tr>
</table>
<h5><a id='sigen_0_247_30148'>Smart Load 02 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_02_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_02_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_02_power/state</td></tr>
<tr><td>Source</td><td>30148</td></tr>
</table>
<h5><a id='sigen_0_247_30100'>Smart Load 02 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_02_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_02_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_02_total_consumption/state</td></tr>
<tr><td>Source</td><td>30100</td></tr>
</table>
<h5><a id='sigen_0_247_30150'>Smart Load 03 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_03_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_03_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_03_power/state</td></tr>
<tr><td>Source</td><td>30150</td></tr>
</table>
<h5><a id='sigen_0_247_30102'>Smart Load 03 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_03_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_03_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_03_total_consumption/state</td></tr>
<tr><td>Source</td><td>30102</td></tr>
</table>
<h5><a id='sigen_0_247_30152'>Smart Load 04 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_04_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_04_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_04_power/state</td></tr>
<tr><td>Source</td><td>30152</td></tr>
</table>
<h5><a id='sigen_0_247_30104'>Smart Load 04 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_04_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_04_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_04_total_consumption/state</td></tr>
<tr><td>Source</td><td>30104</td></tr>
</table>
<h5><a id='sigen_0_247_30154'>Smart Load 05 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_05_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_05_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_05_power/state</td></tr>
<tr><td>Source</td><td>30154</td></tr>
</table>
<h5><a id='sigen_0_247_30106'>Smart Load 05 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_05_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_05_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_05_total_consumption/state</td></tr>
<tr><td>Source</td><td>30106</td></tr>
</table>
<h5><a id='sigen_0_247_30156'>Smart Load 06 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_06_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_06_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_06_power/state</td></tr>
<tr><td>Source</td><td>30156</td></tr>
</table>
<h5><a id='sigen_0_247_30108'>Smart Load 06 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_06_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_06_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_06_total_consumption/state</td></tr>
<tr><td>Source</td><td>30108</td></tr>
</table>
<h5><a id='sigen_0_247_30158'>Smart Load 07 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_07_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_07_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_07_power/state</td></tr>
<tr><td>Source</td><td>30158</td></tr>
</table>
<h5><a id='sigen_0_247_30110'>Smart Load 07 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_07_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_07_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_07_total_consumption/state</td></tr>
<tr><td>Source</td><td>30110</td></tr>
</table>
<h5><a id='sigen_0_247_30160'>Smart Load 08 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_08_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_08_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_08_power/state</td></tr>
<tr><td>Source</td><td>30160</td></tr>
</table>
<h5><a id='sigen_0_247_30112'>Smart Load 08 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_08_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_08_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_08_total_consumption/state</td></tr>
<tr><td>Source</td><td>30112</td></tr>
</table>
<h5><a id='sigen_0_247_30162'>Smart Load 09 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_09_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_09_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_09_power/state</td></tr>
<tr><td>Source</td><td>30162</td></tr>
</table>
<h5><a id='sigen_0_247_30114'>Smart Load 09 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_09_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_09_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_09_total_consumption/state</td></tr>
<tr><td>Source</td><td>30114</td></tr>
</table>
<h5><a id='sigen_0_247_30164'>Smart Load 10 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_10_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_10_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_10_power/state</td></tr>
<tr><td>Source</td><td>30164</td></tr>
</table>
<h5><a id='sigen_0_247_30116'>Smart Load 10 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_10_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_10_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_10_total_consumption/state</td></tr>
<tr><td>Source</td><td>30116</td></tr>
</table>
<h5><a id='sigen_0_247_30166'>Smart Load 11 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_11_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_11_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_11_power/state</td></tr>
<tr><td>Source</td><td>30166</td></tr>
</table>
<h5><a id='sigen_0_247_30118'>Smart Load 11 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_11_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_11_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_11_total_consumption/state</td></tr>
<tr><td>Source</td><td>30118</td></tr>
</table>
<h5><a id='sigen_0_247_30168'>Smart Load 12 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_12_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_12_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_12_power/state</td></tr>
<tr><td>Source</td><td>30168</td></tr>
</table>
<h5><a id='sigen_0_247_30120'>Smart Load 12 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_12_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_12_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_12_total_consumption/state</td></tr>
<tr><td>Source</td><td>30120</td></tr>
</table>
<h5><a id='sigen_0_247_30170'>Smart Load 13 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_13_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_13_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_13_power/state</td></tr>
<tr><td>Source</td><td>30170</td></tr>
</table>
<h5><a id='sigen_0_247_30122'>Smart Load 13 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_13_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_13_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_13_total_consumption/state</td></tr>
<tr><td>Source</td><td>30122</td></tr>
</table>
<h5><a id='sigen_0_247_30172'>Smart Load 14 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_14_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_14_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_14_power/state</td></tr>
<tr><td>Source</td><td>30172</td></tr>
</table>
<h5><a id='sigen_0_247_30124'>Smart Load 14 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_14_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_14_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_14_total_consumption/state</td></tr>
<tr><td>Source</td><td>30124</td></tr>
</table>
<h5><a id='sigen_0_247_30174'>Smart Load 15 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_15_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_15_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_15_power/state</td></tr>
<tr><td>Source</td><td>30174</td></tr>
</table>
<h5><a id='sigen_0_247_30126'>Smart Load 15 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_15_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_15_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_15_total_consumption/state</td></tr>
<tr><td>Source</td><td>30126</td></tr>
</table>
<h5><a id='sigen_0_247_30176'>Smart Load 16 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_16_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_16_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_16_power/state</td></tr>
<tr><td>Source</td><td>30176</td></tr>
</table>
<h5><a id='sigen_0_247_30128'>Smart Load 16 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_16_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_16_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_16_total_consumption/state</td></tr>
<tr><td>Source</td><td>30128</td></tr>
</table>
<h5><a id='sigen_0_247_30178'>Smart Load 17 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_17_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_17_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_17_power/state</td></tr>
<tr><td>Source</td><td>30178</td></tr>
</table>
<h5><a id='sigen_0_247_30130'>Smart Load 17 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_17_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_17_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_17_total_consumption/state</td></tr>
<tr><td>Source</td><td>30130</td></tr>
</table>
<h5><a id='sigen_0_247_30180'>Smart Load 18 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_18_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_18_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_18_power/state</td></tr>
<tr><td>Source</td><td>30180</td></tr>
</table>
<h5><a id='sigen_0_247_30132'>Smart Load 18 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_18_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_18_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_18_total_consumption/state</td></tr>
<tr><td>Source</td><td>30132</td></tr>
</table>
<h5><a id='sigen_0_247_30182'>Smart Load 19 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_19_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_19_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_19_power/state</td></tr>
<tr><td>Source</td><td>30182</td></tr>
</table>
<h5><a id='sigen_0_247_30134'>Smart Load 19 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_19_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_19_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_19_total_consumption/state</td></tr>
<tr><td>Source</td><td>30134</td></tr>
</table>
<h5><a id='sigen_0_247_30184'>Smart Load 20 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_20_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_20_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_20_power/state</td></tr>
<tr><td>Source</td><td>30184</td></tr>
</table>
<h5><a id='sigen_0_247_30136'>Smart Load 20 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_20_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_20_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_20_total_consumption/state</td></tr>
<tr><td>Source</td><td>30136</td></tr>
</table>
<h5><a id='sigen_0_247_30186'>Smart Load 21 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_21_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_21_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_21_power/state</td></tr>
<tr><td>Source</td><td>30186</td></tr>
</table>
<h5><a id='sigen_0_247_30138'>Smart Load 21 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_21_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_21_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_21_total_consumption/state</td></tr>
<tr><td>Source</td><td>30138</td></tr>
</table>
<h5><a id='sigen_0_247_30188'>Smart Load 22 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_22_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_22_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_22_power/state</td></tr>
<tr><td>Source</td><td>30188</td></tr>
</table>
<h5><a id='sigen_0_247_30140'>Smart Load 22 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_22_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_22_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_22_total_consumption/state</td></tr>
<tr><td>Source</td><td>30140</td></tr>
</table>
<h5><a id='sigen_0_247_30190'>Smart Load 23 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_23_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_23_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_23_power/state</td></tr>
<tr><td>Source</td><td>30190</td></tr>
</table>
<h5><a id='sigen_0_247_30142'>Smart Load 23 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_23_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_23_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_23_total_consumption/state</td></tr>
<tr><td>Source</td><td>30142</td></tr>
</table>
<h5><a id='sigen_0_247_30192'>Smart Load 24 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_24_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_24_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_24_power/state</td></tr>
<tr><td>Source</td><td>30192</td></tr>
</table>
<h5><a id='sigen_0_247_30144'>Smart Load 24 Total Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_smart_load_24_total_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_24_total_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_24_total_consumption/state</td></tr>
<tr><td>Source</td><td>30144</td></tr>
</table>
<h5><a id='sigen_0_247_30000'>System Time</a></h5>
<table>
<tr><td>Sensor Class</td><td>SystemTime</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_system_time</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_system_time/state</td></tr>
<tr><td>Source</td><td>30000</td></tr>
</table>
<h5><a id='sigen_0_247_30002'>System Time Zone</a></h5>
<table>
<tr><td>Sensor Class</td><td>SystemTimeZone</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_system_time_zone</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time_zone/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_system_time_zone/state</td></tr>
<tr><td>Source</td><td>30002</td></tr>
</table>
<h5><a id='sigen_0_247_30194'>Third-Party PV Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>ThirdPartyPVPower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_third_party_pv_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_third_party_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_third_party_pv_power/state</td></tr>
<tr><td>Source</td><td>30194</td></tr>
</table>
<h5><a id='sigen_0_total_pv_power'>Total PV Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>TotalPVPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_total_pv_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_total_pv_power/state</td></tr>
<tr><td>Source</td><td>PV Power + (sum of all Smart-Port PV Power sensors)</td></tr>
</table>

#### Grid Sensor
<h5><a id='sigen_0_247_30005'>Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridSensorActivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_sensor_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_active_power/state</td></tr>
<tr><td>Source</td><td>30005</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_daily_export_energy'>Daily Exported Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridSensorDailyExportEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_grid_sensor_daily_export_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_export_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_daily_export_energy/state</td></tr>
<tr><td>Source</td><td>PlantTotalExportedEnergy &minus; PlantTotalExportedEnergy at last midnight</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_daily_import_energy'>Daily Imported Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridSensorDailyImportEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_grid_sensor_daily_import_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_import_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_daily_import_energy/state</td></tr>
<tr><td>Source</td><td>PlantTotalImportedEnergy &minus; PlantTotalImportedEnergy at last midnight</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_export_power'>Export Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridSensorExportPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_grid_sensor_export_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_export_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_export_power/state</td></tr>
<tr><td>Source</td><td>GridSensorActivePower &lt; 0 &times; -1</td></tr>
</table>
<h5><a id='sigen_0_247_30004'>Grid Sensor Status</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridSensorStatus</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_sensor_status</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_status/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_status/state</td></tr>
<tr><td>Source</td><td>30004</td></tr>
<tr><td>Comment</td><td>Gateway or meter connection status</td></tr>
</table>
<h5><a id='sigen_0_247_30009'>Grid Status</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridStatus</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_status</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_status/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_status/state</td></tr>
<tr><td>Source</td><td>30009</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_import_power'>Import Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridSensorImportPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_grid_sensor_import_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_import_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_import_power/state</td></tr>
<tr><td>Source</td><td>GridSensorActivePower &gt; 0</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_lifetime_export_energy'>Lifetime Exported Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantTotalExportedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_grid_sensor_lifetime_export_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_export_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_lifetime_export_energy/state</td></tr>
<tr><td>Source</td><td>30220</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_lifetime_import_energy'>Lifetime Imported Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>PlantTotalImportedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_grid_sensor_lifetime_import_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_import_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_lifetime_import_energy/state</td></tr>
<tr><td>Source</td><td>30216</td></tr>
</table>
<h5><a id='sigen_0_247_30052'>Phase A Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridPhaseAActivePower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_phase_a_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_a_active_power/state</td></tr>
<tr><td>Source</td><td>30052</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
<h5><a id='sigen_0_247_30058'>Phase A Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridPhaseAReactivePower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_phase_a_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_a_reactive_power/state</td></tr>
<tr><td>Source</td><td>30058</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>
<h5><a id='sigen_0_247_30054'>Phase B Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridPhaseBActivePower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_phase_b_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_b_active_power/state</td></tr>
<tr><td>Source</td><td>30054</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
<h5><a id='sigen_0_247_30060'>Phase B Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridPhaseBReactivePower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_phase_b_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_b_reactive_power/state</td></tr>
<tr><td>Source</td><td>30060</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>
<h5><a id='sigen_0_247_30056'>Phase C Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridPhaseCActivePower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_phase_c_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_c_active_power/state</td></tr>
<tr><td>Source</td><td>30056</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
</table>
<h5><a id='sigen_0_247_30062'>Phase C Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridPhaseCReactivePower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_phase_c_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_c_reactive_power/state</td></tr>
<tr><td>Source</td><td>30062</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>
<h5><a id='sigen_0_247_30007'>Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridSensorReactivePower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>var</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_grid_sensor_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_reactive_power/state</td></tr>
<tr><td>Source</td><td>30007</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
</table>

#### Statistics
<h5><a id='sigen_0_247_30232'>Total AC EV Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalEVACChargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_ev_ac_charged_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_ev_ac_charged_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_ev_ac_charged_energy/state</td></tr>
<tr><td>Source</td><td>30232</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30244'>Total Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalChargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_charged_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_charged_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_charged_energy/state</td></tr>
<tr><td>Source</td><td>30244</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30228'>Total Common Load Consumption</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalCommonLoadConsumption</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_common_load_consumption</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_common_load_consumption/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_common_load_consumption/state</td></tr>
<tr><td>Source</td><td>30228</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30252'>Total DC EV Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalEVDCChargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_evdc_total_charge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_evdc_total_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_evdc_total_charge_energy/state</td></tr>
<tr><td>Source</td><td>30252</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30256'>Total DC EV Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalEVDCDischargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_evdc_total_discharge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_evdc_total_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_evdc_total_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30256</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30248'>Total Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalDischargedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_discharged_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_discharged_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_discharged_energy/state</td></tr>
<tr><td>Source</td><td>30248</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30264'>Total Exported Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalExportedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_exported_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_exported_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_exported_energy/state</td></tr>
<tr><td>Source</td><td>30264</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30268'>Total Generator Output Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalGeneratorOutputEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_generator_output_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_generator_output_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_generator_output_energy/state</td></tr>
<tr><td>Source</td><td>30268</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30260'>Total Imported Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalImportedEnergy</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_imported_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_imported_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_imported_energy/state</td></tr>
<tr><td>Source</td><td>30260</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30236'>Total PV Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalSelfPVGeneration</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_self_pv_generation</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_self_pv_generation/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_self_pv_generation/state</td></tr>
<tr><td>Source</td><td>30236</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>
<h5><a id='sigen_0_247_30240'>Total Third-Party PV Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>SITotalThirdPartyPVGeneration</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_si_total_third_party_pv_generation</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_third_party_pv_generation/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_si_total_third_party_pv_generation/state</td></tr>
<tr><td>Source</td><td>30240</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
</table>

### Inverter
<h5><a id='sigen_0_001_31005'>A-B Line Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>LineVoltage</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_a_b_line_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_a_b_line_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_a_b_line_voltage/state</td></tr>
<tr><td>Source</td><td>31005</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30587'>Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>ActivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power/state</td></tr>
<tr><td>Source</td><td>30587</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_41501'>Active Power Fixed Value Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterActivePowerFixedValueAdjustment</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_active_power_fixed_value_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Source</td><td>41501</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30613'>Active Power Fixed Value Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterActivePowerFixedValueAdjustmentFeedback</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30613</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_41505'>Active Power Percentage Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterActivePowerPercentageAdjustment</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_active_power_percentage_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Source</td><td>41505</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30617'>Active Power Percentage Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterActivePowerPercentageAdjustmentFeedback</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_active_power_percentage_adjustment_feedback</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30617</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31007'>B-C Line Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>LineVoltage</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_b_c_line_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_b_c_line_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_b_c_line_voltage/state</td></tr>
<tr><td>Source</td><td>31007</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31009'>C-A Line Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>LineVoltage</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_c_a_line_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_c_a_line_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_c_a_line_voltage/state</td></tr>
<tr><td>Source</td><td>31009</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_inverter_1_daily_pv_energy'>Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterPVDailyGeneration</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_daily_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>31509</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30525'>Firmware Version</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterFirmwareVersion</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_firmware_version</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_firmware_version/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_firmware_version/state</td></tr>
<tr><td>Source</td><td>30525</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30608'>Gateway Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterAlarm4</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_alarm_4</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_alarm_4/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_4/state</td></tr>
<tr><td>Source</td><td>30608</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31002'>Grid Frequency</a></h5>
<table>
<tr><td>Sensor Class</td><td>GridFrequency</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_grid_frequency</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_grid_frequency/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_grid_frequency/state</td></tr>
<tr><td>Source</td><td>31002</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31037'>Insulation Resistance</a></h5>
<table>
<tr><td>Sensor Class</td><td>InsulationResistance</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>MΩ</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_insulation_resistance</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_insulation_resistance/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_insulation_resistance/state</td></tr>
<tr><td>Source</td><td>31037</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_inverter_1_lifetime_pv_energy'>Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterPVLifetimeGeneration</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_lifetime_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>31511</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31026'>MPTT Count</a></h5>
<table>
<tr><td>Sensor Class</td><td>MPTTCount</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_mptt_count</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_mptt_count/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_mptt_count/state</td></tr>
<tr><td>Source</td><td>31026</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30546'>Max Absorption Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxAbsorptionPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_absorption_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_absorption_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_absorption_power/state</td></tr>
<tr><td>Source</td><td>30546</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30544'>Max Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterMaxActivePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_active_power/state</td></tr>
<tr><td>Source</td><td>30544</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30579'>Max Active Power Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxActivePowerAdjustment</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_active_power_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_active_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30579</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30542'>Max Rated Apparent Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxRatedApparentPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kVA</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_rated_apparent_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_rated_apparent_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_rated_apparent_power/state</td></tr>
<tr><td>Source</td><td>30542</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30583'>Max Reactive Power Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxReactivePowerAdjustment</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_reactive_power_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_reactive_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_reactive_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30583</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30581'>Min Active Power Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>MinActivePowerAdjustment</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_min_active_power_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_active_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_active_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30581</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30585'>Min Reactive Power Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>MinReactivePowerAdjustment</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_min_reactive_power_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_reactive_power_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_reactive_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30585</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30500'>Model</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterModel</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_model</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_model/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_model/state</td></tr>
<tr><td>Source</td><td>30500</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31004'>Output Type</a></h5>
<table>
<tr><td>Sensor Class</td><td>OutputType</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_output_type</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_output_type/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_output_type/state</td></tr>
<tr><td>Source</td><td>31004</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31024'>PACK/BCU Count</a></h5>
<table>
<tr><td>Sensor Class</td><td>PACKBCUCount</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pack_bcu_count</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pack_bcu_count/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pack_bcu_count/state</td></tr>
<tr><td>Source</td><td>31024</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pcs_alarm'>PCS Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterPCSAlarm</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pcs_alarm</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pcs_alarm/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pcs_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 30605 and 30606</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31035'>PV Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterPVPower</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv_power/state</td></tr>
<tr><td>Source</td><td>31035</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31025'>PV String Count</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringCount</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv_string_count</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_string_count/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv_string_count/state</td></tr>
<tr><td>Source</td><td>31025</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31017'>Phase A Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseCurrent</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_phase_a_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_a_current/state</td></tr>
<tr><td>Source</td><td>31017</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31011'>Phase A Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseVoltage</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_phase_a_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_a_voltage/state</td></tr>
<tr><td>Source</td><td>31011</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31019'>Phase B Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseCurrent</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_phase_b_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_b_current/state</td></tr>
<tr><td>Source</td><td>31019</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31013'>Phase B Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseVoltage</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_phase_b_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_b_voltage/state</td></tr>
<tr><td>Source</td><td>31013</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31021'>Phase C Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseCurrent</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_phase_c_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_c_current/state</td></tr>
<tr><td>Source</td><td>31021</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31015'>Phase C Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PhaseVoltage</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_phase_c_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_c_voltage/state</td></tr>
<tr><td>Source</td><td>31015</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31023'>Power Factor</a></h5>
<table>
<tr><td>Sensor Class</td><td>PowerFactor</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_power_factor</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_power_factor/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor/state</td></tr>
<tr><td>Source</td><td>31023</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_41507'>Power Factor Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterPowerFactorAdjustment</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_power_factor_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Source</td><td>41507</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30619'>Power Factor Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterPowerFactorAdjustmentFeedback</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_power_factor_adjustment_feedback</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30619</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30540'>Rated Active Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>RatedActivePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_rated_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_active_power/state</td></tr>
<tr><td>Source</td><td>30540</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31001'>Rated Grid Frequency</a></h5>
<table>
<tr><td>Sensor Class</td><td>RatedGridFrequency</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_rated_grid_frequency</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_frequency/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_grid_frequency/state</td></tr>
<tr><td>Source</td><td>31001</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31000'>Rated Grid Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>RatedGridVoltage</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_rated_grid_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_grid_voltage/state</td></tr>
<tr><td>Source</td><td>31000</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30589'>Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>ReactivePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power/state</td></tr>
<tr><td>Source</td><td>30589</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_41503'>Reactive Power Fixed Value Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterReactivePowerFixedValueAdjustment</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_fixed_value_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Source</td><td>41503</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30615'>Reactive Power Fixed Value Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterReactivePowerFixedValueAdjustmentFeedback</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30615</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30618'>Reactive Power Percentage Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterReactivePowerPercentageAdjustmentFeedback</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30618</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_41506'>Reactive Power Q/S Adjustment</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterReactivePowerQSAdjustment</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_q_s_adjustment</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Source</td><td>41506</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_41500'>Remote EMS Dispatch</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterRemoteEMSDispatch</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_remote_ems_dispatch</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/switch/sigen_0_001_inverter/sigen_0_inverter_1_remote_ems_dispatch/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/state</td></tr>
<tr><td>Source</td><td>41500</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30578'>Running State</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterRunningState</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_running_state</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_running_state/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_running_state/state</td></tr>
<tr><td>Source</td><td>30578</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_30515'>Serial Number</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterSerialNumber</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_serial_number</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_serial_number/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_serial_number/state</td></tr>
<tr><td>Source</td><td>30515</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31040'>Shutdown Time</a></h5>
<table>
<tr><td>Sensor Class</td><td>ShutdownTime</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_shutdown_time</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_shutdown_time/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_shutdown_time/state</td></tr>
<tr><td>Source</td><td>31040</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31038'>Startup Time</a></h5>
<table>
<tr><td>Sensor Class</td><td>StartupTime</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_startup_time</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_startup_time/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_startup_time/state</td></tr>
<tr><td>Source</td><td>31038</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31003'>Temperature</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterTemperature</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_temperature</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_temperature/state</td></tr>
<tr><td>Source</td><td>31003</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>

#### Energy Storage System
<h5><a id='sigen_0_001_30607'>Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterAlarm3</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_alarm_3</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_alarm_3/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_3/state</td></tr>
<tr><td>Source</td><td>30607</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30595'>Available Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableBatteryChargeEnergy</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_available_battery_charge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_available_battery_charge_energy/state</td></tr>
<tr><td>Source</td><td>30595</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30597'>Available Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>AvailableBatteryDischargeEnergy</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_available_battery_discharge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_available_battery_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30597</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30603'>Average Cell Temperature</a></h5>
<table>
<tr><td>Sensor Class</td><td>AverageCellTemperature</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_average_cell_temperature</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_average_cell_temperature/state</td></tr>
<tr><td>Source</td><td>30603</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30604'>Average Cell Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>AverageCellVoltage</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_average_cell_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_average_cell_voltage/state</td></tr>
<tr><td>Source</td><td>30604</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_battery_charging_power'>Battery Charging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterBatteryChargingPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_battery_charging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_charging_power/state</td></tr>
<tr><td>Source</td><td>ChargeDischargePower &gt; 0</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_battery_discharging_power'>Battery Discharging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterBatteryDischargingPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_battery_discharging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_discharging_power/state</td></tr>
<tr><td>Source</td><td>ChargeDischargePower &lt; 0 &times; -1</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_001_30599'>Battery Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>ChargeDischargePower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_charge_discharge_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_charge_discharge_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_charge_discharge_power/state</td></tr>
<tr><td>Source</td><td>30599</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30601'>Battery SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterBatterySoC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_battery_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_soc/state</td></tr>
<tr><td>Source</td><td>30601</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30602'>Battery SoH</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterBatterySoH</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_battery_soh</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soh/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_soh/state</td></tr>
<tr><td>Source</td><td>30602</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30566'>Daily Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>DailyChargeEnergy</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_daily_charge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_charge_energy/state</td></tr>
<tr><td>Source</td><td>30566</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30572'>Daily Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>DailyDischargeEnergy</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_daily_discharge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30572</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30568'>Lifetime Charge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>AccumulatedChargeEnergy</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_accumulated_charge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_charge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_accumulated_charge_energy/state</td></tr>
<tr><td>Source</td><td>30568</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30574'>Lifetime Discharge Energy</a></h5>
<table>
<tr><td>Sensor Class</td><td>AccumulatedDischargeEnergy</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_accumulated_discharge_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_discharge_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_accumulated_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30574</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30620'>Max Battery Temperature</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterMaxBatteryTemperature</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_battery_temperature</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_temperature/state</td></tr>
<tr><td>Source</td><td>30620</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30591'>Max Charge Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxBatteryChargePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_battery_charge_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_charge_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_charge_power/state</td></tr>
<tr><td>Source</td><td>30591</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30593'>Max Discharge Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>MaxBatteryDischargePower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_max_battery_discharge_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_discharge_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_discharge_power/state</td></tr>
<tr><td>Source</td><td>30593</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30621'>Min Battery Temperature</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterMinBatteryTemperature</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_min_battery_temperature</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_min_battery_temperature/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_battery_temperature/state</td></tr>
<tr><td>Source</td><td>30621</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30548'>Rated Battery Capacity</a></h5>
<table>
<tr><td>Sensor Class</td><td>RatedBatteryCapacity</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_rated_battery_capacity</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_battery_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_battery_capacity/state</td></tr>
<tr><td>Source</td><td>30548</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30550'>Rated Charging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>RatedChargingPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_rated_charging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>30550</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_30552'>Rated Discharging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>RatedDischargingPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_rated_discharging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_discharging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_discharging_power/state</td></tr>
<tr><td>Source</td><td>30552</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
</table>

#### PV String

The actual number of PV Strings is determined from `PV String Count` in the Inverter.
<h5><a id='sigen_0_001_31028'>PV String 1 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv1_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_current/state</td></tr>
<tr><td>Source</td><td>31028</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31030'>PV String 2 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv2_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_current/state</td></tr>
<tr><td>Source</td><td>31030</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31032'>PV String 3 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv3_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_current/state</td></tr>
<tr><td>Source</td><td>31032</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31034'>PV String 4 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv4_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_current/state</td></tr>
<tr><td>Source</td><td>31034</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31043'>PV String 5 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv5_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_current/state</td></tr>
<tr><td>Source</td><td>31043</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31045'>PV String 6 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv6_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_current/state</td></tr>
<tr><td>Source</td><td>31045</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31047'>PV String 7 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv7_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_current/state</td></tr>
<tr><td>Source</td><td>31047</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31049'>PV String 8 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv8_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_current/state</td></tr>
<tr><td>Source</td><td>31049</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31051'>PV String 9 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv9_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_current/state</td></tr>
<tr><td>Source</td><td>31051</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31053'>PV String 10 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv10_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_current/state</td></tr>
<tr><td>Source</td><td>31053</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31055'>PV String 11 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv11_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_current/state</td></tr>
<tr><td>Source</td><td>31055</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31057'>PV String 12 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv12_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_current/state</td></tr>
<tr><td>Source</td><td>31057</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31059'>PV String 13 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv13_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_current/state</td></tr>
<tr><td>Source</td><td>31059</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31061'>PV String 14 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv14_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_current/state</td></tr>
<tr><td>Source</td><td>31061</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31063'>PV String 15 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv15_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_current/state</td></tr>
<tr><td>Source</td><td>31063</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31065'>PV String 16 Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv16_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_current/state</td></tr>
<tr><td>Source</td><td>31065</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv1_daily_energy'>PV String 1 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv1_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv2_daily_energy'>PV String 2 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv2_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv3_daily_energy'>PV String 3 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv3_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv4_daily_energy'>PV String 4 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv4_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv5_daily_energy'>PV String 5 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv5_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv6_daily_energy'>PV String 6 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv6_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv7_daily_energy'>PV String 7 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv7_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv8_daily_energy'>PV String 8 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv8_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv9_daily_energy'>PV String 9 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv9_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv10_daily_energy'>PV String 10 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv10_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv11_daily_energy'>PV String 11 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv11_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv12_daily_energy'>PV String 12 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv12_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv13_daily_energy'>PV String 13 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv13_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv14_daily_energy'>PV String 14 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv14_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv15_daily_energy'>PV String 15 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv15_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv16_daily_energy'>PV String 16 Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv16_daily_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_daily_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv1_lifetime_energy'>PV String 1 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv1_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv2_lifetime_energy'>PV String 2 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv2_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv3_lifetime_energy'>PV String 3 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv3_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv4_lifetime_energy'>PV String 4 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv4_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv5_lifetime_energy'>PV String 5 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv5_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv6_lifetime_energy'>PV String 6 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv6_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv7_lifetime_energy'>PV String 7 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv7_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv8_lifetime_energy'>PV String 8 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv8_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv9_lifetime_energy'>PV String 9 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv9_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv10_lifetime_energy'>PV String 10 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv10_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv11_lifetime_energy'>PV String 11 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv11_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv12_lifetime_energy'>PV String 12 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv12_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv13_lifetime_energy'>PV String 13 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv13_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv14_lifetime_energy'>PV String 14 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv14_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv15_lifetime_energy'>PV String 15 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv15_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv16_lifetime_energy'>PV String 16 Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv16_lifetime_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_lifetime_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv1_power'>PV String 1 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv1_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv2_power'>PV String 2 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv2_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv3_power'>PV String 3 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv3_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv4_power'>PV String 4 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv4_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv5_power'>PV String 5 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv5_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv6_power'>PV String 6 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv6_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv7_power'>PV String 7 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv7_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv8_power'>PV String 8 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv8_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv9_power'>PV String 9 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv9_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv10_power'>PV String 10 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv10_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv11_power'>PV String 11 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv11_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv12_power'>PV String 12 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv12_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv13_power'>PV String 13 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv13_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv14_power'>PV String 14 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv14_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv15_power'>PV String 15 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv15_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv16_power'>PV String 16 Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVStringPower</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv16_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
</table>
<h5><a id='sigen_0_001_31027'>PV String 1 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv1_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_voltage/state</td></tr>
<tr><td>Source</td><td>31027</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31029'>PV String 2 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv2_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_voltage/state</td></tr>
<tr><td>Source</td><td>31029</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31031'>PV String 3 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv3_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_voltage/state</td></tr>
<tr><td>Source</td><td>31031</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31033'>PV String 4 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv4_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_voltage/state</td></tr>
<tr><td>Source</td><td>31033</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31042'>PV String 5 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv5_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_voltage/state</td></tr>
<tr><td>Source</td><td>31042</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31044'>PV String 6 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv6_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_voltage/state</td></tr>
<tr><td>Source</td><td>31044</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31046'>PV String 7 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv7_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_voltage/state</td></tr>
<tr><td>Source</td><td>31046</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31048'>PV String 8 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv8_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_voltage/state</td></tr>
<tr><td>Source</td><td>31048</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31050'>PV String 9 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv9_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_voltage/state</td></tr>
<tr><td>Source</td><td>31050</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31052'>PV String 10 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv10_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_voltage/state</td></tr>
<tr><td>Source</td><td>31052</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31054'>PV String 11 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv11_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_voltage/state</td></tr>
<tr><td>Source</td><td>31054</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31056'>PV String 12 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv12_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_voltage/state</td></tr>
<tr><td>Source</td><td>31056</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31058'>PV String 13 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv13_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_voltage/state</td></tr>
<tr><td>Source</td><td>31058</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31060'>PV String 14 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv14_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_voltage/state</td></tr>
<tr><td>Source</td><td>31060</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31062'>PV String 15 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv15_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_voltage/state</td></tr>
<tr><td>Source</td><td>31062</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_31064'>PV String 16 Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_pv16_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_voltage/state</td></tr>
<tr><td>Source</td><td>31064</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>

### AC Charger
<h5><a id='sigen_0_ac_charger_2_alarm'>Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerAlarms</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_alarm</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_alarm/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 32012, 32013, and 32014</td></tr>
</table>
<h5><a id='sigen_0_002_32003'>Charging Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerChargingPower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_charging_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_charging_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>32003</td></tr>
</table>
<h5><a id='sigen_0_002_32010'>Input Breaker</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerInputBreaker</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_input_breaker</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_input_breaker/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_input_breaker/state</td></tr>
<tr><td>Source</td><td>32010</td></tr>
</table>
<h5><a id='sigen_0_002_42001'>Output Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerOutputCurrent</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_output_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/number/sigen_0_002_accharger/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Source</td><td>42001</td></tr>
</table>
<h5><a id='sigen_0_002_32007'>Rated Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerRatedCurrent</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_current/state</td></tr>
<tr><td>Source</td><td>32007</td></tr>
</table>
<h5><a id='sigen_0_002_32005'>Rated Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerRatedPower</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_power/state</td></tr>
<tr><td>Source</td><td>32005</td></tr>
</table>
<h5><a id='sigen_0_002_32009'>Rated Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerRatedVoltage</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_voltage/state</td></tr>
<tr><td>Source</td><td>32009</td></tr>
</table>
<h5><a id='sigen_0_002_32000'>Running State</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerRunningState</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_running_state</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_running_state/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_running_state/state</td></tr>
<tr><td>Source</td><td>32000</td></tr>
</table>
<h5><a id='sigen_0_002_32001'>Total Energy Consumed</a></h5>
<table>
<tr><td>Sensor Class</td><td>ACChargerTotalEnergyConsumed</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_ac_charger_2_total_energy_consumed</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_total_energy_consumed/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_total_energy_consumed/state</td></tr>
<tr><td>Source</td><td>32001</td></tr>
</table>

### DC Charger
<h5><a id='sigen_0_001_30609'>Alarms</a></h5>
<table>
<tr><td>Sensor Class</td><td>InverterAlarm5</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_inverter_1_alarm_5</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_inverter_1_alarm_5/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_5/state</td></tr>
<tr><td>Source</td><td>30609</td></tr>
</table>
<h5><a id='sigen_0_001_31505'>Current Charging Capacity</a></h5>
<table>
<tr><td>Sensor Class</td><td>DCChargerCurrentChargingCapacity</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_dc_charger_current_charging_capacity</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_dc_charger_current_charging_capacity/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_dc_charger_current_charging_capacity/state</td></tr>
<tr><td>Source</td><td>31505</td></tr>
<tr><td>Comment</td><td>Single time</td></tr>
</table>
<h5><a id='sigen_0_001_31507'>Current Charging Duration</a></h5>
<table>
<tr><td>Sensor Class</td><td>DCChargerCurrentChargingDuration</td></tr>
<tr><td>Scan Interval</td><td>600s</td></tr>
<tr><td>Unit of Measurement</td><td>s</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_dc_charger_current_charging_duration</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_dc_charger_current_charging_duration/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_dc_charger_current_charging_duration/state</td></tr>
<tr><td>Source</td><td>31507</td></tr>
<tr><td>Comment</td><td>Single time</td></tr>
</table>
<h5><a id='sigen_0_001_31502'>Output Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>DCChargerOutputPower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_dc_charger_output_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_dc_charger_output_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_dc_charger_output_power/state</td></tr>
<tr><td>Source</td><td>31502</td></tr>
</table>
<h5><a id='sigen_0_001_31500'>Vehicle Battery Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>VehicleBatteryVoltage</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_vehicle_battery_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_vehicle_battery_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_vehicle_battery_voltage/state</td></tr>
<tr><td>Source</td><td>31500</td></tr>
</table>
<h5><a id='sigen_0_001_31501'>Vehicle Charging Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>VehicleChargingCurrent</td></tr>
<tr><td>Scan Interval</td><td>10s</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_vehicle_charging_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_vehicle_charging_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_vehicle_charging_current/state</td></tr>
<tr><td>Source</td><td>31501</td></tr>
</table>
<h5><a id='sigen_0_001_31504'>Vehicle SoC</a></h5>
<table>
<tr><td>Sensor Class</td><td>VehicleSoC</td></tr>
<tr><td>Scan Interval</td><td>60s</td></tr>
<tr><td>Unit of Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_plant_vehicle_soc</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_plant_vehicle_soc/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_vehicle_soc/state</td></tr>
<tr><td>Source</td><td>31504</td></tr>
</table>

#### Smart-Port (Enphase Envoy only)
<h5><a id='sigen_0_enphase_123456789012_current'>Current</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphaseCurrent</td></tr>
<tr><td>Unit of Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_current</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_current/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_current/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_daily_pv_energy'>Daily Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphaseDailyPVEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_daily_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_daily_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_frequency'>Frequency</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphaseFrequency</td></tr>
<tr><td>Unit of Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_frequency</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_frequency/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_frequency/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_lifetime_pv_energy'>Lifetime Production</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphaseLifetimePVEnergy</td></tr>
<tr><td>Unit of Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_lifetime_pv_energy</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_active_power'>PV Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphasePVPower</td></tr>
<tr><td>Scan Interval</td><td>5s</td></tr>
<tr><td>Unit of Measurement</td><td>W</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_active_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_active_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_active_power/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_power_factor'>Power Factor</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphasePowerFactor</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_power_factor</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_power_factor/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_power_factor/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_reactive_power'>Reactive Power</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphaseReactivePower</td></tr>
<tr><td>Unit of Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_reactive_power</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_reactive_power/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_reactive_power/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_voltage'>Voltage</a></h5>
<table>
<tr><td>Sensor Class</td><td>EnphaseVoltage</td></tr>
<tr><td>Unit of Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home Assistant Sensor</td><td>sensor.sigen_0_enphase_123456789012_voltage</td></tr>
<tr><td>Home Assistant State Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_voltage/state</td></tr>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_voltage/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
</table>

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
<h5><a id='sigen_0_247_40001'>Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40005'>Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40046'>Backup SoC
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/set</td></tr>
</table>
<h5><a id='sigen_0_247_40047'>Charge Cut-Off SoC
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/set</td></tr>
</table>
<h5><a id='sigen_0_247_40048'>Discharge Cut-Off SoC
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/set</td></tr>
</table>
<h5><a id='sigen_0_247_40038'>Grid Max Export Limit
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/set</td></tr>
</table>
<h5><a id='sigen_0_247_40040'>Grid Max Import Limit
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/set</td></tr>
</table>
<h5><a id='sigen_0_247_40030'>Independent Phase Power Control
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/set</td></tr>
</table>
<h5><a id='sigen_0_247_40032'>Max Charging Limit
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/set</td></tr>
</table>
<h5><a id='sigen_0_247_40034'>Max Discharging Limit
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/set</td></tr>
</table>
<h5><a id='sigen_0_247_40042'>PCS Max Export Limit
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/set</td></tr>
</table>
<h5><a id='sigen_0_247_40044'>PCS Max Import Limit
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/set</td></tr>
</table>
<h5><a id='sigen_0_247_40036'>PV Max Power Limit
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/set</td></tr>
</table>
<h5><a id='sigen_0_247_40008'>Phase A Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40020'>Phase A Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40023'>Phase A Q/S Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40014'>Phase A Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40010'>Phase B Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40021'>Phase B Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40024'>Phase B Q/S Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40016'>Phase B Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40012'>Phase C Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40022'>Phase C Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40025'>Phase C Q/S Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40018'>Phase C Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40000'>Power On/Off
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_status/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_status/set</td></tr>
</table>
<h5><a id='sigen_0_247_40007'>Power Factor Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40006'>Q/S Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40003'>Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/set</td></tr>
</table>
<h5><a id='sigen_0_247_40029'>Remote EMS
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/set</td></tr>
</table>
<h5><a id='sigen_0_247_40031'>Remote EMS Control Mode
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/set</td></tr>
</table>

### Inverter
<h5><a id='sigen_0_001_41501'>Active Power Fixed Value Adjustment
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_41505'>Active Power Percentage Adjustment
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_40500'>Power On/Off
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_status/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_status/set</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
</table>
<h5><a id='sigen_0_001_41507'>Power Factor Adjustment
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_41503'>Reactive Power Fixed Value Adjustment
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_41506'>Reactive Power Q/S Adjustment
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>
<h5><a id='sigen_0_001_41500'>Remote EMS Dispatch
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_remote_ems_dispatch/set</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
</table>

### AC Charger
<h5><a id='sigen_0_002_42000'>AC Charger Stop/Start
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2/set</td></tr>
</table>
<h5><a id='sigen_0_002_42001'>Output Current
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/set</td></tr>
</table>

### DC Charger
<h5><a id='sigen_0_001_41000'>DC Charger Stop/Start
</a></h5>
<table>
<tr><td>Simplified State Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1/state</td></tr>
<tr><td>Simplified Update Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1/set</td></tr>
</table>
