# Environment Variables

Environment variables override the configuration file, but *not* command line options.


## General Configuration Variables

| Name | Description | Since |
|------|-------------|-------|
| `SIGENERGY2MQTT_CONFIG` | The path to the YAML configuration file (defaults: `/etc/sigenergy2mqtt.yaml` for Linux, `/data/sigenergy2mqtt.yaml` for Docker and `/config/sigenergy2mqtt.yaml` for Home Assistant) [<sup>(More…)</sup>](README.md#opt_config_path) | 2025.5.12 |
| `SIGENERGY2MQTT_STATE_DIR` | The directory in which to store persistent state files (defaults: `/var/lib/` for Linux, `/data/` for Docker and `/config/` for Home Assistant). A sub-directory will be created in the specified directory called `sigenergy2mqtt` to store the files. [<sup>(More…)</sup>](README.md#opt_state_dir) | 2026.2.23 |
| `SIGENERGY2MQTT_LANGUAGE` | The language to use for translations. Valid values are determined from the translation files available in the 'translations' directory. The default is determined from system (e.g. LANG environment variable) or English if no translation is found. [<sup>(More…)</sup>](README.md#opt_language) | 2026.1.22 |
| `SIGENERGY2MQTT_LOG_LEVEL` | Set the log level. Valid values are: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `WARNING` (warnings, errors and critical failures) [<sup>(More…)</sup>](README.md#opt_log_level) | 2025.5.12 |
| `SIGENERGY2MQTT_DEBUG_SENSOR` | Specify a sensor to be debugged using either the full entity id, a partial entity id, the full sensor class name, or a partial sensor class name. For example, specifying 'daily' would match all sensors with daily in their entity id. From 2026.1.5, the sensor may also be specified as a regular expression (e.g. ^PowerFactor$ will match *only* the PowerFactor class name, but not InverterPowerFactorAdjustmentFeedback). If specified, `SIGENERGY2MQTT_LOG_LEVEL` is also forced to `DEBUG`. [<sup>(More…)</sup>](README.md#opt_debug_sensor) | 2025.5.12 |
| `SIGENERGY2MQTT_SANITY_CHECK_FAILURES_INCREMENT` | Set to `true` to increment the number of sensor read failures when a sanity check fails. Default is `false`. [<sup>(More…)</sup>](README.md#opt_sanity_check_failures_increment) | 2026.1.21 |
| `SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW` | The default value in kW used for sanity checks to validate the maximum and minimum values for actual value of power sensors and the delta value of energy sensors. The default value is `500` kW per second, and readings outside the range are ignored. [<sup>(More…)</sup>](README.md#opt_sanity_check_default_kw) | 2025.7.9 |
| `SIGENERGY2MQTT_SENSOR_OVERRIDES_JSON` | A JSON string containing sensor overrides. This allows fine-grained control over individual sensor settings (like debug logging) via environment variables. [<sup>(More…)</sup>](README.md#opt_sensor_overrides) | 2026.4.4 |
| `SIGENERGY2MQTT_NO_METRICS` | Set to `true` to prevent sigenergy2mqtt from publishing metrics to MQTT. [<sup>(More…)</sup>](README.md#opt_no_metrics) | 2025.8.2 |
| `SIGENERGY2MQTT_NO_EMS_MODE_CHECK` | Set to `true` to turn off the validation that disables ESS Max Charging/Discharging and PV Max Power limits when Remote EMS Control Mode is not Command Charging/Discharging. This setting is ignored for firmware SPC113 and later, because PV Max Power and ESS Charge/Discharge limits are globally available in those versions. [<sup>(More…)</sup>](README.md#opt_no_ems_mode_check) | 2026.1.13 |
| `SIGENERGY2MQTT_CONSUMPTION` | Set the method of calculating the `Plant Consumed Power` sensor. Valid values are: `calculated`, `total` (use the V2.8 `Total Load Power` register), or `general` (use the V2.8 `General Load Power` register). The default is `total`. This option is _ignored_ on firmware earlier than that supporting Modbus Protocol V2.8. [<sup>(More…)</sup>](README.md#opt_consumption) | 2025.12.23 |
| `SIGENERGY2MQTT_REPEATED_STATE_PUBLISH_INTERVAL` | Set the interval in seconds at which repeated states are published. (Repeated states occur when the state that is acquired is identical to the previous read.) If < 0, repeated states are never published. If 0, repeated states are always published. If > 0, repeated states are published at the specified interval. The default is 0 (always publish) [<sup>(More…)</sup>](README.md#opt_repeated_state_publish_interval) | 2026.2.19 |

## Home Assistant Configuration Variables

| Name | Description | Since |
|------|-------------|-------|
| `SIGENERGY2MQTT_HASS_ENABLED` | Set to `true` to enable auto-discovery in Home Assistant. [<sup>(More…)</sup>](README.md#opt_home_assistant_enabled) | 2025.5.12 |
| `SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX` | The Home Assistant MQTT Discovery topic prefix to use (default: `homeassistant`) [<sup>(More…)</sup>](README.md#opt_home_assistant_discovery_prefix) | 2025.5.12 |
| `SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX` | The prefix to use for Home Assistant entity names. Example: A prefix of `prefix` will prepend 'prefix ' to names (default: '') [<sup>(More…)</sup>](README.md#opt_home_assistant_device_name_prefix) | 2025.5.12 |
| `SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX` | The prefix to use for Home Assistant entity IDs. Example: A prefix of `prefix` will prepend 'prefix_' to entity IDs (default: `sigen`) [<sup>(More…)</sup>](README.md#opt_home_assistant_entity_id_prefix) | 2025.5.12 |
| `SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX` | The prefix to use for Home Assistant unique IDs. Example: A prefix of `prefix` will prepend 'prefix_' to unique IDs (default: `sigen`). Once you have set this, you should **NEVER** change it, as it will break existing entities in Home Assistant. [<sup>(More…)</sup>](README.md#opt_home_assistant_unique_id_prefix) | 2025.5.12 |
| `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` | Set to `true` to enable the simplified topic structure (sigenergy2mqtt/object_id/state) instead of the full Home Assistant topic structure (homeassistant/platform/device_id/object_id/state). This is forced to `false` when `SIGENERGY2MQTT_HASS_SIGENERGY_LOCAL_MODBUS_NAMING` is `true`. [<sup>(More…)</sup>](README.md#opt_home_assistant_use_simplified_topics) | 2025.7.26 |
| `SIGENERGY2MQTT_HASS_SIGENERGY_LOCAL_MODBUS_NAMING` | Set to `true` to apply Sigenergy-Local-Modbus entity_id, gain and unit mappings (where available) to ease migration. If enabled, `SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX` must be 'sigen' (default) and `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` is forced to `false`. [<sup>(More…)</sup>](README.md#opt_home_assistant_use_sigenergy_local_modbus_naming) | 2026.3.13 |
| `SIGENERGY2MQTT_HASS_SENSORS_ENABLED_BY_DEFAULT` | Set to `true` to enable all sensors by default when they are first discovered by Home Assistant. [<sup>(More…)</sup>](README.md#opt_home_assistant_sensors_enabled_by_default) | 2026.4.4 |
| `SIGENERGY2MQTT_HASS_EDIT_PCT_BOX` | Set to `true` to use a numeric entry box to change the value of percentage sensors or `false` to use a slider to change the value (default: `false`) [<sup>(More…)</sup>](README.md#opt_home_assistant_edit_pct_box) | 2025.5.12 |

## Modbus Configuration Variables

| Name | Description | Since |
|------|-------------|-------|
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY` | Controls auto-discovery of Sigenergy Modbus hosts and device IDs. If `once` is specified, auto-discovery will only occur if no existing auto-discovery results are found. If `force`, auto-discovery will overwrite any previously discovered Modbus hosts and device IDs. If not specified, auto-discovery is disabled. [<sup>(More…)</sup>](README.md#opt_modbus_auto_discovery) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT` | The ping timeout, in seconds, to use when performing auto-discovery of Sigenergy devices on the network. The default is `0.5` seconds. [<sup>(More…)</sup>](README.md#opt_modbus_auto_discovery_ping_timeout) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT` | The Modbus timeout, in seconds, to use when performing auto-discovery of Sigenergy devices on the network. The default is `0.25` seconds. [<sup>(More…)</sup>](README.md#opt_modbus_auto_discovery_timeout) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES` | The Modbus maximum retry count to use when performing auto-discovery of Sigenergy devices on the network. The default is `0`. [<sup>(More…)</sup>](README.md#opt_modbus_auto_discovery_retries) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_HOST` | The hostname or IP address of the Sigenergy device. Required unless auto-discovery is enabled. [<sup>(More…)</sup>](README.md#opt_modbus_host) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_PORT` | The Sigenergy device Modbus port number (default: `502`) [<sup>(More…)</sup>](README.md#opt_modbus_port) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID` | The Sigenergy device Modbus Device ID. May be specified as a comma-separated list (e.g. `1,2`). (default: `1`) [<sup>(More…)</sup>](README.md#opt_modbus_inverter_device_id) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID` | The Sigenergy AC Charger Modbus Device ID. May be specified as a comma-separated list. [<sup>(More…)</sup>](README.md#opt_modbus_accharger_device_id) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID` | The Sigenergy DC Charger Modbus Device ID. May be specified as a comma-separated list. [<sup>(More…)</sup>](README.md#opt_modbus_dccharger_device_id) | 2025.5.12 |
| `SIGENERGY2MQTT_MODBUS_READ_ONLY` | If `false`, read-only entities will not be published to MQTT. Default is `true`. [<sup>(More…)</sup>](README.md#opt_modbus_read_only) | 2025.5.18 |
| `SIGENERGY2MQTT_MODBUS_READ_WRITE` | If `false`, read-write entities will not be published to MQTT. Default is `true`. [<sup>(More…)</sup>](README.md#opt_modbus_read_write) | 2025.5.18 |
| `SIGENERGY2MQTT_MODBUS_WRITE_ONLY` | If `false`, write-only entities will not be published to MQTT. Default is `true`. [<sup>(More…)</sup>](README.md#opt_modbus_write_only) | 2025.5.18 |
| `SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS`| If `true`, read-write sensors for remote Energy Management System (EMS) integration will NOT be published to MQTT. Default is `false`. Ignored if `SIGENERGY2MQTT_MODBUS_READ_WRITE` is `false`. | 2025.5.31 |
| `SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING` | If `true`, chunking of Modbus reads will be disabled and each register will be read individually. This is NOT recommended for production use. [<sup>(More…)</sup>](README.md#opt_modbus_disable_chunking) | 2025.9.19 |
| `SIGENERGY2MQTT_MODBUS_RETRIES` | The maximum number of times to retry a Modbus operation if it fails. The default is `3`. [<sup>(More…)</sup>](README.md#opt_modbus_retries) | 2025.10.14 |
| `SIGENERGY2MQTT_MODBUS_TIMEOUT` | The timeout for connecting and receiving Modbus data, in seconds (use decimals for milliseconds). The default is `1.0`. [<sup>(More…)</sup>](README.md#opt_modbus_timeout) | 2025.10.14 |
| `SIGENERGY2MQTT_MODBUS_LOG_LEVEL` | Set the pymodbus log level. Valid values are: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `WARNING` (warnings, errors and critical failures) [<sup>(More…)</sup>](README.md#opt_modbus_log_level) | 2025.5.12 |
| `SIGENERGY2MQTT_SCAN_INTERVAL_LOW` | The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is `600` (seconds), and the minimum value is `1`. [<sup>(More…)</sup>](README.md#opt_modbus_scan_interval_low) | 2025.6.11 |
| `SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM` | The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is `60` (seconds), and the minimum value is `1`. [<sup>(More…)</sup>](README.md#opt_modbus_scan_interval_medium) | 2025.6.11 |
| `SIGENERGY2MQTT_SCAN_INTERVAL_HIGH` | The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is `10` (seconds), and the minimum value is `1`. [<sup>(More…)</sup>](README.md#opt_modbus_scan_interval_high) | 2025.6.11 |
| `SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME` | The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is `5` (seconds), and the minimum value is `1`. [<sup>(More…)</sup>](README.md#opt_modbus_scan_interval_realtime) | 2025.6.11 |

## MQTT Configuration Variables

| Name | Description | Since |
|------|-------------|-------|
| `SIGENERGY2MQTT_MQTT_BROKER` | The hostname or IP address of an MQTT broker (default: `127.0.0.1`) [<sup>(More…)</sup>](README.md#opt_mqtt_broker) | 2025.5.12 |
| `SIGENERGY2MQTT_MQTT_PORT` | The listening port of the MQTT broker (default is 1883, unless `SIGENERGY2MQTT_MQTT_TLS` is `true`, in which case the default is 8883) [<sup>(More…)</sup>](README.md#opt_mqtt_port) | 2025.5.12 |
| `SIGENERGY2MQTT_MQTT_ANONYMOUS` | Set to `true` to connect to MQTT anonymously (i.e. without username/password). [<sup>(More…)</sup>](README.md#opt_mqtt_anonymous) | 2025.5.12 |
| `SIGENERGY2MQTT_MQTT_USERNAME` | A valid username for the MQTT broker [<sup>(More…)</sup>](README.md#opt_mqtt_username) | 2025.5.12 |
| `SIGENERGY2MQTT_MQTT_PASSWORD` | A valid password for the MQTT broker username [<sup>(More…)</sup>](README.md#opt_mqtt_password) | 2025.5.12 |
| `SIGENERGY2MQTT_MQTT_KEEPALIVE` | The maximum period in seconds between communications with the broker. If no other messages are being exchanged, this controls the rate at which the client will send ping messages to the broker. Default is `60` and minimum is `1`. [<sup>(More…)</sup>](README.md#opt_mqtt_keepalive) | 2025.10.15 |
| `SIGENERGY2MQTT_MQTT_TLS` | Set to `true` to enable secure communication to MQTT broker over TLS/SSL. If specified, the default MQTT port is `8883`. [<sup>(More…)</sup>](README.md#opt_mqtt_tls) | 2025.8.11 |
| `SIGENERGY2MQTT_MQTT_TLS_INSECURE` | If `true`, allows insecure communication over TLS. If your broker is using a self-signed certificate, you _must_ set this to `true`. If you are using a valid certificate, set this to `false` (or do not set at all). Ignored unless `SIGENERGY2MQTT_MQTT_TLS` is also `true`. [<sup>(More…)</sup>](README.md#opt_mqtt_tls_insecure) | 2025.8.12 |
| `SIGENERGY2MQTT_MQTT_TRANSPORT` | Sets the MQTT transport mechanism. Must be one of `websockets` or `tcp`. The default is `tcp`. [<sup>(More…)</sup>](README.md#opt_mqtt_transport) | 2026.1.4 |
| `SIGENERGY2MQTT_MQTT_LOG_LEVEL` | Set the paho.mqtt log level. Valid values are: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `WARNING` (warnings, errors and critical failures) [<sup>(More…)</sup>](README.md#opt_mqtt_log_level) | 2025.5.12 |

## State Persistence Configuration Variables

| Name | Description | Since |
|------|-------------|-------|
| `SIGENERGY2MQTT_PERSISTENCE_MQTT_REDUNDANCY` | Set to `true` to enable off-host state redundancy using MQTT retained messages (QoS 2). Default is `true`. [<sup>(More…)</sup>](README.md#opt_persistence_mqtt_redundancy) | 2026.4.5 |
| `SIGENERGY2MQTT_PERSISTENCE_MQTT_STATE_PREFIX` | The MQTT topic prefix used for storing persisted state. (default: `sigenergy2mqtt/_state`) [<sup>(More…)</sup>](README.md#opt_persistence_mqtt_state_prefix) | 2026.4.5 |
| `SIGENERGY2MQTT_PERSISTENCE_DISK_PRIMARY` | Set to `true` to prefer local disk-based state over MQTT if both are available. Default is `true`. [<sup>(More…)</sup>](README.md#opt_persistence_disk_primary) | 2026.4.5 |
| `SIGENERGY2MQTT_PERSISTENCE_CACHE_WARMUP_TIMEOUT` | The maximum time in seconds to wait for the MQTT state cache to warm up from retained messages on startup. (default: `5.0`) [<sup>(More…)</sup>](README.md#opt_persistence_cache_warmup_timeout) | 2026.4.5 |
| `SIGENERGY2MQTT_PERSISTENCE_SYNC_TIMEOUT` | The timeout in seconds for synchronous persistence operations when called from a non-asyncio thread. (default: `5.0`) [<sup>(More…)</sup>](README.md#opt_persistence_sync_timeout) | 2026.4.10 |


## PVOutput Configuration Variables

<table>
  <thead><tr><th>Name</th><th>Description</th><th>Since</th></tr></thead>
  <tbody>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_ENABLED</code></td><td>Set to <code>true</code> to enable status updates to PVOutput. <a href="README.md#opt_pvoutput_enabled"><sup>(More…)</sup></a><td>2025.5.12</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_API_KEY</code></td><td>The API Key for PVOutput <a href="README.md#opt_pvoutput_api_key"><sup>(More…)</sup></a><td>2025.5.12</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID</code></td><td>The PVOutput System ID <a href="README.md#opt_pvoutput_system_id"><sup>(More…)</sup></a><td>2025.5.12</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION</code></td><td><ul>
      <li>If specified with a value of <code>true</code> or <code>consumption</code>, raw consumption data will be sent to PVOutput.</li>
      <li>If specified with a value of <code>net-of-battery</code>, consumption will be calculated as:<br><i>consumption + battery charge - battery discharge</i>.<br>WARNING: This could cause consumption to go negative (e.g. if exporting to take advantage of time-based Feed-In Tariffs). Negative consumption is not allowed by PVOutput, so it will be uploaded as 0.</li>
      <li>If specified with a value of <code>imported</code>, the energy imported from the grid will be sent as consumption.</li>
      <li>If not specified or the value is <code>false</code>, no consumption data will be sent.</ul></td><td>2025.10.21</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXPORTS</code></td><td>Set to <code>true</code> to upload export data to PVOutput. <a href="README.md#opt_pvoutput_exports"><sup>(More…)</sup></a><td>2025.10.1</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_IMPORTS</code></td><td>Set to <code>true</code> to upload import data to PVOutput. <a href="README.md#opt_pvoutput_imports"><sup>(More…)</sup></a><td>2025.10.1</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR</code></td><td>The hour of the day at which the daily totals are sent to PVOutput. The default is <code>23</code> (11pm). Valid values are <code>20</code> to <code>23</code>, or <code>-1</code>.<br><br>If <code>20</code> to <code>23</code> specified, the minute is randomly chosen between 56 and 59.<br><br>If you specify <code>-1</code>, daily uploads will be sent at the same frequency as status updates. If uploaded at the same interval as status updates, PVOutput can overwrite the uploaded values during the day. If this occurs, it will be fixed at end of day. <a href="README.md#opt_pvoutput_output_hour"><sup>(More…)</sup></a><td>2025.5.12</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC</code></td><td>An MQTT topic from which the current temperature can be read. This is used to send the temperature to PVOutput. If not specified, the temperature will not be sent to PVOutput. <a href="README.md#opt_pvoutput_temperature_topic"><sup>(More…)</sup></a><td>2025.7.19</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_VOLTAGE</code></td><td>The source of the voltage value to be sent to PVOutput. Valid values are: <code>phase-a</code>, <code>phase-b</code>, <code>phase-c</code>, <code>l/n-avg</code> (line to neutral average), <code>l/l-avg</code> (line to line average) or <code>pv</code> (average across PV strings). If not specified, defaults to <code>l/n-avg</code>. <a href="README.md#opt_pvoutput_voltage"><sup>(More…)</sup></a><td>2025.11.21</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V7</code></td><td rowspan=6>A sensor class name, or entity_id without the 'sensor.' prefix, that will be used to populate the associated extended data field in PVOutput. If not specified, OR your donation status is not current, the field will not be sent to PVOutput. You can use any sensor with a numeric value.<br><br>If you specify an Energy sensor class, the value sent to PVOutput will be the <i>power</i> value over the Status Interval.<br><br>You can use any sensor that shows a numeric value. If a sensor class is used for multiple sensors (e.g. the <code>PhaseVoltage</code> sensor class is used for phases A, B and C), the sensor values will be averaged and a single value sent to PVOutput. <a href="README.md#opt_pvoutput_v7"><sup>(More…)</sup></a><td rowspan=6>2025.9.16</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V8</code></td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V9</code></td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V10</code></td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V11</code></td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V12</code></td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL</code></td><td>Set the PVOutput log level. Valid values are: <code>DEBUG</code>, <code>INFO</code>, <code>WARNING</code>, <code>ERROR</code> or <code>CRITICAL</code>. Default is <code>WARNING</code> (warnings, errors and critical failures) <a href="README.md#opt_pvoutput_log_level"><sup>(More…)</sup></a><td>2025.5.12</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING</code></td><td>If <code>true</code>, the aggregation of values for uploading to PVOutput will be logged at the DEBUG level. Only applicable if SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL is set to <code>DEBUG</code></td><td>2025.11.11</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING</code></td><td>If <code>true</code>, the updating of values for uploading to PVOutput will be logged at the DEBUG level. Only applicable if SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL is set to <code>DEBUG</code></td><td>2025.11.11</td><tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON</code></td><td>A string of JSON containing an array of date ranges with time periods that describe the peak, shoulder, high-shoulder and off-peak periods. THE TIME PERIODS SPECIFIED MUST MATCH THE TIME PERIODS CONFIGURED IN YOUR PVOUTPUT TARIFF DEFINITIONS. e.g.<br><code>[{"from-date":"2025-11-18T00:00:00.000Z","periods":[{"type":"off-peak","start":"11:00","end":"14:00"},{"type":"peak","start":"15:00","end":"21:00"}]}]</code><br><br>See <a href='sigenergy2mqtt.yaml'>sigenergy2mqtt.yaml</a> for the element names and further details.</td><td>2025.11.17</td><tr>
  </tbody>
</table>


## InfluxDB Configuration Variables

| Name | Description | Since |
|------|-------------|-------|
| `SIGENERGY2MQTT_INFLUX_ENABLED` | Set to `true` to enable publishing of sensor updates to InfluxDB. [<sup>(More…)</sup>](README.md#opt_influxdb_enabled) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_HOST` | The hostname or IP address of the InfluxDB server. [<sup>(More…)</sup>](README.md#opt_influxdb_host) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_PORT` | The listening port of the InfluxDB database (default: `8086`) [<sup>(More…)</sup>](README.md#opt_influxdb_port) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_USERNAME` | A valid user name for the InfluxDB database. [<sup>(More…)</sup>](README.md#opt_influxdb_username) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_PASSWORD` | A valid password for the InfluxDB database username. [<sup>(More…)</sup>](README.md#opt_influxdb_password) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_DATABASE` | The name of the database to use. The default is `sigenergy`. [<sup>(More…)</sup>](README.md#opt_influxdb_database) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_ORG` | The InfluxDB v2 organization name or ID. If not specified, the v1 API will be used. [<sup>(More…)</sup>](README.md#opt_influxdb_org) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_TOKEN` | The InfluxDB v2 authentication token. If supplied, v2 APIs will be used in preference to v1. [<sup>(More…)</sup>](README.md#opt_influxdb_token) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_BUCKET` | The InfluxDB v2 bucket name. If not specified, the value of 'database' will be used as the v2 bucket name. [<sup>(More…)</sup>](README.md#opt_influxdb_bucket) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_DEFAULT_MEASUREMENT` | The default measurement name to use for InfluxDB updates if a sensor does not have a Unit of Measurement defined. If not specified, `state` will be used. [<sup>(More…)</sup>](README.md#opt_influxdb_default_measurement) | 2026.2.3 |
| `SIGENERGY2MQTT_INFLUX_LOAD_HASS_HISTORY` | If `true`, `sigenergy2mqtt` will attempt to load historical data from the Home Assistant InfluxDB database. This will only work if `sigenergy2mqtt` is configured to use the same InfluxDB server as Home Assistant with the same credentials. [<sup>(More…)</sup>](README.md#opt_influxdb_load_hass_history) | 2026.2.3 |
| `SIGENERGY2MQTT_INFLUX_INCLUDE` | A comma-separated list of sensors to include when publishing to InfluxDB, using either the full or partial entity id or sensor class name, or a regular expression to be matched against the entity id or sensor class name. If not specified, all sensors will be included. [<sup>(More…)</sup>](README.md#opt_influxdb_include) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_EXCLUDE` | A comma-separated list of sensors to exclude when publishing to InfluxDB, using either the full or partial entity id or sensor class name, or a regular expression to be matched against the entity id or sensor class name. If not specified, no sensors will be excluded. [<sup>(More…)</sup>](README.md#opt_influxdb_exclude) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_LOG_LEVEL` | Logging level for InfluxDB operations. Defaults to `WARNING` if not specified. [<sup>(More…)</sup>](README.md#opt_influxdb_log_level) | 2026.1.30 |
| `SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT` | InfluxDB write timeout in seconds (default: `30.0`) [<sup>(More…)</sup>](README.md#opt_influxdb_write_timeout) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_READ_TIMEOUT` | InfluxDB read timeout in seconds (default: `120.0`) [<sup>(More…)</sup>](README.md#opt_influxdb_read_timeout) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_BATCH_SIZE` | InfluxDB batch size (default: `100`) [<sup>(More…)</sup>](README.md#opt_influxdb_batch_size) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL` | InfluxDB flush interval in seconds (default: `1.0`) [<sup>(More…)</sup>](README.md#opt_influxdb_flush_interval) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL` | InfluxDB query interval in seconds (default: `0.5`) [<sup>(More…)</sup>](README.md#opt_influxdb_query_interval) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_MAX_RETRIES` | InfluxDB maximum retries (default: `3`) [<sup>(More…)</sup>](README.md#opt_influxdb_max_retries) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS` | InfluxDB connection pool size (default: `100`) [<sup>(More…)</sup>](README.md#opt_influxdb_pool_connections) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE` | InfluxDB connection pool max size (default: `100`) [<sup>(More…)</sup>](README.md#opt_influxdb_pool_maxsize) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE` | InfluxDB sync chunk size (default: `1000`) [<sup>(More…)</sup>](README.md#opt_influxdb_sync_chunk_size) | 2026.2.5 |
| `SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS` | InfluxDB maximum sync workers (default: `4`) [<sup>(More…)</sup>](README.md#opt_influxdb_max_sync_workers) | 2026.2.5 |


## Third Party PV Production Configuration Variables

**NOTE**: _This feature is under consideration for removal in a future release. Have your say in the [discussion](https://github.com/seud0nym/sigenergy2mqtt/discussions/124)._

This feature allows you to report PV generation from a third-party device, either directly from Enphase micro-inverters, or via MQTT for other inverters. This may be useful if you find there are delays in updating third-party PV generation through the Sigenergy Modbus registers.

| Name | Description | Since |
|------|-------------|-------|
| `SIGENERGY2MQTT_SMARTPORT_ENABLED` | Set to `true` to enable interrogation of a third-party device for production data. [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_enabled) | 2025.5.12 |
| `SIGENERGY2MQTT_SMARTPORT_MODULE_NAME` | The name of the module which will be used to obtain third-party device production data. [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_module_name) | 2025.5.12 |
| `SIGENERGY2MQTT_SMARTPORT_HOST` | The IP address or hostname of the third-party device. [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_host) | 2025.5.12 |
| `SIGENERGY2MQTT_SMARTPORT_USERNAME` | The username to authenticate to the third-party device. [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_username) | 2025.5.12 |
| `SIGENERGY2MQTT_SMARTPORT_PASSWORD` | The password to authenticate to the third-party device. [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_password) | 2025.5.12 |
| `SIGENERGY2MQTT_SMARTPORT_PV_POWER` | The sensor class to hold the production data obtained from the third-party device. [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_pv_power) | 2025.5.12 |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC` | The MQTT topic to which to subscribe to obtain the production data for the third-party device. [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_mqtt_topic) | 2025.5.12 |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN` | The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. `1000` if the data is in kW) Default is `1` (Watts). [<sup>(More…)</sup>](README.md#opt_modbus_smart_port_mqtt_gain) | 2025.5.12 |

