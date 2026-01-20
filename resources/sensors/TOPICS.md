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
- The index of the Modbus host from the configuration file (or auto-discovery), starting from 0. (This is to prevent clashes with the <a href='https://github.com/TypQxQ/Sigenergy-Local-Modbus'>TypQxQ Sigenergy-Local-Modbus</a> HACS integration.)
- _ separator
##### _Followed by:_
###### Plant Sensors


- The sensor description.
  - Plant sensors have no device type or device ID, but the description _may_ be prefixed with `plant_` for clarity.
  - The description for Smart Load sensors will be prefixed by `smart_load_` (not `plant_`).
  - The description for Statistics Interface sensors will be prefixed by `si_` (not `plant_`).
##### _OR:_
###### Device Sensors


- The device type (inverter, ac_charger, or dc_charger).
- _ separator
- The Modbus device ID. Normally 1 for the Inverter and DC Charger and 2 for an AC Charger, but depends on how the installer configured the Modbus interface.
- _ separator
- The sensor description.

<table>
<tr><th>Published Topics</th><th>Subscribed Topics</th></tr>
<tr><td>

<h6>Plant</h6>
<a href='#sigen_0_247_30031'>Active Power</a><br>
<a href='#sigen_0_247_40001'>Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40005'>Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40049'>Active Power Regulation Gradient</a><br>
<a href='#sigen_0_247_30039'>Available Max Active Power</a><br>
<a href='#sigen_0_247_30064'>Available Max Charging Capacity</a><br>
<a href='#sigen_0_247_30047'>Available Max Charging Power</a><br>
<a href='#sigen_0_247_30066'>Available Max Discharging Capacity</a><br>
<a href='#sigen_0_247_30049'>Available Max Discharging Power</a><br>
<a href='#sigen_0_247_30043'>Available Max Reactive Power</a><br>
<a href='#sigen_0_247_30041'>Available Min Active Power</a><br>
<a href='#sigen_0_247_30045'>Available Min Reactive Power</a><br>
<a href='#sigen_0_247_40046'>Backup SoC</a><br>
<a href='#sigen_0_battery_charging_power'>Battery Charging Power</a><br>
<a href='#sigen_0_battery_discharging_power'>Battery Discharging Power</a><br>
<a href='#sigen_0_247_30037'>Battery Power</a><br>
<a href='#sigen_0_247_30014'>Battery SoC</a><br>
<a href='#sigen_0_247_30087'>Battery SoH</a><br>
<a href='#sigen_0_247_30085'>Charge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40047'>Charge Cut-Off SoC</a><br>
<a href='#sigen_0_consumed_power'>Consumed Power</a><br>
<a href='#sigen_0_247_30279'>Current Control Command Value</a><br>
<a href='#sigen_0_247_30072'>DC Charger Alarms</a><br>
<a href='#sigen_0_daily_charge_energy'>Daily Charge Energy</a><br>
<a href='#sigen_0_daily_consumed_energy'>Daily Consumption</a><br>
<a href='#sigen_0_daily_discharge_energy'>Daily Discharge Energy</a><br>
<a href='#sigen_0_daily_pv_energy'>Daily PV Production</a><br>
<a href='#sigen_0_total_daily_pv_energy'>Daily Total PV Production</a><br>
<a href='#sigen_0_247_30086'>Discharge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40048'>Discharge Cut-Off SoC</a><br>
<a href='#sigen_0_247_30003'>EMS Work Mode</a><br>
<a href='#sigen_0_247_30029'>ESS Alarms</a><br>
<a href='#sigen_0_247_30030'>Gateway Alarms</a><br>
<a href='#sigen_0_247_30282'>General Load Power</a><br>
<a href='#sigen_0_247_40038'>Grid Max Export Limit</a><br>
<a href='#sigen_0_247_40040'>Grid Max Import Limit</a><br>
<a href='#sigen_0_247_40030'>Independent Phase Power Control</a><br>
<a href='#sigen_0_accumulated_charge_energy'>Lifetime Charge Energy</a><br>
<a href='#sigen_0_lifetime_consumed_energy'>Lifetime Consumption</a><br>
<a href='#sigen_0_247_30208'>Lifetime DC EV Charge Energy</a><br>
<a href='#sigen_0_247_30212'>Lifetime DC EV Discharge Energy</a><br>
<a href='#sigen_0_accumulated_discharge_energy'>Lifetime Discharge Energy</a><br>
<a href='#sigen_0_247_30224'>Lifetime Generator Output Energy</a><br>
<a href='#sigen_0_247_30088'>Lifetime PV Production</a><br>
<a href='#sigen_0_247_30196'>Lifetime Third-Party PV Production</a><br>
<a href='#sigen_0_lifetime_pv_energy'>Lifetime Total PV Production</a><br>
<a href='#sigen_0_247_30010'>Max Active Power</a><br>
<a href='#sigen_0_247_30012'>Max Apparent Power</a><br>
<a href='#sigen_0_247_40032'>Max Charging Limit</a><br>
<a href='#sigen_0_247_40034'>Max Discharging Limit</a><br>
<a href='#sigen_0_general_pcs_alarm'>PCS Alarms</a><br>
<a href='#sigen_0_247_40042'>PCS Max Export Limit</a><br>
<a href='#sigen_0_247_40044'>PCS Max Import Limit</a><br>
<a href='#sigen_0_247_40036'>PV Max Power Limit</a><br>
<a href='#sigen_0_247_30035'>PV Power</a><br>
<a href='#sigen_0_247_30015'>Phase A Active Power</a><br>
<a href='#sigen_0_247_40008'>Phase A Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40020'>Phase A Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40023'>Phase A Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30021'>Phase A Reactive Power</a><br>
<a href='#sigen_0_247_40014'>Phase A Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30017'>Phase B Active Power</a><br>
<a href='#sigen_0_247_40010'>Phase B Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40021'>Phase B Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40024'>Phase B Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30023'>Phase B Reactive Power</a><br>
<a href='#sigen_0_247_40016'>Phase B Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30019'>Phase C Active Power</a><br>
<a href='#sigen_0_247_40012'>Phase C Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40022'>Phase C Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40025'>Phase C Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_30025'>Phase C Reactive Power</a><br>
<a href='#sigen_0_247_40018'>Phase C Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_plant_alarms'>Plant Alarms</a><br>
<a href='#sigen_0_247_40007'>Power Factor Adjustment Target Value</a><br>
<a href='#sigen_0_247_40006'>Q/S Adjustment Target Value</a><br>
<a href='#sigen_0_247_30068'>Rated Charging Power</a><br>
<a href='#sigen_0_247_30070'>Rated Discharging Power</a><br>
<a href='#sigen_0_247_30083'>Rated Energy Capacity</a><br>
<a href='#sigen_0_247_30033'>Reactive Power</a><br>
<a href='#sigen_0_247_40003'>Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40029'>Remote EMS</a><br>
<a href='#sigen_0_247_40031'>Remote EMS Control Mode</a><br>
<a href='#sigen_0_247_30051'>Running State</a><br>
<a href='#sigen_0_247_30146'>Smart Load 01 Power</a><br>
<a href='#sigen_0_247_30098'>Smart Load 01 Total Consumption</a><br>
<a href='#sigen_0_247_30148'>Smart Load 02 Power</a><br>
<a href='#sigen_0_247_30100'>Smart Load 02 Total Consumption</a><br>
<a href='#sigen_0_247_30150'>Smart Load 03 Power</a><br>
<a href='#sigen_0_247_30102'>Smart Load 03 Total Consumption</a><br>
<a href='#sigen_0_247_30152'>Smart Load 04 Power</a><br>
<a href='#sigen_0_247_30104'>Smart Load 04 Total Consumption</a><br>
<a href='#sigen_0_247_30154'>Smart Load 05 Power</a><br>
<a href='#sigen_0_247_30106'>Smart Load 05 Total Consumption</a><br>
<a href='#sigen_0_247_30156'>Smart Load 06 Power</a><br>
<a href='#sigen_0_247_30108'>Smart Load 06 Total Consumption</a><br>
<a href='#sigen_0_247_30158'>Smart Load 07 Power</a><br>
<a href='#sigen_0_247_30110'>Smart Load 07 Total Consumption</a><br>
<a href='#sigen_0_247_30160'>Smart Load 08 Power</a><br>
<a href='#sigen_0_247_30112'>Smart Load 08 Total Consumption</a><br>
<a href='#sigen_0_247_30162'>Smart Load 09 Power</a><br>
<a href='#sigen_0_247_30114'>Smart Load 09 Total Consumption</a><br>
<a href='#sigen_0_247_30164'>Smart Load 10 Power</a><br>
<a href='#sigen_0_247_30116'>Smart Load 10 Total Consumption</a><br>
<a href='#sigen_0_247_30166'>Smart Load 11 Power</a><br>
<a href='#sigen_0_247_30118'>Smart Load 11 Total Consumption</a><br>
<a href='#sigen_0_247_30168'>Smart Load 12 Power</a><br>
<a href='#sigen_0_247_30120'>Smart Load 12 Total Consumption</a><br>
<a href='#sigen_0_247_30170'>Smart Load 13 Power</a><br>
<a href='#sigen_0_247_30122'>Smart Load 13 Total Consumption</a><br>
<a href='#sigen_0_247_30172'>Smart Load 14 Power</a><br>
<a href='#sigen_0_247_30124'>Smart Load 14 Total Consumption</a><br>
<a href='#sigen_0_247_30174'>Smart Load 15 Power</a><br>
<a href='#sigen_0_247_30126'>Smart Load 15 Total Consumption</a><br>
<a href='#sigen_0_247_30176'>Smart Load 16 Power</a><br>
<a href='#sigen_0_247_30128'>Smart Load 16 Total Consumption</a><br>
<a href='#sigen_0_247_30178'>Smart Load 17 Power</a><br>
<a href='#sigen_0_247_30130'>Smart Load 17 Total Consumption</a><br>
<a href='#sigen_0_247_30180'>Smart Load 18 Power</a><br>
<a href='#sigen_0_247_30132'>Smart Load 18 Total Consumption</a><br>
<a href='#sigen_0_247_30182'>Smart Load 19 Power</a><br>
<a href='#sigen_0_247_30134'>Smart Load 19 Total Consumption</a><br>
<a href='#sigen_0_247_30184'>Smart Load 20 Power</a><br>
<a href='#sigen_0_247_30136'>Smart Load 20 Total Consumption</a><br>
<a href='#sigen_0_247_30186'>Smart Load 21 Power</a><br>
<a href='#sigen_0_247_30138'>Smart Load 21 Total Consumption</a><br>
<a href='#sigen_0_247_30188'>Smart Load 22 Power</a><br>
<a href='#sigen_0_247_30140'>Smart Load 22 Total Consumption</a><br>
<a href='#sigen_0_247_30190'>Smart Load 23 Power</a><br>
<a href='#sigen_0_247_30142'>Smart Load 23 Total Consumption</a><br>
<a href='#sigen_0_247_30192'>Smart Load 24 Power</a><br>
<a href='#sigen_0_247_30144'>Smart Load 24 Total Consumption</a><br>
<a href='#sigen_0_247_30000'>System Time</a><br>
<a href='#sigen_0_247_30002'>System Time Zone</a><br>
<a href='#sigen_0_247_30194'>Third-Party PV Power</a><br>
<a href='#sigen_0_247_30284'>Total Load Power</a><br>
<a href='#sigen_0_total_pv_power'>Total PV Power</a><br>

<h6>Grid Sensor</h6>
<a href='#sigen_0_247_30005'>Active Power</a><br>
<a href='#sigen_0_grid_sensor_daily_export_energy'>Daily Exported Energy</a><br>
<a href='#sigen_0_grid_sensor_daily_import_energy'>Daily Imported Energy</a><br>
<a href='#sigen_0_grid_sensor_export_power'>Export Power</a><br>
<a href='#sigen_0_247_30004'>Grid Sensor Status</a><br>
<a href='#sigen_0_247_30009'>Grid Status</a><br>
<a href='#sigen_0_grid_sensor_import_power'>Import Power</a><br>
<a href='#sigen_0_grid_sensor_lifetime_export_energy'>Lifetime Exported Energy</a><br>
<a href='#sigen_0_grid_sensor_lifetime_import_energy'>Lifetime Imported Energy</a><br>
<a href='#sigen_0_247_30052'>Phase A Active Power</a><br>
<a href='#sigen_0_247_30058'>Phase A Reactive Power</a><br>
<a href='#sigen_0_247_30054'>Phase B Active Power</a><br>
<a href='#sigen_0_247_30060'>Phase B Reactive Power</a><br>
<a href='#sigen_0_247_30056'>Phase C Active Power</a><br>
<a href='#sigen_0_247_30062'>Phase C Reactive Power</a><br>
<a href='#sigen_0_247_30007'>Reactive Power</a><br>

<h6>Statistics</h6>
<a href='#sigen_0_247_30232'>Total AC EV Charge Energy</a><br>
<a href='#sigen_0_247_30244'>Total Charge Energy</a><br>
<a href='#sigen_0_247_30228'>Total Common Load Consumption</a><br>
<a href='#sigen_0_247_30252'>Total DC EV Charge Energy</a><br>
<a href='#sigen_0_247_30256'>Total DC EV Discharge Energy</a><br>
<a href='#sigen_0_247_30248'>Total Discharge Energy</a><br>
<a href='#sigen_0_247_30264'>Total Exported Energy</a><br>
<a href='#sigen_0_247_30268'>Total Generator Output Energy</a><br>
<a href='#sigen_0_247_30260'>Total Imported Energy</a><br>
<a href='#sigen_0_247_30236'>Total PV Production</a><br>
<a href='#sigen_0_247_30240'>Total Third-Party PV Production</a><br>

