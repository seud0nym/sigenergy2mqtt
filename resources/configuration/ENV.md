# Environment Variables

Environment variables override the configuration file, but *not* command line options.

## General Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_CONFIG` | The path to the JSON configuration file (defaults: `/etc/sigenergy2mqtt.yaml` for Linux, `/data/sigenergy2mqtt.yaml` for Docker and `/config/sigenergy2mqtt.yaml` for Home Assistant) |
| `SIGENERGY2MQTT_LOG_LEVEL` | Set the log level. Valid values are: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `WARNING` (warnings, errors and critical failures) |
| `SIGENERGY2MQTT_DEBUG_SENSOR` | Specify a sensor to be debugged using either the full entity id, a partial entity id, the full sensor class name, or a partial sensor class name. For example, specifying 'daily' would match all sensors with daily in their entity name. If specified, `SIGENERGY2MQTT_LOG_LEVEL` is also forced to `DEBUG` |
| `SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW` | The default value in kW used for sanity checks to validate the maximum and minimum values for actual value of power sensors and the delta value of energy sensors. The default value is `100` kW per second, and readings outside the range are ignored. |
| `SIGENERGY2MQTT_NO_METRICS` | Set to `true` to prevent sigenergy2mqtt from publishing metrics to MQTT. |
| `SIGENERGY2MQTT_CONSUMPTION` | Set the method of calculating the `Plant Consumed Power` sensor. Valid values are: `calculated`, `total` (use the V2.8 `Total Load Power` register), or `general` (use the V2.8 `General Load Power` register). The default is `calculated`. This option is _ignored_ on firmware earlier than that supporting Modbus Protocol V2.8. |

## Home Assistant Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_HASS_ENABLED` | Set to `true` to enable auto-discovery in Home Assistant. |
| `SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX` | The Home Assistant MQTT Discovery topic prefix to use (default: `homeassistant`) |
| `SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX` | The prefix to use for Home Assistant entity names. Example: A prefix of `prefix` will prepend 'prefix ' to names (default: '') |
| `SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX` | The prefix to use for Home Assistant entity IDs. Example: A prefix of `prefix` will prepend 'prefix_' to entity IDs (default: `sigen`) |
| `SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX` | The prefix to use for Home Assistant unique IDs. Example: A prefix of `prefix` will prepend 'prefix_' to unique IDs (default: `sigen`). Once you have set this, you should **NEVER** change it, as it will break existing entities in Home Assistant. |
| `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` | Set to `true` to enable the simplified topic structure (sigenergy2mqtt/object_id/state) instead of the full Home Assistant topic structure (homeassistant/platform/device_id/object_id/state) |
| `SIGENERGY2MQTT_HASS_DISCOVERY_ONLY`| Set to `true` to exit immediately after publishing discovery. Does not read values from the Modbus interface, except to probe for device configuration. |
| `SIGENERGY2MQTT_HASS_EDIT_PCT_BOX` | Set to `true` to use a numeric entry box to change the value of percentage sensors or `false` to use a slider to change the value (default: `false`) |