<h6>Inverter</h6>
<a href='#sigen_0_001_31005'>A-B Line Voltage</a><br>
<a href='#sigen_0_001_30587'>Active Power</a><br>
<a href='#sigen_0_001_41501'>Active Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_30613'>Active Power Fixed Value Adjustment Feedback</a><br>
<a href='#sigen_0_001_41505'>Active Power Percentage Adjustment</a><br>
<a href='#sigen_0_001_30617'>Active Power Percentage Adjustment Feedback</a><br>
<a href='#sigen_0_001_31007'>B-C Line Voltage</a><br>
<a href='#sigen_0_001_31009'>C-A Line Voltage</a><br>
<a href='#sigen_0_inverter_1_daily_pv_energy'>Daily Production</a><br>
<a href='#sigen_0_001_30525'>Firmware Version</a><br>
<a href='#sigen_0_001_30608'>Gateway Alarms</a><br>
<a href='#sigen_0_001_31002'>Grid Frequency</a><br>
<a href='#sigen_0_001_31037'>Insulation Resistance</a><br>
<a href='#sigen_0_inverter_1_lifetime_pv_energy'>Lifetime Production</a><br>
<a href='#sigen_0_001_31026'>MPTT Count</a><br>
<a href='#sigen_0_001_30546'>Max Absorption Power</a><br>
<a href='#sigen_0_001_30544'>Max Active Power</a><br>
<a href='#sigen_0_001_30579'>Max Active Power Adjustment</a><br>
<a href='#sigen_0_001_30542'>Max Rated Apparent Power</a><br>
<a href='#sigen_0_001_30583'>Max Reactive Power Adjustment</a><br>
<a href='#sigen_0_001_30581'>Min Active Power Adjustment</a><br>
<a href='#sigen_0_001_30585'>Min Reactive Power Adjustment</a><br>
<a href='#sigen_0_001_30500'>Model</a><br>
<a href='#sigen_0_001_31004'>Output Type</a><br>
<a href='#sigen_0_001_31024'>PACK/BCU Count</a><br>
<a href='#sigen_0_inverter_1_pcs_alarm'>PCS Alarms</a><br>
<a href='#sigen_0_001_31035'>PV Power</a><br>
<a href='#sigen_0_001_31025'>PV String Count</a><br>
<a href='#sigen_0_001_31017'>Phase A Current</a><br>
<a href='#sigen_0_001_31011'>Phase A Voltage</a><br>
<a href='#sigen_0_001_31019'>Phase B Current</a><br>
<a href='#sigen_0_001_31013'>Phase B Voltage</a><br>
<a href='#sigen_0_001_31021'>Phase C Current</a><br>
<a href='#sigen_0_001_31015'>Phase C Voltage</a><br>
<a href='#sigen_0_001_31023'>Power Factor</a><br>
<a href='#sigen_0_001_41507'>Power Factor Adjustment</a><br>
<a href='#sigen_0_001_30619'>Power Factor Adjustment Feedback</a><br>
<a href='#sigen_0_001_30540'>Rated Active Power</a><br>
<a href='#sigen_0_001_31001'>Rated Grid Frequency</a><br>
<a href='#sigen_0_001_31000'>Rated Grid Voltage</a><br>
<a href='#sigen_0_001_30589'>Reactive Power</a><br>
<a href='#sigen_0_001_41503'>Reactive Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_30615'>Reactive Power Fixed Value Adjustment Feedback</a><br>
<a href='#sigen_0_001_30618'>Reactive Power Percentage Adjustment Feedback</a><br>
<a href='#sigen_0_001_41506'>Reactive Power Q/S Adjustment</a><br>
<a href='#sigen_0_001_30578'>Running State</a><br>
<a href='#sigen_0_001_30515'>Serial Number</a><br>
<a href='#sigen_0_001_31040'>Shutdown Time</a><br>
<a href='#sigen_0_001_31038'>Startup Time</a><br>
<a href='#sigen_0_001_31003'>Temperature</a><br>

<h6>Energy Storage System</h6>
<a href='#sigen_0_001_30607'>Alarms</a><br>
<a href='#sigen_0_001_30595'>Available Charge Energy</a><br>
<a href='#sigen_0_001_30597'>Available Discharge Energy</a><br>
<a href='#sigen_0_001_30603'>Average Cell Temperature</a><br>
<a href='#sigen_0_001_30604'>Average Cell Voltage</a><br>
<a href='#sigen_0_inverter_1_battery_charging_power'>Battery Charging Power</a><br>
<a href='#sigen_0_inverter_1_battery_discharging_power'>Battery Discharging Power</a><br>
<a href='#sigen_0_001_30599'>Battery Power</a><br>
<a href='#sigen_0_001_30601'>Battery SoC</a><br>
<a href='#sigen_0_001_30602'>Battery SoH</a><br>
<a href='#sigen_0_001_30566'>Daily Charge Energy</a><br>
<a href='#sigen_0_001_30572'>Daily Discharge Energy</a><br>
<a href='#sigen_0_001_30568'>Lifetime Charge Energy</a><br>
<a href='#sigen_0_001_30574'>Lifetime Discharge Energy</a><br>
<a href='#sigen_0_001_30620'>Max Battery Temperature</a><br>
<a href='#sigen_0_001_30622'>Max Cell Voltage</a><br>
<a href='#sigen_0_001_30591'>Max Charge Power</a><br>
<a href='#sigen_0_001_30593'>Max Discharge Power</a><br>
<a href='#sigen_0_001_30621'>Min Battery Temperature</a><br>
<a href='#sigen_0_001_30623'>Min Cell Voltage</a><br>
<a href='#sigen_0_001_30548'>Rated Battery Capacity</a><br>
<a href='#sigen_0_001_30550'>Rated Charging Power</a><br>
<a href='#sigen_0_001_30552'>Rated Discharging Power</a><br>

<h6>PV String</h6>
<a href='#sigen_0_001_31028'>PV String 1 Current</a><br>
<a href='#sigen_0_001_31030'>PV String 2 Current</a><br>
<a href='#sigen_0_001_31032'>PV String 3 Current</a><br>
<a href='#sigen_0_001_31034'>PV String 4 Current</a><br>
<a href='#sigen_0_001_31043'>PV String 5 Current</a><br>
<a href='#sigen_0_001_31045'>PV String 6 Current</a><br>
<a href='#sigen_0_001_31047'>PV String 7 Current</a><br>
<a href='#sigen_0_001_31049'>PV String 8 Current</a><br>
<a href='#sigen_0_001_31051'>PV String 9 Current</a><br>
<a href='#sigen_0_001_31053'>PV String 10 Current</a><br>
<a href='#sigen_0_001_31055'>PV String 11 Current</a><br>
<a href='#sigen_0_001_31057'>PV String 12 Current</a><br>
<a href='#sigen_0_001_31059'>PV String 13 Current</a><br>
<a href='#sigen_0_001_31061'>PV String 14 Current</a><br>
<a href='#sigen_0_001_31063'>PV String 15 Current</a><br>
<a href='#sigen_0_001_31065'>PV String 16 Current</a><br>
<a href='#sigen_0_001_31067'>PV String 17 Current</a><br>
<a href='#sigen_0_001_31069'>PV String 18 Current</a><br>
<a href='#sigen_0_001_31071'>PV String 19 Current</a><br>
<a href='#sigen_0_001_31073'>PV String 20 Current</a><br>
<a href='#sigen_0_001_31075'>PV String 21 Current</a><br>
<a href='#sigen_0_001_31077'>PV String 22 Current</a><br>
<a href='#sigen_0_001_31079'>PV String 23 Current</a><br>
<a href='#sigen_0_001_31081'>PV String 24 Current</a><br>
<a href='#sigen_0_001_31083'>PV String 25 Current</a><br>
<a href='#sigen_0_001_31085'>PV String 26 Current</a><br>
<a href='#sigen_0_001_31087'>PV String 27 Current</a><br>
<a href='#sigen_0_001_31089'>PV String 28 Current</a><br>
<a href='#sigen_0_001_31091'>PV String 29 Current</a><br>
<a href='#sigen_0_001_31093'>PV String 30 Current</a><br>
<a href='#sigen_0_001_31095'>PV String 31 Current</a><br>
<a href='#sigen_0_001_31097'>PV String 32 Current</a><br>
<a href='#sigen_0_001_31099'>PV String 33 Current</a><br>
<a href='#sigen_0_001_31101'>PV String 34 Current</a><br>
<a href='#sigen_0_001_31103'>PV String 35 Current</a><br>
<a href='#sigen_0_001_31105'>PV String 36 Current</a><br>
<a href='#sigen_0_inverter_1_pv1_daily_energy'>PV String 1 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv2_daily_energy'>PV String 2 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv3_daily_energy'>PV String 3 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv4_daily_energy'>PV String 4 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv5_daily_energy'>PV String 5 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv6_daily_energy'>PV String 6 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv7_daily_energy'>PV String 7 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv8_daily_energy'>PV String 8 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv9_daily_energy'>PV String 9 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv10_daily_energy'>PV String 10 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv11_daily_energy'>PV String 11 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv12_daily_energy'>PV String 12 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv13_daily_energy'>PV String 13 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv14_daily_energy'>PV String 14 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv15_daily_energy'>PV String 15 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv16_daily_energy'>PV String 16 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv17_daily_energy'>PV String 17 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv18_daily_energy'>PV String 18 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv19_daily_energy'>PV String 19 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv20_daily_energy'>PV String 20 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv21_daily_energy'>PV String 21 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv22_daily_energy'>PV String 22 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv23_daily_energy'>PV String 23 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv24_daily_energy'>PV String 24 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv25_daily_energy'>PV String 25 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv26_daily_energy'>PV String 26 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv27_daily_energy'>PV String 27 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv28_daily_energy'>PV String 28 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv29_daily_energy'>PV String 29 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv30_daily_energy'>PV String 30 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv31_daily_energy'>PV String 31 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv32_daily_energy'>PV String 32 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv33_daily_energy'>PV String 33 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv34_daily_energy'>PV String 34 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv35_daily_energy'>PV String 35 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv36_daily_energy'>PV String 36 Daily Production</a><br>
<a href='#sigen_0_inverter_1_pv1_lifetime_energy'>PV String 1 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv2_lifetime_energy'>PV String 2 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv3_lifetime_energy'>PV String 3 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv4_lifetime_energy'>PV String 4 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv5_lifetime_energy'>PV String 5 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv6_lifetime_energy'>PV String 6 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv7_lifetime_energy'>PV String 7 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv8_lifetime_energy'>PV String 8 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv9_lifetime_energy'>PV String 9 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv10_lifetime_energy'>PV String 10 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv11_lifetime_energy'>PV String 11 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv12_lifetime_energy'>PV String 12 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv13_lifetime_energy'>PV String 13 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv14_lifetime_energy'>PV String 14 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv15_lifetime_energy'>PV String 15 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv16_lifetime_energy'>PV String 16 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv17_lifetime_energy'>PV String 17 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv18_lifetime_energy'>PV String 18 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv19_lifetime_energy'>PV String 19 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv20_lifetime_energy'>PV String 20 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv21_lifetime_energy'>PV String 21 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv22_lifetime_energy'>PV String 22 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv23_lifetime_energy'>PV String 23 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv24_lifetime_energy'>PV String 24 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv25_lifetime_energy'>PV String 25 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv26_lifetime_energy'>PV String 26 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv27_lifetime_energy'>PV String 27 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv28_lifetime_energy'>PV String 28 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv29_lifetime_energy'>PV String 29 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv30_lifetime_energy'>PV String 30 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv31_lifetime_energy'>PV String 31 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv32_lifetime_energy'>PV String 32 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv33_lifetime_energy'>PV String 33 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv34_lifetime_energy'>PV String 34 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv35_lifetime_energy'>PV String 35 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv36_lifetime_energy'>PV String 36 Lifetime Production</a><br>
<a href='#sigen_0_inverter_1_pv1_power'>PV String 1 Power</a><br>
<a href='#sigen_0_inverter_1_pv2_power'>PV String 2 Power</a><br>
<a href='#sigen_0_inverter_1_pv3_power'>PV String 3 Power</a><br>
<a href='#sigen_0_inverter_1_pv4_power'>PV String 4 Power</a><br>
<a href='#sigen_0_inverter_1_pv5_power'>PV String 5 Power</a><br>
<a href='#sigen_0_inverter_1_pv6_power'>PV String 6 Power</a><br>
<a href='#sigen_0_inverter_1_pv7_power'>PV String 7 Power</a><br>
<a href='#sigen_0_inverter_1_pv8_power'>PV String 8 Power</a><br>
<a href='#sigen_0_inverter_1_pv9_power'>PV String 9 Power</a><br>
<a href='#sigen_0_inverter_1_pv10_power'>PV String 10 Power</a><br>
<a href='#sigen_0_inverter_1_pv11_power'>PV String 11 Power</a><br>
<a href='#sigen_0_inverter_1_pv12_power'>PV String 12 Power</a><br>
<a href='#sigen_0_inverter_1_pv13_power'>PV String 13 Power</a><br>
<a href='#sigen_0_inverter_1_pv14_power'>PV String 14 Power</a><br>
<a href='#sigen_0_inverter_1_pv15_power'>PV String 15 Power</a><br>
<a href='#sigen_0_inverter_1_pv16_power'>PV String 16 Power</a><br>
<a href='#sigen_0_inverter_1_pv17_power'>PV String 17 Power</a><br>
<a href='#sigen_0_inverter_1_pv18_power'>PV String 18 Power</a><br>
<a href='#sigen_0_inverter_1_pv19_power'>PV String 19 Power</a><br>
<a href='#sigen_0_inverter_1_pv20_power'>PV String 20 Power</a><br>
<a href='#sigen_0_inverter_1_pv21_power'>PV String 21 Power</a><br>
<a href='#sigen_0_inverter_1_pv22_power'>PV String 22 Power</a><br>
<a href='#sigen_0_inverter_1_pv23_power'>PV String 23 Power</a><br>
<a href='#sigen_0_inverter_1_pv24_power'>PV String 24 Power</a><br>
<a href='#sigen_0_inverter_1_pv25_power'>PV String 25 Power</a><br>
<a href='#sigen_0_inverter_1_pv26_power'>PV String 26 Power</a><br>
<a href='#sigen_0_inverter_1_pv27_power'>PV String 27 Power</a><br>
<a href='#sigen_0_inverter_1_pv28_power'>PV String 28 Power</a><br>
<a href='#sigen_0_inverter_1_pv29_power'>PV String 29 Power</a><br>
<a href='#sigen_0_inverter_1_pv30_power'>PV String 30 Power</a><br>
<a href='#sigen_0_inverter_1_pv31_power'>PV String 31 Power</a><br>
<a href='#sigen_0_inverter_1_pv32_power'>PV String 32 Power</a><br>
<a href='#sigen_0_inverter_1_pv33_power'>PV String 33 Power</a><br>
<a href='#sigen_0_inverter_1_pv34_power'>PV String 34 Power</a><br>
<a href='#sigen_0_inverter_1_pv35_power'>PV String 35 Power</a><br>
<a href='#sigen_0_inverter_1_pv36_power'>PV String 36 Power</a><br>
<a href='#sigen_0_001_31027'>PV String 1 Voltage</a><br>
<a href='#sigen_0_001_31029'>PV String 2 Voltage</a><br>
<a href='#sigen_0_001_31031'>PV String 3 Voltage</a><br>
<a href='#sigen_0_001_31033'>PV String 4 Voltage</a><br>
<a href='#sigen_0_001_31042'>PV String 5 Voltage</a><br>
<a href='#sigen_0_001_31044'>PV String 6 Voltage</a><br>
<a href='#sigen_0_001_31046'>PV String 7 Voltage</a><br>
<a href='#sigen_0_001_31048'>PV String 8 Voltage</a><br>
<a href='#sigen_0_001_31050'>PV String 9 Voltage</a><br>
<a href='#sigen_0_001_31052'>PV String 10 Voltage</a><br>
<a href='#sigen_0_001_31054'>PV String 11 Voltage</a><br>
<a href='#sigen_0_001_31056'>PV String 12 Voltage</a><br>
<a href='#sigen_0_001_31058'>PV String 13 Voltage</a><br>
<a href='#sigen_0_001_31060'>PV String 14 Voltage</a><br>
<a href='#sigen_0_001_31062'>PV String 15 Voltage</a><br>
<a href='#sigen_0_001_31064'>PV String 16 Voltage</a><br>
<a href='#sigen_0_001_31066'>PV String 17 Voltage</a><br>
<a href='#sigen_0_001_31068'>PV String 18 Voltage</a><br>
<a href='#sigen_0_001_31070'>PV String 19 Voltage</a><br>
<a href='#sigen_0_001_31072'>PV String 20 Voltage</a><br>
<a href='#sigen_0_001_31074'>PV String 21 Voltage</a><br>
<a href='#sigen_0_001_31076'>PV String 22 Voltage</a><br>
<a href='#sigen_0_001_31078'>PV String 23 Voltage</a><br>
<a href='#sigen_0_001_31080'>PV String 24 Voltage</a><br>
<a href='#sigen_0_001_31082'>PV String 25 Voltage</a><br>
<a href='#sigen_0_001_31084'>PV String 26 Voltage</a><br>
<a href='#sigen_0_001_31086'>PV String 27 Voltage</a><br>
<a href='#sigen_0_001_31088'>PV String 28 Voltage</a><br>
<a href='#sigen_0_001_31090'>PV String 29 Voltage</a><br>
<a href='#sigen_0_001_31092'>PV String 30 Voltage</a><br>
<a href='#sigen_0_001_31094'>PV String 31 Voltage</a><br>
<a href='#sigen_0_001_31096'>PV String 32 Voltage</a><br>
<a href='#sigen_0_001_31098'>PV String 33 Voltage</a><br>
<a href='#sigen_0_001_31100'>PV String 34 Voltage</a><br>
<a href='#sigen_0_001_31102'>PV String 35 Voltage</a><br>
<a href='#sigen_0_001_31104'>PV String 36 Voltage</a><br>