## Modbus Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY` | Controls auto-discovery of Sigenergy Modbus hosts and device IDs. If `once` is specified, auto-discovery will only occur if no existing auto-discovery results are found. If `force`, auto-discovery will overwrite any previously discovered Modbus hosts and device IDs. If not specified, auto-discovery is disabled. |
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT` | The ping timeout, in seconds, to use when performing auto-discovery of Sigenergy devices on the network. The default is `0.5` seconds. |
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT` | The Modbus timeout, in seconds, to use when performing auto-discovery of Sigenergy devices on the network. The default is `0.25` seconds. |
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES` | The Modbus maximum retry count to use when performing auto-discovery of Sigenergy devices on the network. The default is `0`. |
| `SIGENERGY2MQTT_MODBUS_HOST` | The hostname or IP address of the Sigenergy device. Required unless auto-discovery is enabled. |
| `SIGENERGY2MQTT_MODBUS_PORT` | The Sigenergy device Modbus port number (default: `502`) |
| `SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID` | The Sigenergy device Modbus Device ID. May be specified as a comma-separated list (e.g. `1,2`). (default: `1`) |
| `SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID` | The Sigenergy AC Charger Modbus Device ID. May be specified as a comma-separated list. |
| `SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID` | The Sigenergy DC Charger Modbus Device ID. May be specified as a comma-separated list. |
| `SIGENERGY2MQTT_MODBUS_READ_ONLY` | If `false`, read-only entities will not be published to MQTT. Default is `true`. |
| `SIGENERGY2MQTT_MODBUS_READ_WRITE` | If `false`, read-write entities will not be published to MQTT. Default is `true`. |
| `SIGENERGY2MQTT_MODBUS_WRITE_ONLY` | If `false`, write-only entities will not be published to MQTT. Default is `true`. |
| `SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS`| If `true`, read-write sensors for remote Energy Management System (EMS) integration will NOT be published to MQTT. Default is `false`. Ignored if `SIGENERGY2MQTT_MODBUS_READ_WRITE` is `false`. |
| `SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING` | If `true`, chunking of Modbus reads will be disabled and each register will be read individually. This is NOT recommended for production use. |
| `SIGENERGY2MQTT_MODBUS_RETRIES` | The maximum number of times to retry a Modbus operation if it fails. The default is `3`. |
| `SIGENERGY2MQTT_MODBUS_TIMEOUT` | The timeout for connecting and receiving Modbus data, in seconds (use decimals for milliseconds). The default is `1.0`. |
| `SIGENERGY2MQTT_MODBUS_LOG_LEVEL` | Set the pymodbus log level. Valid values are: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `WARNING` (warnings, errors and critical failures) |
| `SIGENERGY2MQTT_SCAN_INTERVAL_LOW` | The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is `600` (seconds), and the minimum value is `1`. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM` | The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is `60` (seconds), and the minimum value is `1`. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_HIGH` | The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is `10` (seconds), and the minimum value is `1`. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME` | The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is `5` (seconds), and the minimum value is `1`. |

## MQTT Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_MQTT_BROKER` | The hostname or IP address of an MQTT broker (default: `127.0.0.1`) |
| `SIGENERGY2MQTT_MQTT_PORT` | The listening port of the MQTT broker (default is 1883, unless `SIGENERGY2MQTT_MQTT_TLS` is `true`, in which case the default is 8883) |
| `SIGENERGY2MQTT_MQTT_ANONYMOUS` | Set to `true` to connect to MQTT anonymously (i.e. without username/password). |
| `SIGENERGY2MQTT_MQTT_USERNAME` | A valid username for the MQTT broker |
| `SIGENERGY2MQTT_MQTT_PASSWORD` | A valid password for the MQTT broker username |
| `SIGENERGY2MQTT_MQTT_KEEPALIVE` | The maximum period in seconds between communications with the broker. If no other messages are being exchanged, this controls the rate at which the client will send ping messages to the broker. Default is `60` and minimum is `1`. |
| `SIGENERGY2MQTT_MQTT_TLS` | Set to `true` to enable secure communication to MQTT broker over TLS/SSL. If specified, the default MQTT port is `8883`. |
| `SIGENERGY2MQTT_MQTT_TLS_INSECURE` | If `true`, allows insecure communication over TLS. If your broker is using a self-signed certificate, you _must_ set this to `true`. If you are using a valid certificate, set this to `false` (or do not set at all). Ignored unless `SIGENERGY2MQTT_MQTT_TLS` is also `true`. |
| `SIGENERGY2MQTT_MQTT_TRANSPORT` | Sets the MQTT transport mechanism. Must be one of websockets or tcp. The default is tcp. |
| `SIGENERGY2MQTT_MQTT_LOG_LEVEL` | Set the paho.mqtt log level. Valid values are: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `WARNING` (warnings, errors and critical failures) |

## PVOutput Configuration Variables