<h6>AC Charger</h6>
<a href='#sigen_0_ac_charger_2_alarm'>Alarms</a><br>
<a href='#sigen_0_002_32003'>Charging Power</a><br>
<a href='#sigen_0_002_32010'>Input Breaker</a><br>
<a href='#sigen_0_002_42001'>Output Current</a><br>
<a href='#sigen_0_002_32007'>Rated Current</a><br>
<a href='#sigen_0_002_32005'>Rated Power</a><br>
<a href='#sigen_0_002_32009'>Rated Voltage</a><br>
<a href='#sigen_0_002_32000'>Running State</a><br>
<a href='#sigen_0_002_32001'>Total Energy Consumed</a><br>

<h6>DC Charger</h6>
<a href='#sigen_0_001_30609'>Alarms</a><br>
<a href='#sigen_0_001_31505'>Current Charging Capacity</a><br>
<a href='#sigen_0_001_31507'>Current Charging Duration</a><br>
<a href='#sigen_0_001_31502'>Output Power</a><br>
<a href='#sigen_0_001_31513'>Running State</a><br>
<a href='#sigen_0_001_31500'>Vehicle Battery Voltage</a><br>
<a href='#sigen_0_001_31501'>Vehicle Charging Current</a><br>
<a href='#sigen_0_001_31504'>Vehicle SoC</a><br>

<h6>Smart-Port (Enphase Envoy only)</h6>
<a href='#sigen_0_enphase_123456789012_current'>Current</a><br>
<a href='#sigen_0_enphase_123456789012_daily_pv_energy'>Daily Production</a><br>
<a href='#sigen_0_enphase_123456789012_frequency'>Frequency</a><br>
<a href='#sigen_0_enphase_123456789012_lifetime_pv_energy'>Lifetime Production</a><br>
<a href='#sigen_0_enphase_123456789012_active_power'>PV Power</a><br>
<a href='#sigen_0_enphase_123456789012_power_factor'>Power Factor</a><br>
<a href='#sigen_0_enphase_123456789012_reactive_power'>Reactive Power</a><br>
<a href='#sigen_0_enphase_123456789012_voltage'>Voltage</a><br>

<h6>Metrics</h6>
<a href='#sigen_modbus_locks'>Modbus Active Locks</a><br>
<a href='#sigen_modbus_cache_hit_percentage'>Modbus Cache Hits</a><br>
<a href='#sigen_modbus_read_errors'>Modbus Read Errors</a><br>
<a href='#sigen_modbus_read_max'>Modbus Read Max</a><br>
<a href='#sigen_modbus_read_mean'>Modbus Read Mean</a><br>
<a href='#sigen_modbus_read_min'>Modbus Read Min</a><br>
<a href='#sigen_modbus_reads_sec'>Modbus Reads/second</a><br>
<a href='#sigen_modbus_write_errors'>Modbus Write Errors</a><br>
<a href='#sigen_modbus_write_max'>Modbus Write Max</a><br>
<a href='#sigen_modbus_write_mean'>Modbus Write Mean</a><br>
<a href='#sigen_modbus_write_min'>Modbus Write Min</a><br>
<a href='#sigen_modbus_protocol_published'>Protocol Published</a><br>
<a href='#sigen_modbus_protocol'>Protocol Version</a><br>
<a href='#sigen_started'>Started</a><br>
</td><td>

<h6>Plant</h6>
<a href='#sigen_0_247_40001_set'>Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40005_set'>Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40049_set'>Active Power Regulation Gradient</a><br>
<a href='#sigen_0_247_40046_set'>Backup SoC</a><br>
<a href='#sigen_0_247_40047_set'>Charge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40048_set'>Discharge Cut-Off SoC</a><br>
<a href='#sigen_0_247_40038_set'>Grid Max Export Limit</a><br>
<a href='#sigen_0_247_40040_set'>Grid Max Import Limit</a><br>
<a href='#sigen_0_247_40030_set'>Independent Phase Power Control</a><br>
<a href='#sigen_0_247_40032_set'>Max Charging Limit</a><br>
<a href='#sigen_0_247_40034_set'>Max Discharging Limit</a><br>
<a href='#sigen_0_247_40042_set'>PCS Max Export Limit</a><br>
<a href='#sigen_0_247_40044_set'>PCS Max Import Limit</a><br>
<a href='#sigen_0_247_40036_set'>PV Max Power Limit</a><br>
<a href='#sigen_0_247_40008_set'>Phase A Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40020_set'>Phase A Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40023_set'>Phase A Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40014_set'>Phase A Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40010_set'>Phase B Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40021_set'>Phase B Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40024_set'>Phase B Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40016_set'>Phase B Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40012_set'>Phase C Active Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40022_set'>Phase C Active Power Percentage Adjustment Target Value</a><br>
<a href='#sigen_0_247_40025_set'>Phase C Q/S Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40018_set'>Phase C Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40000_set'>Plant Power On/Off</a><br>
<a href='#sigen_0_247_40007_set'>Power Factor Adjustment Target Value</a><br>
<a href='#sigen_0_247_40006_set'>Q/S Adjustment Target Value</a><br>
<a href='#sigen_0_247_40003_set'>Reactive Power Fixed Adjustment Target Value</a><br>
<a href='#sigen_0_247_40029_set'>Remote EMS</a><br>
<a href='#sigen_0_247_40031_set'>Remote EMS Control Mode</a><br>

<h6>Inverter</h6>
<a href='#sigen_0_001_41501_set'>Active Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_41505_set'>Active Power Percentage Adjustment</a><br>
<a href='#sigen_0_001_40500_set'>Inverter Power On/Off</a><br>
<a href='#sigen_0_001_41507_set'>Power Factor Adjustment</a><br>
<a href='#sigen_0_001_41503_set'>Reactive Power Fixed Value Adjustment</a><br>
<a href='#sigen_0_001_41506_set'>Reactive Power Q/S Adjustment</a><br>

<h6>AC Charger</h6>
<a href='#sigen_0_002_42000_set'>AC Charger Stop/Start</a><br>
<a href='#sigen_0_002_42001_set'>Output Current</a><br>

<h6>DC Charger</h6>
<a href='#sigen_0_001_41000_set'>DC Charger Stop/Start</a><br>
<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br></td></tr>
</table>

## Published Topics

### Plant
<h5><a id='sigen_0_247_30031'>Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power/state</td></tr>
<tr><td>Source</td><td>30031</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_40001'>Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40001</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40005'>Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40005</td></tr>
<tr><td>Comment</td><td>Range: [-100.00,100.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40049'>Active Power Regulation Gradient</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ActivePowerRegulationGradient</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%/s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_active_power_regulation_gradient</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_regulation_gradient/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_regulation_gradient/state</td></tr>
<tr><td>Source</td><td>40049 (may not be available on all devices)</td></tr>
<tr><td>Comment</td><td>Range:[0,5000]。Percentage of rated power adjusted per second</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30039'>Available Max Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMaxActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_max_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_active_power/state</td></tr>
<tr><td>Source</td><td>30039</td></tr>
<tr><td>Comment</td><td>Feed to the AC terminal. Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30064'>Available Max Charging Capacity</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMaxChargingCapacity</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_max_charging_capacity</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_capacity/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_charging_capacity/state</td></tr>
<tr><td>Source</td><td>30064</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30047'>Available Max Charging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMaxChargingPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_max_charging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_charging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_charging_power/state</td></tr>
<tr><td>Source</td><td>30047</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30066'>Available Max Discharging Capacity</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMaxDischargingCapacity</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_max_discharging_capacity</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_capacity/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_discharging_capacity/state</td></tr>
<tr><td>Source</td><td>30066</td></tr>
<tr><td>Comment</td><td>Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30049'>Available Max Discharging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMaxDischargingPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_max_discharging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_discharging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_discharging_power/state</td></tr>
<tr><td>Source</td><td>30049</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30043'>Available Max Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMaxReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_max_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_max_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_max_reactive_power/state</td></tr>
<tr><td>Source</td><td>30043</td></tr>
<tr><td>Comment</td><td>Feed to the AC terminal. Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_247_30041'>Available Min Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMinActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_min_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_min_active_power/state</td></tr>
<tr><td>Source</td><td>30041</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30045'>Available Min Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableMinReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_available_min_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_available_min_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_available_min_reactive_power/state</td></tr>
<tr><td>Source</td><td>30045</td></tr>
<tr><td>Comment</td><td>Absorb from the AC terminal. Count only the running inverters</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_247_40046'>Backup SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ESSBackupSOC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_ess_backup_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/state</td></tr>
<tr><td>Source</td><td>40046</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_battery_charging_power'>Battery Charging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>BatteryChargingPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_battery_charging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_charging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_battery_charging_power/state</td></tr>
<tr><td>Source</td><td>BatteryPower &gt; 0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_battery_discharging_power'>Battery Discharging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>BatteryDischargingPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_battery_discharging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_battery_discharging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_battery_discharging_power/state</td></tr>
<tr><td>Source</td><td>BatteryPower &lt; 0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30037'>Battery Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>BatteryPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_battery_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_power/state</td></tr>
<tr><td>Source</td><td>30037</td></tr>
<tr><td>Comment</td><td>ESS Power: <0 = discharging >0 = charging</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30014'>Battery SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantBatterySoC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_battery_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_soc/state</td></tr>
<tr><td>Source</td><td>30014</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30087'>Battery SoH</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantBatterySoH</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_battery_soh</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_battery_soh/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_battery_soh/state</td></tr>
<tr><td>Source</td><td>30087</td></tr>
<tr><td>Comment</td><td>This value is the weighted average of the SOH of all ESS devices in the power plant, with each rated capacity as the weight</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30085'>Charge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ChargeCutOffSoC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_charge_cut_off_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_charge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>30085</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_40047'>Charge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ESSChargeCutOffSOC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_ess_charge_cut_off_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>40047</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_consumed_power'>Consumed Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantConsumedPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_consumed_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_consumed_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_consumed_power/state</td></tr>
<tr><td>Source</td><td><dl><dt>CALCULATED Configuration Option:</dt><dd>TotalPVPower &plus; GridSensorActivePower &minus; BatteryPower &minus; ACChargerChargingPower &minus; DCChargerOutputPower</dd><dt>TOTAL Configuration Option:</dt><dd>TotalLoadPower (Protocol V2.8+ only)</dd><dt>GENERAL Configuration Option:</dt><dd>GeneralLoadPower (Protocol V2.8+ only)</dd></dl></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30279'>Current Control Command Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>CurrentControlCommandValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_current_control_command_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_current_control_command_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_current_control_command_value/state</td></tr>
<tr><td>Source</td><td>30279 (may not be available on all devices)</td></tr>
<tr><td>Comment</td><td>Use of Remote Output Control in Japan</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30072'>DC Charger Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GeneralAlarm5</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_general_alarm_5</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_5/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_5/state</td></tr>
<tr><td>Source</td><td>30072</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_daily_charge_energy'>Daily Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantDailyChargeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_daily_charge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_charge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_daily_charge_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of DailyChargeEnergy across all Inverters associated with the Plant</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_daily_consumed_energy'>Daily Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>TotalLoadDailyConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_daily_consumed_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_consumed_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_daily_consumed_energy/state</td></tr>
<tr><td>Source</td><td>30092</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be a maximum of 500000.0</td></tr>
</table>
<h5><a id='sigen_0_daily_discharge_energy'>Daily Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantDailyDischargeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_daily_discharge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_discharge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_daily_discharge_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of DailyDischargeEnergy across all Inverters associated with the Plant</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_daily_pv_energy'>Daily PV Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantDailyPVEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_daily_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_daily_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_total_daily_pv_energy'>Daily Total PV Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>TotalDailyPVEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_total_daily_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_daily_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_total_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>TotalLifetimePVEnergy &minus; TotalLifetimePVEnergy at last midnight</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30086'>Discharge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DischargeCutOffSoC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_discharge_cut_off_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_discharge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>30086</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_40048'>Discharge Cut-Off SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ESSDischargeCutOffSOC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_ess_discharge_cut_off_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/state</td></tr>
<tr><td>Source</td><td>40048</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30003'>EMS Work Mode</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EMSWorkMode</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_ems_work_mode</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_ems_work_mode/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_ems_work_mode/state</td></tr>
<tr><td>Source</td><td>30003</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>Max Self Consumption</li><li value='1'>Sigen AI</li><li value='2'>Time of Use</li><li value='5'>Full Feed-in to Grid</li><li value='6'>VPP Scheduling</li><li value='7'>Remote EMS</li><li value='9'>Time-Based Control</li></ol></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30029'>ESS Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GeneralAlarm3</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_general_alarm_3</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_3/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_3/state</td></tr>
<tr><td>Source</td><td>30029</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30030'>Gateway Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GeneralAlarm4</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_general_alarm_4</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_alarm_4/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_general_alarm_4/state</td></tr>
<tr><td>Source</td><td>30030</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30282'>General Load Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GeneralLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_general_load_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_load_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_general_load_power/state</td></tr>
<tr><td>Source</td><td>30282</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_40038'>Grid Max Export Limit</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridMaxExportLimit</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_max_export_limit</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/state</td></tr>
<tr><td>Source</td><td>40038</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40040'>Grid Max Import Limit</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridMaxImportLimit</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_max_import_limit</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/state</td></tr>
<tr><td>Source</td><td>40040</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40030'>Independent Phase Power Control</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>IndependentPhasePowerControl</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_independent_phase_power_control</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/state</td></tr>
<tr><td>Source</td><td>40030</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_accumulated_charge_energy'>Lifetime Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ESSTotalChargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_accumulated_charge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_charge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_accumulated_charge_energy/state</td></tr>
<tr><td>Source</td><td>30200</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_lifetime_consumed_energy'>Lifetime Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>TotalLoadConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_lifetime_consumed_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_consumed_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_lifetime_consumed_energy/state</td></tr>
<tr><td>Source</td><td>30094</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30208'>Lifetime DC EV Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EVDCTotalChargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_evdc_total_charge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_evdc_total_charge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_evdc_total_charge_energy/state</td></tr>
<tr><td>Source</td><td>30208</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30212'>Lifetime DC EV Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EVDCTotalDischargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_evdc_total_discharge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_evdc_total_discharge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_evdc_total_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30212</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_accumulated_discharge_energy'>Lifetime Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ESSTotalDischargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_accumulated_discharge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_accumulated_discharge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_accumulated_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30204</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30224'>Lifetime Generator Output Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantTotalGeneratorOutputEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_total_generator_output_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_total_generator_output_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_total_generator_output_energy/state</td></tr>
<tr><td>Source</td><td>30224</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30088'>Lifetime PV Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPVTotalGeneration</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_lifetime_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>30088</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30196'>Lifetime Third-Party PV Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ThirdPartyLifetimePVEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_third_party_pv_lifetime_production</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_third_party_pv_lifetime_production/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_third_party_pv_lifetime_production/state</td></tr>
<tr><td>Source</td><td>30196</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_lifetime_pv_energy'>Lifetime Total PV Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>TotalLifetimePVEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_lifetime_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>&sum; of PlantPVTotalGeneration and ThirdPartyLifetimePVEnergy</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30010'>Max Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_max_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_active_power/state</td></tr>
<tr><td>Source</td><td>30010</td></tr>
<tr><td>Comment</td><td>This should be the base value of all active power adjustment actions</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30012'>Max Apparent Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxApparentPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kVA</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_max_apparent_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_max_apparent_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_apparent_power/state</td></tr>
<tr><td>Source</td><td>30012</td></tr>
<tr><td>Comment</td><td>This should be the base value of all reactive power adjustment actions</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_247_40032'>Max Charging Limit</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxChargingLimit</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_max_charging_limit</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/state</td></tr>
<tr><td>Source</td><td>40032</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Charging</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40034'>Max Discharging Limit</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxDischargingLimit</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_max_discharging_limit</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/state</td></tr>
<tr><td>Source</td><td>40034</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Discharging</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_general_pcs_alarm'>PCS Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GeneralPCSAlarm</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_general_pcs_alarm</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_general_pcs_alarm/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_general_pcs_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 30027 and 30028</td></tr>
<tr><td>Comment</td><td>If any hybrid inverter has alarm, then this alarm will be set accordingly</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40042'>PCS Max Export Limit</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PCSMaxExportLimit</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_pcs_max_export_limit</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/state</td></tr>
<tr><td>Source</td><td>40042</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40044'>PCS Max Import Limit</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PCSMaxImportLimit</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_pcs_max_import_limit</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/state</td></tr>
<tr><td>Source</td><td>40044</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40036'>PV Max Power Limit</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVMaxPowerLimit</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_pv_max_power_limit</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/state</td></tr>
<tr><td>Source</td><td>40036</td></tr>
<tr><td>Comment</td><td>Takes effect when Remote EMS control mode (40031) is set to Command Charging/Discharging</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30035'>PV Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPVPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_pv_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_pv_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_power/state</td></tr>
<tr><td>Source</td><td>30035</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30015'>Phase A Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPhaseActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_a_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power/state</td></tr>
<tr><td>Source</td><td>30015</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_40008'>Phase A Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40008</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40020'>Phase A Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40020</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40023'>Phase A Q/S Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseQSAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40023</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30021'>Phase A Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPhaseReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_a_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power/state</td></tr>
<tr><td>Source</td><td>30021</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_247_40014'>Phase A Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40014</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30017'>Phase B Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPhaseActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_b_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power/state</td></tr>
<tr><td>Source</td><td>30017</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_40010'>Phase B Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40010</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40021'>Phase B Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40021</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40024'>Phase B Q/S Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseQSAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40024</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30023'>Phase B Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPhaseReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_b_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power/state</td></tr>
<tr><td>Source</td><td>30023</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_247_40016'>Phase B Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40016</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30019'>Phase C Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPhaseActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_c_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power/state</td></tr>
<tr><td>Source</td><td>30019</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_40012'>Phase C Active Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseActivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40012</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40022'>Phase C Active Power Percentage Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseActivePowerPercentageAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40022</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40025'>Phase C Q/S Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseQSAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40025</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30025'>Phase C Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantPhaseReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_c_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power/state</td></tr>
<tr><td>Source</td><td>30025</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_247_40018'>Phase C Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40018</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_plant_alarms'>Plant Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantAlarms</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_alarms</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_alarms/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_alarms/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 30280 and 30281</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40007'>Power Factor Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PowerFactorAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_power_factor_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40007</td></tr>
<tr><td>Comment</td><td>Range: [(-1.0, -0.8) U (0.8, 1.0)]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40006'>Q/S Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>QSAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_q_s_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40006</td></tr>
<tr><td>Comment</td><td>Range: [-60.0,60.00]. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_30068'>Rated Charging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantRatedChargingPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_rated_charging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_charging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>30068</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30070'>Rated Discharging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantRatedDischargingPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_rated_discharging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_discharging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_discharging_power/state</td></tr>
<tr><td>Source</td><td>30070</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30083'>Rated Energy Capacity</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantRatedEnergyCapacity</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_rated_energy_capacity</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_rated_energy_capacity/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_rated_energy_capacity/state</td></tr>
<tr><td>Source</td><td>30083</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30033'>Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power/state</td></tr>
<tr><td>Source</td><td>30033</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_247_40003'>Reactive Power Fixed Adjustment Target Value</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ReactivePowerFixedAdjustmentTargetValue</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_reactive_power_fixed_adjustment_target_value</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/state</td></tr>
<tr><td>Source</td><td>40003</td></tr>
<tr><td>Comment</td><td>Range: [-60.00 * base value ,60.00 * base value]. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_247_40029'>Remote EMS</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RemoteEMS</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_remote_ems</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/state</td></tr>
<tr><td>Source</td><td>40029</td></tr>
<tr><td>Comment</td><td>When needed to control EMS remotely, this register needs to be enabled. When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_40031'>Remote EMS Control Mode</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RemoteEMSControlMode</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_remote_ems_control_mode</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/select/sigen_0_247_powerplant/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/state</td></tr>
<tr><td>Source</td><td>40031</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>PCS remote control</li><li value='1'>Standby</li><li value='2'>Maximum Self-consumption (Default)</li><li value='3'>Command Charging (Consume power from the grid first)</li><li value='4'>Command Charging (Consume power from the PV first)</li><li value='5'>Command Discharging (Output power from PV first)</li><li value='6'>Command Discharging (Output power from the battery first)</li></ol></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30051'>Running State</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantRunningState</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_running_state</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_running_state/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_running_state/state</td></tr>
<tr><td>Source</td><td>30051</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>Standby</li><li value='1'>Normal</li><li value='2'>Fault</li><li value='3'>Power-Off</li><li value='7'>Environmental Abnormality</li></ol></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30146'>Smart Load 01 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_01_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_01_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_01_power/state</td></tr>
<tr><td>Source</td><td>30146</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30098'>Smart Load 01 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_01_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_01_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_01_total_consumption/state</td></tr>
<tr><td>Source</td><td>30098</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30148'>Smart Load 02 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_02_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_02_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_02_power/state</td></tr>
<tr><td>Source</td><td>30148</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30100'>Smart Load 02 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_02_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_02_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_02_total_consumption/state</td></tr>
<tr><td>Source</td><td>30100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30150'>Smart Load 03 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_03_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_03_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_03_power/state</td></tr>
<tr><td>Source</td><td>30150</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30102'>Smart Load 03 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_03_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_03_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_03_total_consumption/state</td></tr>
<tr><td>Source</td><td>30102</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30152'>Smart Load 04 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_04_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_04_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_04_power/state</td></tr>
<tr><td>Source</td><td>30152</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30104'>Smart Load 04 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_04_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_04_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_04_total_consumption/state</td></tr>
<tr><td>Source</td><td>30104</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30154'>Smart Load 05 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_05_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_05_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_05_power/state</td></tr>
<tr><td>Source</td><td>30154</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30106'>Smart Load 05 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_05_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_05_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_05_total_consumption/state</td></tr>
<tr><td>Source</td><td>30106</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30156'>Smart Load 06 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_06_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_06_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_06_power/state</td></tr>
<tr><td>Source</td><td>30156</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30108'>Smart Load 06 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_06_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_06_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_06_total_consumption/state</td></tr>
<tr><td>Source</td><td>30108</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30158'>Smart Load 07 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_07_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_07_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_07_power/state</td></tr>
<tr><td>Source</td><td>30158</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30110'>Smart Load 07 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_07_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_07_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_07_total_consumption/state</td></tr>
<tr><td>Source</td><td>30110</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30160'>Smart Load 08 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_08_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_08_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_08_power/state</td></tr>
<tr><td>Source</td><td>30160</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30112'>Smart Load 08 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_08_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_08_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_08_total_consumption/state</td></tr>
<tr><td>Source</td><td>30112</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30162'>Smart Load 09 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_09_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_09_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_09_power/state</td></tr>
<tr><td>Source</td><td>30162</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30114'>Smart Load 09 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_09_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_09_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_09_total_consumption/state</td></tr>
<tr><td>Source</td><td>30114</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30164'>Smart Load 10 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_10_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_10_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_10_power/state</td></tr>
<tr><td>Source</td><td>30164</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30116'>Smart Load 10 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_10_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_10_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_10_total_consumption/state</td></tr>
<tr><td>Source</td><td>30116</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30166'>Smart Load 11 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_11_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_11_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_11_power/state</td></tr>
<tr><td>Source</td><td>30166</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30118'>Smart Load 11 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_11_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_11_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_11_total_consumption/state</td></tr>
<tr><td>Source</td><td>30118</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30168'>Smart Load 12 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_12_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_12_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_12_power/state</td></tr>
<tr><td>Source</td><td>30168</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30120'>Smart Load 12 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_12_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_12_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_12_total_consumption/state</td></tr>
<tr><td>Source</td><td>30120</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30170'>Smart Load 13 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_13_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_13_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_13_power/state</td></tr>
<tr><td>Source</td><td>30170</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30122'>Smart Load 13 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_13_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_13_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_13_total_consumption/state</td></tr>
<tr><td>Source</td><td>30122</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30172'>Smart Load 14 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_14_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_14_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_14_power/state</td></tr>
<tr><td>Source</td><td>30172</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30124'>Smart Load 14 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_14_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_14_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_14_total_consumption/state</td></tr>
<tr><td>Source</td><td>30124</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30174'>Smart Load 15 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_15_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_15_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_15_power/state</td></tr>
<tr><td>Source</td><td>30174</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30126'>Smart Load 15 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_15_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_15_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_15_total_consumption/state</td></tr>
<tr><td>Source</td><td>30126</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30176'>Smart Load 16 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_16_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_16_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_16_power/state</td></tr>
<tr><td>Source</td><td>30176</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30128'>Smart Load 16 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_16_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_16_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_16_total_consumption/state</td></tr>
<tr><td>Source</td><td>30128</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30178'>Smart Load 17 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_17_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_17_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_17_power/state</td></tr>
<tr><td>Source</td><td>30178</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30130'>Smart Load 17 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_17_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_17_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_17_total_consumption/state</td></tr>
<tr><td>Source</td><td>30130</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30180'>Smart Load 18 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_18_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_18_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_18_power/state</td></tr>
<tr><td>Source</td><td>30180</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30132'>Smart Load 18 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_18_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_18_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_18_total_consumption/state</td></tr>
<tr><td>Source</td><td>30132</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30182'>Smart Load 19 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_19_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_19_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_19_power/state</td></tr>
<tr><td>Source</td><td>30182</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30134'>Smart Load 19 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_19_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_19_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_19_total_consumption/state</td></tr>
<tr><td>Source</td><td>30134</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30184'>Smart Load 20 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_20_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_20_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_20_power/state</td></tr>
<tr><td>Source</td><td>30184</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30136'>Smart Load 20 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_20_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_20_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_20_total_consumption/state</td></tr>
<tr><td>Source</td><td>30136</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30186'>Smart Load 21 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_21_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_21_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_21_power/state</td></tr>
<tr><td>Source</td><td>30186</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30138'>Smart Load 21 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_21_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_21_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_21_total_consumption/state</td></tr>
<tr><td>Source</td><td>30138</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30188'>Smart Load 22 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_22_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_22_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_22_power/state</td></tr>
<tr><td>Source</td><td>30188</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30140'>Smart Load 22 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_22_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_22_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_22_total_consumption/state</td></tr>
<tr><td>Source</td><td>30140</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30190'>Smart Load 23 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_23_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_23_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_23_power/state</td></tr>
<tr><td>Source</td><td>30190</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30142'>Smart Load 23 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_23_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_23_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_23_total_consumption/state</td></tr>
<tr><td>Source</td><td>30142</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30192'>Smart Load 24 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_24_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_24_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_24_power/state</td></tr>
<tr><td>Source</td><td>30192</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30144'>Smart Load 24 Total Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SmartLoadTotalConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_smart_load_24_total_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_smart_load_24_total_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_smart_load_24_total_consumption/state</td></tr>
<tr><td>Source</td><td>30144</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30000'>System Time</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SystemTime</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_system_time</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_system_time/state</td></tr>
<tr><td>Source</td><td>30000</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_247_30002'>System Time Zone</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SystemTimeZone</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_system_time_zone</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_plant_system_time_zone/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_system_time_zone/state</td></tr>
<tr><td>Source</td><td>30002</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_247_30194'>Third-Party PV Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ThirdPartyPVPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_third_party_pv_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_third_party_pv_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_third_party_pv_power/state</td></tr>
<tr><td>Source</td><td>30194</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30284'>Total Load Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>TotalLoadPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_total_load_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_load_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_total_load_power/state</td></tr>
<tr><td>Source</td><td>30284</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_total_pv_power'>Total PV Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>TotalPVPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_total_pv_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_powerplant/sigen_0_total_pv_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_total_pv_power/state</td></tr>
<tr><td>Source</td><td>PV Power + (sum of all Smart-Port PV Power sensors)</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>

#### Grid Sensor
<h5><a id='sigen_0_247_30005'>Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridSensorActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_sensor_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_active_power/state</td></tr>
<tr><td>Source</td><td>30005</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -100000 and 100000</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_daily_export_energy'>Daily Exported Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridSensorDailyExportEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_grid_sensor_daily_export_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_export_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_daily_export_energy/state</td></tr>
<tr><td>Source</td><td>PlantTotalExportedEnergy &minus; PlantTotalExportedEnergy at last midnight</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_daily_import_energy'>Daily Imported Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridSensorDailyImportEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_grid_sensor_daily_import_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_daily_import_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_daily_import_energy/state</td></tr>
<tr><td>Source</td><td>PlantTotalImportedEnergy &minus; PlantTotalImportedEnergy at last midnight</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_export_power'>Export Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridSensorExportPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_grid_sensor_export_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_export_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_export_power/state</td></tr>
<tr><td>Source</td><td>GridSensorActivePower &lt; 0 &times; -1</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30004'>Grid Sensor Status</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridSensorStatus</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_sensor_status</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_status/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_status/state</td></tr>
<tr><td>Source</td><td>30004</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>Not Connected</li><li value='1'>Connected</li></ol></td></tr>
<tr><td>Comment</td><td>Gateway or meter connection status</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_247_30009'>Grid Status</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridStatus</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_status</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_status/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_status/state</td></tr>
<tr><td>Source</td><td>30009</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>On Grid</li><li value='1'>Off Grid (auto)</li><li value='2'>Off Grid (manual)</li></ol></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_import_power'>Import Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridSensorImportPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_grid_sensor_import_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_import_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_import_power/state</td></tr>
<tr><td>Source</td><td>GridSensorActivePower &gt; 0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_lifetime_export_energy'>Lifetime Exported Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantTotalExportedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_grid_sensor_lifetime_export_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_export_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_lifetime_export_energy/state</td></tr>
<tr><td>Source</td><td>30220</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_grid_sensor_lifetime_import_energy'>Lifetime Imported Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PlantTotalImportedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_grid_sensor_lifetime_import_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_grid_sensor_lifetime_import_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_grid_sensor_lifetime_import_energy/state</td></tr>
<tr><td>Source</td><td>30216</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30052'>Phase A Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridPhaseActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_phase_a_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_a_active_power/state</td></tr>
<tr><td>Source</td><td>30052</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30058'>Phase A Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridPhaseReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_phase_a_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_a_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_a_reactive_power/state</td></tr>
<tr><td>Source</td><td>30058</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_247_30054'>Phase B Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridPhaseActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_phase_b_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_b_active_power/state</td></tr>
<tr><td>Source</td><td>30054</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30060'>Phase B Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridPhaseReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_phase_b_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_b_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_b_reactive_power/state</td></tr>
<tr><td>Source</td><td>30060</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_247_30056'>Phase C Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridPhaseActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_phase_c_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_c_active_power/state</td></tr>
<tr><td>Source</td><td>30056</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30062'>Phase C Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridPhaseReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_phase_c_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_phase_c_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_phase_c_reactive_power/state</td></tr>
<tr><td>Source</td><td>30062</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_247_30007'>Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridSensorReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>var</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_plant_grid_sensor_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_gridsensor/sigen_0_plant_grid_sensor_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_sensor_reactive_power/state</td></tr>
<tr><td>Source</td><td>30007</td></tr>
<tr><td>Comment</td><td>Data collected from grid sensor at grid to system checkpoint</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>

#### Statistics
<h5><a id='sigen_0_247_30232'>Total AC EV Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalEVACChargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_ev_ac_charged_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_ev_ac_charged_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_ev_ac_charged_energy/state</td></tr>
<tr><td>Source</td><td>30232</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30244'>Total Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalChargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_charged_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_charged_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_charged_energy/state</td></tr>
<tr><td>Source</td><td>30244</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30228'>Total Common Load Consumption</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalCommonLoadConsumption</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_common_load_consumption</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_common_load_consumption/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_common_load_consumption/state</td></tr>
<tr><td>Source</td><td>30228</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30252'>Total DC EV Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalEVDCChargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_evdc_total_charge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_evdc_total_charge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_evdc_total_charge_energy/state</td></tr>
<tr><td>Source</td><td>30252</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30256'>Total DC EV Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalEVDCDischargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_evdc_total_discharge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_evdc_total_discharge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_evdc_total_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30256</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30248'>Total Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalDischargedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_discharged_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_discharged_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_discharged_energy/state</td></tr>
<tr><td>Source</td><td>30248</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30264'>Total Exported Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalExportedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_exported_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_exported_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_exported_energy/state</td></tr>
<tr><td>Source</td><td>30264</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30268'>Total Generator Output Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalGeneratorOutputEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_generator_output_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_generator_output_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_generator_output_energy/state</td></tr>
<tr><td>Source</td><td>30268</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30260'>Total Imported Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalImportedEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_imported_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_imported_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_imported_energy/state</td></tr>
<tr><td>Source</td><td>30260</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30236'>Total PV Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalSelfPVGeneration</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_self_pv_generation</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_self_pv_generation/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_self_pv_generation/state</td></tr>
<tr><td>Source</td><td>30236</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_247_30240'>Total Third-Party PV Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>SITotalThirdPartyPVGeneration</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_si_total_third_party_pv_generation</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_247_plantstatistics/sigen_0_si_total_third_party_pv_generation/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_si_total_third_party_pv_generation/state</td></tr>
<tr><td>Source</td><td>30240</td></tr>
<tr><td>Comment</td><td>After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.7</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>

### Inverter
<h5><a id='sigen_0_001_31005'>A-B Line Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>LineVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_a_b_line_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_a_b_line_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_a_b_line_voltage/state</td></tr>
<tr><td>Source</td><td>31005</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_30587'>Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power/state</td></tr>
<tr><td>Source</td><td>30587</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_41501'>Active Power Fixed Value Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterActivePowerFixedValueAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_active_power_fixed_value_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/state</td></tr>
<tr><td>Source</td><td>41501</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_30613'>Active Power Fixed Value Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterActivePowerFixedValueAdjustmentFeedback</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30613</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_41505'>Active Power Percentage Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterActivePowerPercentageAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_active_power_percentage_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/state</td></tr>
<tr><td>Source</td><td>41505</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_30617'>Active Power Percentage Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterActivePowerPercentageAdjustmentFeedback</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_active_power_percentage_adjustment_feedback</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30617</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31007'>B-C Line Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>LineVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_b_c_line_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_b_c_line_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_b_c_line_voltage/state</td></tr>
<tr><td>Source</td><td>31007</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_31009'>C-A Line Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>LineVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_c_a_line_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_c_a_line_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_c_a_line_voltage/state</td></tr>
<tr><td>Source</td><td>31009</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_daily_pv_energy'>Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterPVDailyGeneration</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_daily_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_daily_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>31509</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be a maximum of 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30525'>Firmware Version</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterFirmwareVersion</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_firmware_version</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_firmware_version/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_firmware_version/state</td></tr>
<tr><td>Source</td><td>30525</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_30608'>Gateway Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterAlarm4</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_alarm_4</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_alarm_4/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_4/state</td></tr>
<tr><td>Source</td><td>30608</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31002'>Grid Frequency</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>GridFrequency</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_grid_frequency</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_grid_frequency/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_grid_frequency/state</td></tr>
<tr><td>Source</td><td>31002</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31037'>Insulation Resistance</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InsulationResistance</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>MΩ</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_insulation_resistance</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_insulation_resistance/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_insulation_resistance/state</td></tr>
<tr><td>Source</td><td>31037</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_lifetime_pv_energy'>Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterPVLifetimeGeneration</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_lifetime_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>31511</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_31026'>MPTT Count</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MPTTCount</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_mptt_count</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_mptt_count/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_mptt_count/state</td></tr>
<tr><td>Source</td><td>31026</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30546'>Max Absorption Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxAbsorptionPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_absorption_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_absorption_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_absorption_power/state</td></tr>
<tr><td>Source</td><td>30546</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30544'>Max Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterMaxActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_active_power/state</td></tr>
<tr><td>Source</td><td>30544</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30579'>Max Active Power Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxActivePowerAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_active_power_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_active_power_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_active_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30579</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30542'>Max Rated Apparent Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxRatedApparentPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kVA</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_rated_apparent_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_rated_apparent_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_rated_apparent_power/state</td></tr>
<tr><td>Source</td><td>30542</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_30583'>Max Reactive Power Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxReactivePowerAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_reactive_power_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_max_reactive_power_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_reactive_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30583</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_30581'>Min Active Power Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MinActivePowerAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_min_active_power_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_active_power_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_active_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30581</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30585'>Min Reactive Power Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MinReactivePowerAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_min_reactive_power_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_min_reactive_power_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_reactive_power_adjustment/state</td></tr>
<tr><td>Source</td><td>30585</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_30500'>Model</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterModel</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_model</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_model/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_model/state</td></tr>
<tr><td>Source</td><td>30500</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_31004'>Output Type</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>OutputType</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_output_type</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_output_type/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_output_type/state</td></tr>
<tr><td>Source</td><td>31004</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>L/N</li><li value='1'>L1/L2/L3</li><li value='2'>L1/L2/L3/N</li><li value='3'>L1/L2/N</li></ol></td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31024'>PACK/BCU Count</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PACKBCUCount</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pack_bcu_count</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pack_bcu_count/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pack_bcu_count/state</td></tr>
<tr><td>Source</td><td>31024</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pcs_alarm'>PCS Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterPCSAlarm</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pcs_alarm</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pcs_alarm/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pcs_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 30605 and 30606</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_31035'>PV Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterPVPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv_power/state</td></tr>
<tr><td>Source</td><td>31035</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_31025'>PV String Count</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringCount</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv_string_count</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_pv_string_count/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv_string_count/state</td></tr>
<tr><td>Source</td><td>31025</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31017'>Phase A Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseCurrent</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_phase_a_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_a_current/state</td></tr>
<tr><td>Source</td><td>31017</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_001_31011'>Phase A Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_phase_a_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_a_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_a_voltage/state</td></tr>
<tr><td>Source</td><td>31011</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_31019'>Phase B Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseCurrent</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_phase_b_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_b_current/state</td></tr>
<tr><td>Source</td><td>31019</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_001_31013'>Phase B Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_phase_b_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_b_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_b_voltage/state</td></tr>
<tr><td>Source</td><td>31013</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_31021'>Phase C Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseCurrent</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_phase_c_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_c_current/state</td></tr>
<tr><td>Source</td><td>31021</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_001_31015'>Phase C Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PhaseVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_phase_c_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_phase_c_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_phase_c_voltage/state</td></tr>
<tr><td>Source</td><td>31015</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_31023'>Power Factor</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PowerFactor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_power_factor</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_power_factor/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor/state</td></tr>
<tr><td>Source</td><td>31023</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 1000</td></tr>
</table>
<h5><a id='sigen_0_001_41507'>Power Factor Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterPowerFactorAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_power_factor_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/state</td></tr>
<tr><td>Source</td><td>41507</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_30619'>Power Factor Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterPowerFactorAdjustmentFeedback</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_power_factor_adjustment_feedback</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment_feedback/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30619</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_30540'>Rated Active Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RatedActivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_rated_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_active_power/state</td></tr>
<tr><td>Source</td><td>30540</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_31001'>Rated Grid Frequency</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RatedGridFrequency</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_rated_grid_frequency</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_frequency/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_grid_frequency/state</td></tr>
<tr><td>Source</td><td>31001</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31000'>Rated Grid Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RatedGridVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_rated_grid_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_rated_grid_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_grid_voltage/state</td></tr>
<tr><td>Source</td><td>31000</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30589'>Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ReactivePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power/state</td></tr>
<tr><td>Source</td><td>30589</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_001_41503'>Reactive Power Fixed Value Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterReactivePowerFixedValueAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_fixed_value_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/state</td></tr>
<tr><td>Source</td><td>41503</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_30615'>Reactive Power Fixed Value Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterReactivePowerFixedValueAdjustmentFeedback</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30615</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_001_30618'>Reactive Power Percentage Adjustment Feedback</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterReactivePowerPercentageAdjustmentFeedback</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_percentage_adjustment_feedback/state</td></tr>
<tr><td>Source</td><td>30618</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_41506'>Reactive Power Q/S Adjustment</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterReactivePowerQSAdjustment</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_reactive_power_q_s_adjustment</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/state</td></tr>
<tr><td>Source</td><td>41506</td></tr>
<tr><td>Applicable To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_30578'>Running State</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterRunningState</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_running_state</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_running_state/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_running_state/state</td></tr>
<tr><td>Source</td><td>30578</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>Standby</li><li value='1'>Normal</li><li value='2'>Fault</li><li value='3'>Power-Off</li><li value='7'>Environmental Abnormality</li></ol></td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30515'>Serial Number</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterSerialNumber</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_serial_number</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_serial_number/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_serial_number/state</td></tr>
<tr><td>Source</td><td>30515</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_001_31040'>Shutdown Time</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ShutdownTime</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_shutdown_time</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_shutdown_time/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_shutdown_time/state</td></tr>
<tr><td>Source</td><td>31040</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_31038'>Startup Time</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>StartupTime</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_startup_time</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_startup_time/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_startup_time/state</td></tr>
<tr><td>Source</td><td>31038</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_31003'>Temperature</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterTemperature</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_temperature</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_inverter/sigen_0_inverter_1_temperature/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_temperature/state</td></tr>
<tr><td>Source</td><td>31003</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -400 and 2000</td></tr>
</table>

#### Energy Storage System
<h5><a id='sigen_0_001_30607'>Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterAlarm3</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_alarm_3</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_alarm_3/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_3/state</td></tr>
<tr><td>Source</td><td>30607</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30595'>Available Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableBatteryChargeEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_available_battery_charge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_charge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_available_battery_charge_energy/state</td></tr>
<tr><td>Source</td><td>30595</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30597'>Available Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AvailableBatteryDischargeEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_available_battery_discharge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_available_battery_discharge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_available_battery_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30597</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30603'>Average Cell Temperature</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AverageCellTemperature</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_average_cell_temperature</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_temperature/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_average_cell_temperature/state</td></tr>
<tr><td>Source</td><td>30603</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -400 and 2000</td></tr>
</table>
<h5><a id='sigen_0_001_30604'>Average Cell Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AverageCellVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_average_cell_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_average_cell_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_average_cell_voltage/state</td></tr>
<tr><td>Source</td><td>30604</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_battery_charging_power'>Battery Charging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterBatteryChargingPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_battery_charging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_charging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_charging_power/state</td></tr>
<tr><td>Source</td><td>ChargeDischargePower &gt; 0</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_battery_discharging_power'>Battery Discharging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterBatteryDischargingPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_battery_discharging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_discharging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_discharging_power/state</td></tr>
<tr><td>Source</td><td>ChargeDischargePower &lt; 0 &times; -1</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30599'>Battery Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ChargeDischargePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_charge_discharge_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_charge_discharge_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_charge_discharge_power/state</td></tr>
<tr><td>Source</td><td>30599</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30601'>Battery SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterBatterySoC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_battery_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_soc/state</td></tr>
<tr><td>Source</td><td>30601</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30602'>Battery SoH</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterBatterySoH</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_battery_soh</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_battery_soh/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_battery_soh/state</td></tr>
<tr><td>Source</td><td>30602</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30566'>Daily Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DailyChargeEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_daily_charge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_charge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_charge_energy/state</td></tr>
<tr><td>Source</td><td>30566</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be a maximum of 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30572'>Daily Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DailyDischargeEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_daily_discharge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_daily_discharge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_daily_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30572</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be a maximum of 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30568'>Lifetime Charge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AccumulatedChargeEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_accumulated_charge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_charge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_accumulated_charge_energy/state</td></tr>
<tr><td>Source</td><td>30568</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30574'>Lifetime Discharge Energy</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>AccumulatedDischargeEnergy</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_accumulated_discharge_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_accumulated_discharge_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_accumulated_discharge_energy/state</td></tr>
<tr><td>Source</td><td>30574</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30620'>Max Battery Temperature</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterMaxBatteryTemperature</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_battery_temperature</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_temperature/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_temperature/state</td></tr>
<tr><td>Source</td><td>30620</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -400 and 2000</td></tr>
</table>
<h5><a id='sigen_0_001_30622'>Max Cell Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterMaxCellVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_cell_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_cell_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_cell_voltage/state</td></tr>
<tr><td>Source</td><td>30622 (may not be available on all devices)</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30591'>Max Charge Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxBatteryChargePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_battery_charge_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_charge_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_charge_power/state</td></tr>
<tr><td>Source</td><td>30591</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30593'>Max Discharge Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>MaxBatteryDischargePower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_max_battery_discharge_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_max_battery_discharge_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_max_battery_discharge_power/state</td></tr>
<tr><td>Source</td><td>30593</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30621'>Min Battery Temperature</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterMinBatteryTemperature</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>°C</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_min_battery_temperature</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_min_battery_temperature/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_battery_temperature/state</td></tr>
<tr><td>Source</td><td>30621</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -400 and 2000</td></tr>
</table>
<h5><a id='sigen_0_001_30623'>Min Cell Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterMinCellVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_min_cell_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_min_cell_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_min_cell_voltage/state</td></tr>
<tr><td>Source</td><td>30623 (may not be available on all devices)</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_30548'>Rated Battery Capacity</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RatedBatteryCapacity</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_rated_battery_capacity</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_battery_capacity/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_battery_capacity/state</td></tr>
<tr><td>Source</td><td>30548</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30550'>Rated Charging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RatedChargingPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_rated_charging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_charging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>30550</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_30552'>Rated Discharging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>RatedDischargingPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_rated_discharging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_ess/sigen_0_inverter_1_rated_discharging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_rated_discharging_power/state</td></tr>
<tr><td>Source</td><td>30552</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>

#### PV String

The actual number of PV Strings is determined from `PV String Count` in the Inverter.
<h5><a id='sigen_0_001_31028'>PV String 1 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv1_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_current/state</td></tr>
<tr><td>Source</td><td>31028</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31030'>PV String 2 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv2_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_current/state</td></tr>
<tr><td>Source</td><td>31030</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31032'>PV String 3 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv3_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_current/state</td></tr>
<tr><td>Source</td><td>31032</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31034'>PV String 4 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv4_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_current/state</td></tr>
<tr><td>Source</td><td>31034</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31043'>PV String 5 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv5_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_current/state</td></tr>
<tr><td>Source</td><td>31043</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31045'>PV String 6 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv6_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_current/state</td></tr>
<tr><td>Source</td><td>31045</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31047'>PV String 7 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv7_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_current/state</td></tr>
<tr><td>Source</td><td>31047</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31049'>PV String 8 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv8_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_current/state</td></tr>
<tr><td>Source</td><td>31049</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31051'>PV String 9 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv9_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_current/state</td></tr>
<tr><td>Source</td><td>31051</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31053'>PV String 10 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv10_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_current/state</td></tr>
<tr><td>Source</td><td>31053</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31055'>PV String 11 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv11_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_current/state</td></tr>
<tr><td>Source</td><td>31055</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31057'>PV String 12 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv12_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_current/state</td></tr>
<tr><td>Source</td><td>31057</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31059'>PV String 13 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv13_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_current/state</td></tr>
<tr><td>Source</td><td>31059</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31061'>PV String 14 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv14_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_current/state</td></tr>
<tr><td>Source</td><td>31061</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31063'>PV String 15 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv15_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_current/state</td></tr>
<tr><td>Source</td><td>31063</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31065'>PV String 16 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv16_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_current/state</td></tr>
<tr><td>Source</td><td>31065</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31067'>PV String 17 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv17_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring17/sigen_0_inverter_1_pv17_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv17_current/state</td></tr>
<tr><td>Source</td><td>31067</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31069'>PV String 18 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv18_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring18/sigen_0_inverter_1_pv18_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv18_current/state</td></tr>
<tr><td>Source</td><td>31069</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31071'>PV String 19 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv19_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring19/sigen_0_inverter_1_pv19_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv19_current/state</td></tr>
<tr><td>Source</td><td>31071</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31073'>PV String 20 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv20_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring20/sigen_0_inverter_1_pv20_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv20_current/state</td></tr>
<tr><td>Source</td><td>31073</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31075'>PV String 21 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv21_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring21/sigen_0_inverter_1_pv21_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv21_current/state</td></tr>
<tr><td>Source</td><td>31075</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31077'>PV String 22 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv22_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring22/sigen_0_inverter_1_pv22_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv22_current/state</td></tr>
<tr><td>Source</td><td>31077</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31079'>PV String 23 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv23_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring23/sigen_0_inverter_1_pv23_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv23_current/state</td></tr>
<tr><td>Source</td><td>31079</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31081'>PV String 24 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv24_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring24/sigen_0_inverter_1_pv24_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv24_current/state</td></tr>
<tr><td>Source</td><td>31081</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31083'>PV String 25 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv25_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring25/sigen_0_inverter_1_pv25_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv25_current/state</td></tr>
<tr><td>Source</td><td>31083</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31085'>PV String 26 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv26_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring26/sigen_0_inverter_1_pv26_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv26_current/state</td></tr>
<tr><td>Source</td><td>31085</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31087'>PV String 27 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv27_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring27/sigen_0_inverter_1_pv27_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv27_current/state</td></tr>
<tr><td>Source</td><td>31087</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31089'>PV String 28 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv28_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring28/sigen_0_inverter_1_pv28_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv28_current/state</td></tr>
<tr><td>Source</td><td>31089</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31091'>PV String 29 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv29_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring29/sigen_0_inverter_1_pv29_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv29_current/state</td></tr>
<tr><td>Source</td><td>31091</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31093'>PV String 30 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv30_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring30/sigen_0_inverter_1_pv30_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv30_current/state</td></tr>
<tr><td>Source</td><td>31093</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31095'>PV String 31 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv31_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring31/sigen_0_inverter_1_pv31_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv31_current/state</td></tr>
<tr><td>Source</td><td>31095</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31097'>PV String 32 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv32_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring32/sigen_0_inverter_1_pv32_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv32_current/state</td></tr>
<tr><td>Source</td><td>31097</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31099'>PV String 33 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv33_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring33/sigen_0_inverter_1_pv33_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv33_current/state</td></tr>
<tr><td>Source</td><td>31099</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31101'>PV String 34 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv34_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring34/sigen_0_inverter_1_pv34_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv34_current/state</td></tr>
<tr><td>Source</td><td>31101</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31103'>PV String 35 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv35_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring35/sigen_0_inverter_1_pv35_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv35_current/state</td></tr>
<tr><td>Source</td><td>31103</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31105'>PV String 36 Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVCurrentSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv36_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring36/sigen_0_inverter_1_pv36_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv36_current/state</td></tr>
<tr><td>Source</td><td>31105</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv1_daily_energy'>PV String 1 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv1_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv2_daily_energy'>PV String 2 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv2_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv3_daily_energy'>PV String 3 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv3_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv4_daily_energy'>PV String 4 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv4_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv5_daily_energy'>PV String 5 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv5_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv6_daily_energy'>PV String 6 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv6_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv7_daily_energy'>PV String 7 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv7_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv8_daily_energy'>PV String 8 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv8_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv9_daily_energy'>PV String 9 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv9_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv10_daily_energy'>PV String 10 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv10_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv11_daily_energy'>PV String 11 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv11_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv12_daily_energy'>PV String 12 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv12_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv13_daily_energy'>PV String 13 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv13_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv14_daily_energy'>PV String 14 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv14_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv15_daily_energy'>PV String 15 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv15_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv16_daily_energy'>PV String 16 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv16_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv17_daily_energy'>PV String 17 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv17_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring17/sigen_0_inverter_1_pv17_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv17_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv18_daily_energy'>PV String 18 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv18_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring18/sigen_0_inverter_1_pv18_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv18_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv19_daily_energy'>PV String 19 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv19_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring19/sigen_0_inverter_1_pv19_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv19_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv20_daily_energy'>PV String 20 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv20_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring20/sigen_0_inverter_1_pv20_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv20_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv21_daily_energy'>PV String 21 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv21_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring21/sigen_0_inverter_1_pv21_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv21_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv22_daily_energy'>PV String 22 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv22_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring22/sigen_0_inverter_1_pv22_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv22_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv23_daily_energy'>PV String 23 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv23_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring23/sigen_0_inverter_1_pv23_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv23_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv24_daily_energy'>PV String 24 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv24_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring24/sigen_0_inverter_1_pv24_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv24_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv25_daily_energy'>PV String 25 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv25_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring25/sigen_0_inverter_1_pv25_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv25_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv26_daily_energy'>PV String 26 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv26_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring26/sigen_0_inverter_1_pv26_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv26_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv27_daily_energy'>PV String 27 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv27_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring27/sigen_0_inverter_1_pv27_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv27_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv28_daily_energy'>PV String 28 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv28_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring28/sigen_0_inverter_1_pv28_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv28_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv29_daily_energy'>PV String 29 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv29_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring29/sigen_0_inverter_1_pv29_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv29_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv30_daily_energy'>PV String 30 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv30_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring30/sigen_0_inverter_1_pv30_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv30_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv31_daily_energy'>PV String 31 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv31_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring31/sigen_0_inverter_1_pv31_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv31_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv32_daily_energy'>PV String 32 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv32_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring32/sigen_0_inverter_1_pv32_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv32_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv33_daily_energy'>PV String 33 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv33_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring33/sigen_0_inverter_1_pv33_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv33_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv34_daily_energy'>PV String 34 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv34_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring34/sigen_0_inverter_1_pv34_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv34_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv35_daily_energy'>PV String 35 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv35_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring35/sigen_0_inverter_1_pv35_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv35_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv36_daily_energy'>PV String 36 Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringDailyEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv36_daily_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring36/sigen_0_inverter_1_pv36_daily_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv36_daily_energy/state</td></tr>
<tr><td>Source</td><td>PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv1_lifetime_energy'>PV String 1 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv1_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv2_lifetime_energy'>PV String 2 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv2_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv3_lifetime_energy'>PV String 3 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv3_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv4_lifetime_energy'>PV String 4 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv4_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv5_lifetime_energy'>PV String 5 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv5_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv6_lifetime_energy'>PV String 6 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv6_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv7_lifetime_energy'>PV String 7 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv7_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv8_lifetime_energy'>PV String 8 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv8_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv9_lifetime_energy'>PV String 9 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv9_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv10_lifetime_energy'>PV String 10 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv10_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv11_lifetime_energy'>PV String 11 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv11_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv12_lifetime_energy'>PV String 12 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv12_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv13_lifetime_energy'>PV String 13 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv13_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv14_lifetime_energy'>PV String 14 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv14_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv15_lifetime_energy'>PV String 15 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv15_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv16_lifetime_energy'>PV String 16 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv16_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv17_lifetime_energy'>PV String 17 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv17_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring17/sigen_0_inverter_1_pv17_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv17_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv18_lifetime_energy'>PV String 18 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv18_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring18/sigen_0_inverter_1_pv18_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv18_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv19_lifetime_energy'>PV String 19 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv19_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring19/sigen_0_inverter_1_pv19_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv19_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv20_lifetime_energy'>PV String 20 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv20_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring20/sigen_0_inverter_1_pv20_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv20_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv21_lifetime_energy'>PV String 21 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv21_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring21/sigen_0_inverter_1_pv21_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv21_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv22_lifetime_energy'>PV String 22 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv22_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring22/sigen_0_inverter_1_pv22_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv22_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv23_lifetime_energy'>PV String 23 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv23_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring23/sigen_0_inverter_1_pv23_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv23_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv24_lifetime_energy'>PV String 24 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv24_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring24/sigen_0_inverter_1_pv24_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv24_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv25_lifetime_energy'>PV String 25 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv25_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring25/sigen_0_inverter_1_pv25_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv25_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv26_lifetime_energy'>PV String 26 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv26_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring26/sigen_0_inverter_1_pv26_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv26_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv27_lifetime_energy'>PV String 27 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv27_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring27/sigen_0_inverter_1_pv27_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv27_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv28_lifetime_energy'>PV String 28 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv28_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring28/sigen_0_inverter_1_pv28_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv28_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv29_lifetime_energy'>PV String 29 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv29_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring29/sigen_0_inverter_1_pv29_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv29_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv30_lifetime_energy'>PV String 30 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv30_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring30/sigen_0_inverter_1_pv30_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv30_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv31_lifetime_energy'>PV String 31 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv31_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring31/sigen_0_inverter_1_pv31_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv31_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv32_lifetime_energy'>PV String 32 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv32_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring32/sigen_0_inverter_1_pv32_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv32_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv33_lifetime_energy'>PV String 33 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv33_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring33/sigen_0_inverter_1_pv33_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv33_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv34_lifetime_energy'>PV String 34 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv34_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring34/sigen_0_inverter_1_pv34_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv34_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv35_lifetime_energy'>PV String 35 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv35_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring35/sigen_0_inverter_1_pv35_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv35_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv36_lifetime_energy'>PV String 36 Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringLifetimeEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv36_lifetime_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring36/sigen_0_inverter_1_pv36_lifetime_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv36_lifetime_energy/state</td></tr>
<tr><td>Source</td><td>Riemann &sum; of PVStringPower</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv1_power'>PV String 1 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv1_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv2_power'>PV String 2 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv2_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv3_power'>PV String 3 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv3_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv4_power'>PV String 4 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv4_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv5_power'>PV String 5 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv5_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv6_power'>PV String 6 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv6_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv7_power'>PV String 7 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv7_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv8_power'>PV String 8 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv8_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv9_power'>PV String 9 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv9_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv10_power'>PV String 10 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv10_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv11_power'>PV String 11 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv11_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv12_power'>PV String 12 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv12_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv13_power'>PV String 13 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv13_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv14_power'>PV String 14 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv14_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv15_power'>PV String 15 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv15_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv16_power'>PV String 16 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv16_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv17_power'>PV String 17 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv17_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring17/sigen_0_inverter_1_pv17_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv17_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv18_power'>PV String 18 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv18_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring18/sigen_0_inverter_1_pv18_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv18_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv19_power'>PV String 19 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv19_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring19/sigen_0_inverter_1_pv19_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv19_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv20_power'>PV String 20 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv20_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring20/sigen_0_inverter_1_pv20_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv20_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv21_power'>PV String 21 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv21_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring21/sigen_0_inverter_1_pv21_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv21_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv22_power'>PV String 22 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv22_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring22/sigen_0_inverter_1_pv22_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv22_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv23_power'>PV String 23 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv23_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring23/sigen_0_inverter_1_pv23_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv23_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv24_power'>PV String 24 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv24_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring24/sigen_0_inverter_1_pv24_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv24_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv25_power'>PV String 25 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv25_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring25/sigen_0_inverter_1_pv25_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv25_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv26_power'>PV String 26 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv26_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring26/sigen_0_inverter_1_pv26_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv26_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv27_power'>PV String 27 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv27_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring27/sigen_0_inverter_1_pv27_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv27_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv28_power'>PV String 28 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv28_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring28/sigen_0_inverter_1_pv28_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv28_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv29_power'>PV String 29 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv29_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring29/sigen_0_inverter_1_pv29_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv29_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv30_power'>PV String 30 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv30_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring30/sigen_0_inverter_1_pv30_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv30_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv31_power'>PV String 31 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv31_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring31/sigen_0_inverter_1_pv31_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv31_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv32_power'>PV String 32 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv32_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring32/sigen_0_inverter_1_pv32_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv32_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv33_power'>PV String 33 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv33_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring33/sigen_0_inverter_1_pv33_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv33_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv34_power'>PV String 34 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv34_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring34/sigen_0_inverter_1_pv34_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv34_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv35_power'>PV String 35 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv35_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring35/sigen_0_inverter_1_pv35_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv35_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_inverter_1_pv36_power'>PV String 36 Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVStringPower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv36_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring36/sigen_0_inverter_1_pv36_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv36_power/state</td></tr>
<tr><td>Source</td><td>PVVoltageSensor &times; PVCurrentSensor</td></tr>
<tr><td>Applicable To</td><td></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_31027'>PV String 1 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv1_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring1/sigen_0_inverter_1_pv1_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv1_voltage/state</td></tr>
<tr><td>Source</td><td>31027</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31029'>PV String 2 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv2_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring2/sigen_0_inverter_1_pv2_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv2_voltage/state</td></tr>
<tr><td>Source</td><td>31029</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31031'>PV String 3 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv3_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring3/sigen_0_inverter_1_pv3_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv3_voltage/state</td></tr>
<tr><td>Source</td><td>31031</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31033'>PV String 4 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv4_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring4/sigen_0_inverter_1_pv4_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv4_voltage/state</td></tr>
<tr><td>Source</td><td>31033</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31042'>PV String 5 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv5_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring5/sigen_0_inverter_1_pv5_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv5_voltage/state</td></tr>
<tr><td>Source</td><td>31042</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31044'>PV String 6 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv6_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring6/sigen_0_inverter_1_pv6_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv6_voltage/state</td></tr>
<tr><td>Source</td><td>31044</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31046'>PV String 7 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv7_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring7/sigen_0_inverter_1_pv7_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv7_voltage/state</td></tr>
<tr><td>Source</td><td>31046</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31048'>PV String 8 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv8_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring8/sigen_0_inverter_1_pv8_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv8_voltage/state</td></tr>
<tr><td>Source</td><td>31048</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31050'>PV String 9 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv9_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring9/sigen_0_inverter_1_pv9_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv9_voltage/state</td></tr>
<tr><td>Source</td><td>31050</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31052'>PV String 10 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv10_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring10/sigen_0_inverter_1_pv10_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv10_voltage/state</td></tr>
<tr><td>Source</td><td>31052</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31054'>PV String 11 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv11_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring11/sigen_0_inverter_1_pv11_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv11_voltage/state</td></tr>
<tr><td>Source</td><td>31054</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31056'>PV String 12 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv12_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring12/sigen_0_inverter_1_pv12_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv12_voltage/state</td></tr>
<tr><td>Source</td><td>31056</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31058'>PV String 13 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv13_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring13/sigen_0_inverter_1_pv13_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv13_voltage/state</td></tr>
<tr><td>Source</td><td>31058</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31060'>PV String 14 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv14_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring14/sigen_0_inverter_1_pv14_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv14_voltage/state</td></tr>
<tr><td>Source</td><td>31060</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31062'>PV String 15 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv15_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring15/sigen_0_inverter_1_pv15_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv15_voltage/state</td></tr>
<tr><td>Source</td><td>31062</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31064'>PV String 16 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv16_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring16/sigen_0_inverter_1_pv16_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv16_voltage/state</td></tr>
<tr><td>Source</td><td>31064</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31066'>PV String 17 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv17_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring17/sigen_0_inverter_1_pv17_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv17_voltage/state</td></tr>
<tr><td>Source</td><td>31066</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31068'>PV String 18 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv18_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring18/sigen_0_inverter_1_pv18_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv18_voltage/state</td></tr>
<tr><td>Source</td><td>31068</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31070'>PV String 19 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv19_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring19/sigen_0_inverter_1_pv19_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv19_voltage/state</td></tr>
<tr><td>Source</td><td>31070</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31072'>PV String 20 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv20_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring20/sigen_0_inverter_1_pv20_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv20_voltage/state</td></tr>
<tr><td>Source</td><td>31072</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31074'>PV String 21 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv21_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring21/sigen_0_inverter_1_pv21_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv21_voltage/state</td></tr>
<tr><td>Source</td><td>31074</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31076'>PV String 22 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv22_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring22/sigen_0_inverter_1_pv22_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv22_voltage/state</td></tr>
<tr><td>Source</td><td>31076</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31078'>PV String 23 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv23_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring23/sigen_0_inverter_1_pv23_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv23_voltage/state</td></tr>
<tr><td>Source</td><td>31078</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31080'>PV String 24 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv24_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring24/sigen_0_inverter_1_pv24_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv24_voltage/state</td></tr>
<tr><td>Source</td><td>31080</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31082'>PV String 25 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv25_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring25/sigen_0_inverter_1_pv25_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv25_voltage/state</td></tr>
<tr><td>Source</td><td>31082</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31084'>PV String 26 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv26_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring26/sigen_0_inverter_1_pv26_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv26_voltage/state</td></tr>
<tr><td>Source</td><td>31084</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31086'>PV String 27 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv27_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring27/sigen_0_inverter_1_pv27_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv27_voltage/state</td></tr>
<tr><td>Source</td><td>31086</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31088'>PV String 28 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv28_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring28/sigen_0_inverter_1_pv28_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv28_voltage/state</td></tr>
<tr><td>Source</td><td>31088</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31090'>PV String 29 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv29_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring29/sigen_0_inverter_1_pv29_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv29_voltage/state</td></tr>
<tr><td>Source</td><td>31090</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31092'>PV String 30 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv30_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring30/sigen_0_inverter_1_pv30_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv30_voltage/state</td></tr>
<tr><td>Source</td><td>31092</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31094'>PV String 31 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv31_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring31/sigen_0_inverter_1_pv31_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv31_voltage/state</td></tr>
<tr><td>Source</td><td>31094</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31096'>PV String 32 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv32_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring32/sigen_0_inverter_1_pv32_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv32_voltage/state</td></tr>
<tr><td>Source</td><td>31096</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31098'>PV String 33 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv33_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring33/sigen_0_inverter_1_pv33_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv33_voltage/state</td></tr>
<tr><td>Source</td><td>31098</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31100'>PV String 34 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv34_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring34/sigen_0_inverter_1_pv34_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv34_voltage/state</td></tr>
<tr><td>Source</td><td>31100</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31102'>PV String 35 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv35_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring35/sigen_0_inverter_1_pv35_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv35_voltage/state</td></tr>
<tr><td>Source</td><td>31102</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>
<h5><a id='sigen_0_001_31104'>PV String 36 Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>PVVoltageSensor</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_pv36_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_pvstring36/sigen_0_inverter_1_pv36_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_pv36_voltage/state</td></tr>
<tr><td>Source</td><td>31104</td></tr>
<tr><td>Applicable To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -32767 and 32767</td></tr>
</table>

### AC Charger
<h5><a id='sigen_0_ac_charger_2_alarm'>Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerAlarms</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_alarm</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_alarm/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_alarm/state</td></tr>
<tr><td>Source</td><td>Modbus Registers 32012, 32013, and 32014</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_002_32003'>Charging Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerChargingPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_charging_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_charging_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_charging_power/state</td></tr>
<tr><td>Source</td><td>32003</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_002_32010'>Input Breaker</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerInputBreaker</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_input_breaker</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_input_breaker/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_input_breaker/state</td></tr>
<tr><td>Source</td><td>32010</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_002_42001'>Output Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerOutputCurrent</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_output_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/number/sigen_0_002_accharger/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/state</td></tr>
<tr><td>Source</td><td>42001</td></tr>
<tr><td>Comment</td><td>Range: [6, smaller of 'AC-Charger Rated Current' and 'AC-Charger Input Breaker Rated Current']</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>No sanity checking applied</td></tr>
</table>
<h5><a id='sigen_0_002_32007'>Rated Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerRatedCurrent</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_current/state</td></tr>
<tr><td>Source</td><td>32007</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_002_32005'>Rated Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerRatedPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_power/state</td></tr>
<tr><td>Source</td><td>32005</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_002_32009'>Rated Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerRatedVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_rated_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_rated_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_rated_voltage/state</td></tr>
<tr><td>Source</td><td>32009</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_002_32000'>Running State</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerRunningState</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_running_state</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_running_state/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_running_state/state</td></tr>
<tr><td>Source</td><td>32000</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>Initialising</li><li value='1'>EV not connected</li><li value='2'>Charger and EV not ready</li><li value='3'>Charger ready; EV not ready</li><li value='4'>Charger not ready; EV ready</li><li value='5'>Charging</li><li value='6'>Fault</li><li value='7'>Error</li></ol></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_002_32001'>Total Energy Consumed</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>ACChargerTotalEnergyConsumed</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_ac_charger_2_total_energy_consumed</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_002_accharger/sigen_0_ac_charger_2_total_energy_consumed/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_total_energy_consumed/state</td></tr>
<tr><td>Source</td><td>32001</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>

### DC Charger
<h5><a id='sigen_0_001_30609'>Alarms</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>InverterAlarm5</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_alarm_5</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_inverter_1_alarm_5/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_alarm_5/state</td></tr>
<tr><td>Source</td><td>30609</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31505'>Current Charging Capacity</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DCChargerCurrentChargingCapacity</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>100</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_dc_charger_1_current_charging_capacity</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_dc_charger_1_current_charging_capacity/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_current_charging_capacity/state</td></tr>
<tr><td>Source</td><td>31505</td></tr>
<tr><td>Comment</td><td>Single time</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_31507'>Current Charging Duration</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DCChargerCurrentChargingDuration</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>600s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>s</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_dc_charger_1_current_charging_duration</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_dc_charger_1_current_charging_duration/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_current_charging_duration/state</td></tr>
<tr><td>Source</td><td>31507</td></tr>
<tr><td>Comment</td><td>Single time</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_001_31502'>Output Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DCChargerOutputPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kW</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_dc_charger_1_output_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_dc_charger_1_output_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_output_power/state</td></tr>
<tr><td>Source</td><td>31502</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -500000.0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_001_31513'>Running State</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DCChargerRunningState</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_dc_charger_1_running_state</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_dc_charger_1_running_state/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_running_state/state</td></tr>
<tr><td>Source</td><td>31513</td></tr>
<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'><li value='0'>Idle</li><li value='1'>Occupied (Charging Gun plugged in but not detected)</li><li value='2'>Preparing (Establishing communication)</li><li value='3'>Charging</li><li value='4'>Fault</li><li value='5'>Scheduled</li></ol></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31500'>Vehicle Battery Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DCChargerVehicleBatteryVoltage</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_inverter_1_vehicle_battery_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_inverter_1_vehicle_battery_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_vehicle_battery_voltage/state</td></tr>
<tr><td>Source</td><td>31500</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31501'>Vehicle Charging Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DCChargerVehicleChargingCurrent</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>10s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_dc_charger_1_vehicle_charging_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_dc_charger_1_vehicle_charging_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_vehicle_charging_current/state</td></tr>
<tr><td>Source</td><td>31501</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_001_31504'>Vehicle SoC</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>DCChargerVehicleSoC</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>60s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>%</td></tr>
<tr><td>Gain</td><td>10</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_dc_charger_1_vehicle_soc</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_001_dccharger/sigen_0_dc_charger_1_vehicle_soc/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1_vehicle_soc/state</td></tr>
<tr><td>Source</td><td>31504</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>

#### Smart-Port (Enphase Envoy only)
<h5><a id='sigen_0_enphase_123456789012_current'>Current</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphaseCurrent</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>A</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_current</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_current/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_current/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between -2147483647 and 2147483647</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_daily_pv_energy'>Daily Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphaseDailyPVEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_daily_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_daily_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_daily_pv_energy/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_frequency'>Frequency</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphaseFrequency</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>Hz</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_frequency</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_frequency/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_frequency/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_lifetime_pv_energy'>Lifetime Production</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphaseLifetimePVEnergy</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kWh</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_lifetime_pv_energy</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_lifetime_pv_energy/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_lifetime_pv_energy/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The raw value is sanity checked to be between 0 and 500000.0</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_active_power'>PV Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphasePVPower</td></tr>
<tr><td>Scan&nbsp;Interval</td><td>5s</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>W</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_active_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_active_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_active_power/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.4</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be a maximum of 500000.0</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_power_factor'>Power Factor</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphasePowerFactor</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_power_factor</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_power_factor/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_power_factor/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_reactive_power'>Reactive Power</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphaseReactivePower</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>kvar</td></tr>
<tr><td>Gain</td><td>1000</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_reactive_power</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_reactive_power/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_reactive_power/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 4294967295</td></tr>
</table>
<h5><a id='sigen_0_enphase_123456789012_voltage'>Voltage</a></h5>
<table>
<tr><td>Sensor&nbsp;Class</td><td>EnphaseVoltage</td></tr>
<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>V</td></tr>
<tr><td>Gain</td><td>1</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.sigen_0_enphase_123456789012_voltage</td></tr>
<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>homeassistant/sensor/sigen_0_enphase_envoy_123456789012/sigen_0_enphase_123456789012_voltage/state</td></tr>
<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_enphase_123456789012_voltage/state</td></tr>
<tr><td>Source</td><td>Enphase Envoy API when EnphasePVPower derived</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>N/A</td></tr>
<tr><td>Sanity&nbsp;Check</td><td>The delta of the raw value compared to the previous value is sanity checked to be between 0 and 65535</td></tr>
</table>

### Metrics

Metrics are _only_ published to the sigenergy2mqtt/metrics topics, even when Home Assistant discovery is enabled. The scan interval cannot be altered.
| Metric | Interval | Unit | State Topic|
|--------|---------:|------|------------|
| <a id='sigen_modbus_locks'>Modbus Active Locks</a> | 1 |  | sigenergy2mqtt/metrics/modbus_locks |
| <a id='sigen_modbus_cache_hit_percentage'>Modbus Cache Hits</a> | 1 | % | sigenergy2mqtt/metrics/modbus_cache_hit_percentage |
| <a id='sigen_modbus_read_errors'>Modbus Read Errors</a> | 1 |  | sigenergy2mqtt/metrics/modbus_read_errors |
| <a id='sigen_modbus_read_max'>Modbus Read Max</a> | 1 | ms | sigenergy2mqtt/metrics/modbus_read_max |
| <a id='sigen_modbus_read_mean'>Modbus Read Mean</a> | 1 | ms | sigenergy2mqtt/metrics/modbus_read_mean |
| <a id='sigen_modbus_read_min'>Modbus Read Min</a> | 1 | ms | sigenergy2mqtt/metrics/modbus_read_min |
| <a id='sigen_modbus_reads_sec'>Modbus Reads/second</a> | 1 |  | sigenergy2mqtt/metrics/modbus_reads_sec |
| <a id='sigen_modbus_write_errors'>Modbus Write Errors</a> | 1 |  | sigenergy2mqtt/metrics/modbus_write_errors |
| <a id='sigen_modbus_write_max'>Modbus Write Max</a> | 1 | ms | sigenergy2mqtt/metrics/modbus_write_max |
| <a id='sigen_modbus_write_mean'>Modbus Write Mean</a> | 1 | ms | sigenergy2mqtt/metrics/modbus_write_mean |
| <a id='sigen_modbus_write_min'>Modbus Write Min</a> | 1 | ms | sigenergy2mqtt/metrics/modbus_write_min |
| <a id='sigen_modbus_protocol_published'>Protocol Published</a> | 1 |  | sigenergy2mqtt/metrics/modbus_protocol_published |
| <a id='sigen_modbus_protocol'>Protocol Version</a> | 1 |  | sigenergy2mqtt/metrics/modbus_protocol |
| <a id='sigen_started'>Started</a> | 1 |  | sigenergy2mqtt/metrics/started |

## Subscribed Topics

### Plant
<h5><a id='sigen_0_247_40001_set'>Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40005_set'>Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Range: [-100.00,100.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-100</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40049_set'>Active Power Regulation Gradient
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_active_power_regulation_gradient/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_active_power_regulation_gradient/set</td></tr>
<tr><td>Comment</td><td>Range:[0,5000]。Percentage of rated power adjusted per second</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>5000.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.8</td></tr>
</table>
<h5><a id='sigen_0_247_40046_set'>Backup SoC
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_backup_soc/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_backup_soc/set</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
</table>
<h5><a id='sigen_0_247_40047_set'>Charge Cut-Off SoC
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_charge_cut_off_soc/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_charge_cut_off_soc/set</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
</table>
<h5><a id='sigen_0_247_40048_set'>Discharge Cut-Off SoC
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_ess_discharge_cut_off_soc/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_ess_discharge_cut_off_soc/set</td></tr>
<tr><td>Comment</td><td>Range: [0.00,100.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.6</td></tr>
</table>
<h5><a id='sigen_0_247_40038_set'>Grid Max Export Limit
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_export_limit/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_export_limit/set</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>4294967.295</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_247_40040_set'>Grid Max Import Limit
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_grid_max_import_limit/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_grid_max_import_limit/set</td></tr>
<tr><td>Comment</td><td>Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>4294967.295</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_247_40030_set'>Independent Phase Power Control
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_independent_phase_power_control/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_independent_phase_power_control/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40032_set'>Max Charging Limit
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_charging_limit/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_charging_limit/set</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Charging</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>Rated ESS charging power</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40034_set'>Max Discharging Limit
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_max_discharging_limit/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_max_discharging_limit/set</td></tr>
<tr><td>Comment</td><td>Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Discharging</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>Rated ESS charging power</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40042_set'>PCS Max Export Limit
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_export_limit/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_export_limit/set</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>4294967.295</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_247_40044_set'>PCS Max Import Limit
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pcs_max_import_limit/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_pcs_max_import_limit/set</td></tr>
<tr><td>Comment</td><td>Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally.</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>4294967.295</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_247_40036_set'>PV Max Power Limit
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_pv_max_power_limit/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_pv_max_power_limit/set</td></tr>
<tr><td>Comment</td><td>Takes effect when Remote EMS control mode (40031) is set to Command Charging/Discharging</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>4294967.295</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40008_set'>Phase A Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40020_set'>Phase A Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-100</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40023_set'>Phase A Q/S Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_q_s_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-60</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>60</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40014_set'>Phase A Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_a_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40010_set'>Phase B Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40021_set'>Phase B Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-100</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40024_set'>Phase B Q/S Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_q_s_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-60</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>60</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40016_set'>Phase B Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_b_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40012_set'>Phase C Active Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40022_set'>Phase C Active Power Percentage Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_active_power_percentage_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-100</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40025_set'>Phase C Q/S Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_q_s_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-60</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>60</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40018_set'>Phase C Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_phase_c_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Valid only when Output Type is L1/L2/L3/N</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40000_set'>Plant Power On/Off
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/button/sigen_0_247_powerplant/sigen_0_plant_status/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_status/set</td></tr>
<tr><td>Valid&nbsp;Values</td><td>0:Stop 1:Start</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40007_set'>Power Factor Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_power_factor_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_power_factor_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Range: [(-1.0, -0.8) U (0.8, 1.0)]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>(-1.0, -0.8)</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>(0.8, 1.0)</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40006_set'>Q/S Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_q_s_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_q_s_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Range: [-60.0,60.00]. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-60</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>60</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40003_set'>Reactive Power Fixed Adjustment Target Value
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_247_powerplant/sigen_0_plant_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_reactive_power_fixed_adjustment_target_value/set</td></tr>
<tr><td>Comment</td><td>Range: [-60.00 * base value ,60.00 * base value]. Takes effect globally regardless of the EMS operating mode</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-60.00 * base value</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>60.00 * base value</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40029_set'>Remote EMS
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/switch/sigen_0_247_powerplant/sigen_0_plant_remote_ems/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems/set</td></tr>
<tr><td>Comment</td><td>When needed to control EMS remotely, this register needs to be enabled. When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_247_40031_set'>Remote EMS Control Mode
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/select/sigen_0_247_powerplant/sigen_0_plant_remote_ems_control_mode/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/set</td></tr>
<tr><td>Valid&nbsp;Values</td><td><ul><li value='0'>"PCS remote control"</li><li value='1'>"Standby"</li><li value='2'>"Maximum Self-consumption (Default)"</li><li value='3'>"Command Charging (Consume power from the grid first)"</li><li value='4'>"Command Charging (Consume power from the PV first)"</li><li value='5'>"Command Discharging (Output power from PV first)"</li><li value='6'>"Command Discharging (Output power from the battery first)"</li></ol></td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>

### Inverter
<h5><a id='sigen_0_001_41501_set'>Active Power Fixed Value Adjustment
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_fixed_value_adjustment/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_fixed_value_adjustment/set</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Applicable&nbsp;To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_001_41505_set'>Active Power Percentage Adjustment
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_active_power_percentage_adjustment/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_active_power_percentage_adjustment/set</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-100.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Applicable&nbsp;To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_001_40500_set'>Inverter Power On/Off
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/button/sigen_0_001_inverter/sigen_0_inverter_1_status/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_status/set</td></tr>
<tr><td>Valid&nbsp;Values</td><td>0:Stop 1:Start</td></tr>
<tr><td>Applicable&nbsp;To</td><td> Hybrid Inverter and PV Inverter </td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
<h5><a id='sigen_0_001_41507_set'>Power Factor Adjustment
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_power_factor_adjustment/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_power_factor_adjustment/set</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-1.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>1.0</td></tr>
<tr><td>Applicable&nbsp;To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_001_41503_set'>Reactive Power Fixed Value Adjustment
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_fixed_value_adjustment/set</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>0.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>100.0</td></tr>
<tr><td>Applicable&nbsp;To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>
<h5><a id='sigen_0_001_41506_set'>Reactive Power Q/S Adjustment
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_001_inverter/sigen_0_inverter_1_reactive_power_q_s_adjustment/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_inverter_1_reactive_power_q_s_adjustment/set</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>-60.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>60.0</td></tr>
<tr><td>Applicable&nbsp;To</td><td> PV Inverter only</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.5</td></tr>
</table>

### AC Charger
<h5><a id='sigen_0_002_42000_set'>AC Charger Stop/Start
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/button/sigen_0_002_accharger/sigen_0_ac_charger_2/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2/set</td></tr>
<tr><td>Valid&nbsp;Values</td><td>0:Start 1:Stop</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
</table>
<h5><a id='sigen_0_002_42001_set'>Output Current
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/number/sigen_0_002_accharger/sigen_0_ac_charger_2_output_current/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_ac_charger_2_output_current/set</td></tr>
<tr><td>Comment</td><td>Range: [6, smaller of 'AC-Charger Rated Current' and 'AC-Charger Input Breaker Rated Current']</td></tr>
<tr><td>Minimum&nbsp;Value</td><td>6.0</td></tr>
<tr><td>Maximum&nbsp;Value</td><td>smaller of 'AC-Charger Rated Current' and 'AC-Charger Input Breaker Rated Current'</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>2.0</td></tr>
</table>

### DC Charger
<h5><a id='sigen_0_001_41000_set'>DC Charger Stop/Start
</a></h5>
<table>
<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>homeassistant/button/sigen_0_001_dccharger/sigen_0_dc_charger_1/set</td></tr>
<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>sigenergy2mqtt/sigen_0_dc_charger_1/set</td></tr>
<tr><td>Valid&nbsp;Values</td><td>0:Start 1:Stop</td></tr>
<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>1.8</td></tr>
</table>