<table>
  <thead><tr><th>Name</th><th>Description</th></tr></thead>
  <tbody>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_ENABLED</code></td><td>Set to <code>true</code> to enable status updates to PVOutput.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_API_KEY</code></td><td>The API Key for PVOutput</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID</code></td><td>The PVOutput System ID</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION</code></td><td><ul>
      <li>If specified with a value of <code>true</code> or <code>consumption</code>, raw consumption data will be sent to PVOutput.</li>
      <li>If specified with a value of <code>net-of-battery</code>, consumption will be calculated as:<br><i>consumption + battery charge - battery discharge</i>.<br>WARNING: This could cause consumption to go negative (e.g. if exporting to take advantage of time-based Feed-In Tariffs). Negative consumption is not allowed by PVOutput, so it will be uploaded as 0.</li>
      <li>If specified with a value of <code>imported</code>, the energy imported from the grid will be sent as consumption.</li>
      <li>If not specified or the value is <code>false</code>, no consumption data will be sent.</ul></td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXPORTS</code></td><td>Set to <code>true</code> to upload export data to PVOutput.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_IMPORTS</code></td><td>Set to <code>true</code> to upload import data to PVOutput.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR</code></td><td>The hour of the day at which the daily totals are sent to PVOutput. The default is <code>23</code> (11pm). Valid values are <code>20</code> to <code>23</code>, or <code>-1</code>.<br><br>If <code>20</code> to <code>23</code> specified, the minute is randomly chosen between 56 and 59.<br><br>If you specify <code>-1</code>, daily uploads will be sent at the same frequency as status updates. If uploaded at the same interval as status updates, PVOutput can overwrite the uploaded values during the day. If this occurs, it will be fixed at end of day.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC</code></td><td>An MQTT topic from which the current temperature can be read. This is used to send the temperature to PVOutput. If not specified, the temperature will not be sent to PVOutput.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_VOLTAGE</code></td><td>The source of the voltage value to be sent to PVOutput. Valid values are: <code>phase-a</code>, <code>phase-b</code>, <code>phase-c</code>, <code>l/n-avg</code> (line to neutral average), <code>l/l-avg</code> (line to line average) or <code>pv</code> (average across PV strings). If not specified, defaults to <code>l/n-avg</code>.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V7</code></td><td rowspan=6>A sensor class name, or entity_id without the 'sensor.' prefix, that will be used to populate the associated extended data field in PVOutput. If not specified, OR your donation status is not current, the field will not be sent to PVOutput. You can use any sensor with a numeric value.<br><br>If you specify an Energy sensor class, the value sent to PVOutput will be the <i>power</i> value over the Status Interval.<br><br>You can use any sensor that shows a numeric value. If a sensor class is used for multiple sensors (e.g. the <code>PhaseVoltage</code> sensor class is used for phases A, B and C), the sensor values will be averaged and a single value sent to PVOutput.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V8</code></td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V9</code></td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V10</code></td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V11</code></td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_EXT_V12</code></td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL</code></td><td>Set the PVOutput log level. Valid values are: <code>DEBUG</code>, <code>INFO</code>, <code>WARNING</code>, <code>ERROR</code> or <code>CRITICAL</code>. Default is <code>WARNING</code> (warnings, errors and critical failures)</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING</code></td><td>If <code>true</code>, the aggregation of values for uploading to PVOutput will be logged at the DEBUG level. Only applicable if SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL is set to <code>DEBUG</code>.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING</code></td><td>If <code>true</code>, the updating of values for uploading to PVOutput will be logged at the DEBUG level. Only applicable if SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL is set to <code>DEBUG</code>.</td></tr>
    <tr><td><code>SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON</code></td><td>A string of JSON containing an array of date ranges with time periods that describe the peak, shoulder, high-shoulder and off-peak periods. THE TIME PERIODS SPECIFIED MUST MATCH THE TIME PERIODS CONFIGURED IN YOUR PVOUTPUT TARIFF DEFINITIONS. e.g.<br><code>[{"from-date":"2025-11-18T00:00:00.000Z","periods":[{"type":"off-peak","start":"11:00","end":"14:00"},{"type":"peak","start":"15:00","end":"21:00"}]}]</code><br><br>See <a href='sigenergy2mqtt.yaml'>sigenergy2mqtt.yaml</a> for the element names and further details.</td></tr>
  </tbody>
</table>

## Third Party PV Production Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_SMARTPORT_ENABLED` | Enable interrogation of a third-party device for production data. |
| `SIGENERGY2MQTT_SMARTPORT_MODULE_NAME` | The name of the module which will be used to obtain third-party device production data. |
| `SIGENERGY2MQTT_SMARTPORT_HOST` | The IP address or hostname of the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_USERNAME` | The username to authenticate to the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_PASSWORD` | The password to authenticate to the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_PV_POWER` | The sensor class to hold the production data obtained from the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC` | The MQTT topic to which to subscribe to obtain the production data for the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN` | The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. `1000` if the data is in kW) Default is `1` (Watts). |

