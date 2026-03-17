# Configuration Options

Combined reference for CLI flags, environment variables, and YAML configuration keys.

## General

<a id="opt_config_path"></a>
### Config Path
- CLI: `-c, --config`
- ENV: `SIGENERGY2MQTT_CONFIG`
- Config key: `config-path`

The path to the YAML configuration file (defaults: `/etc/sigenergy2mqtt.yaml` for Linux, `/data/sigenergy2mqtt.yaml` for Docker and `/config/sigenergy2mqtt.yaml` for Home Assistant)

<a id="opt_consumption"></a>
### Consumption
- CLI: `--consumption`
- ENV: `SIGENERGY2MQTT_CONSUMPTION`
- Config key: `consumption`

Set the method of calculating the Plant Consumed Power sensor. Valid values are: 'calculated', 'total' (Total Load Power register), or 'general' (General Load Power register). The default is 'total'. This option is ignored on firmware earlier than that supporting Modbus Protocol V2.8.

<a id="opt_language"></a>
### Language
- CLI: `--language`
- ENV: `SIGENERGY2MQTT_LANGUAGE`
- Config key: `language`

The language to use for translations. Valid values are determined from the translation files available in the 'translations' directory.

<a id="opt_log_level"></a>
### Log Level
- CLI: `-l, --log-level`
- ENV: `SIGENERGY2MQTT_LOG_LEVEL`
- Config key: `log-level`

The sigenergy2mqtt default logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, or CRITICAL

<a id="opt_no_ems_mode_check"></a>
### No Ems Mode Check
- CLI: `--no-ems-mode-check`
- ENV: `SIGENERGY2MQTT_NO_EMS_MODE_CHECK`
- Config key: `no-ems-mode-check`

Turn off the validation that disables ESS Max Charging Discharging Limits and PV Max Power Limits when Remote EMS Control Mode is not Command Charging/Discharging. Ignored for firmware SPC113 and later as these limits are globally available in those versions.

<a id="opt_no_metrics"></a>
### No Metrics
- CLI: `--no-metrics`
- ENV: `SIGENERGY2MQTT_NO_METRICS`
- Config key: `no-metrics`

If true, sigenergy2mqtt will not publish any metrics to MQTT.

<a id="opt_repeated_state_publish_interval"></a>
### Repeated State Publish Interval
- CLI: `--repeated-state-publish-interval`
- ENV: `SIGENERGY2MQTT_REPEATED_STATE_PUBLISH_INTERVAL`
- Config key: `repeated-state-publish-interval`

The interval in seconds at which repeated states are published. (Repeated states occur when the state that is acquired is identical to the previous read.) If < 0, repeated states are never published. If 0, repeated states are always published. If > 0, repeated states are published at the specified interval. The default is 0 (always publish).

<a id="opt_sanity_check_default_kw"></a>
### Sanity Check Default Kw
- CLI: `--sanity-check-default-kw`
- ENV: `SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW`
- Config key: `sanity-check-default-kw`

The default value used for sanity checks to validate the maximum and minimum values for power and energy sensors. The specified value is taken as the maximum in kW, and the minimum value is derived by multiplying by -1 (e.g. if the option value is 500, the minimum value will be -500). The value is applied per second, so the actual sanity check applied to a sensor is a multiple of the scan-interval. For energy sensors, the check is applied to the delta value. Readings outside of the range are ignored.

<a id="opt_sanity_check_failures_increment"></a>
### Sanity Check Failures Increment
- CLI: `n/a`
- ENV: `SIGENERGY2MQTT_SANITY_CHECK_FAILURES_INCREMENT`
- Config key: `sanity-check-failures-increment`

If true, the number of sensor read failures will be incremented when a sanity check fails. If false, the number of sensor read failures will not be incremented.

<a id="opt_sensor_debug_logging"></a>
### Sensor Debug Logging
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-debug-logging`

When log-level is DEBUG, controls whether individual individual sensors debugging messages are displayed. If false, individual sensor debugging may be enabled through sensor-overrides.

<a id="opt_state_dir"></a>
### State Dir
- CLI: `n/a`
- ENV: `SIGENERGY2MQTT_STATE_DIR`
- Config key: `state-dir`

The directory in which to store persistent state files (defaults: `/var/lib/` for Linux, `/data/` for Docker and `/config/` for Home Assistant). A sub-directory will be created in the specified directory called `sigenergy2mqtt` to store the files.


## Home Assistant

<a id="opt_home_assistant_device_name_prefix"></a>
### Device Name Prefix
- CLI: `--hass-device-name-prefix`
- ENV: `SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX`
- Config key: `home-assistant.device-name-prefix`

An optional prefix to be prepended to MQTT device names.

<a id="opt_home_assistant_discovery_prefix"></a>
### Discovery Prefix
- CLI: `--hass-discovery-prefix`
- ENV: `SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX`
- Config key: `home-assistant.discovery-prefix`

The Home Assistant discovery prefix. Only specify if you have changed the prefix in Home Assistant.

<a id="opt_home_assistant_edit_pct_box"></a>
### Edit Pct Box
- CLI: `--hass-edit-pct-box`
- ENV: `SIGENERGY2MQTT_HASS_EDIT_PCT_BOX`
- Config key: `home-assistant.edit-pct-box`

When editing percentage sensors, use a numeric entry box to change the value (true) or use a slider to change the value (false).

<a id="opt_home_assistant_enabled"></a>
### Enabled
- CLI: `--hass-enabled`
- ENV: `SIGENERGY2MQTT_HASS_ENABLED`
- Config key: `home-assistant.enabled`

If true, sigenergy2mqtt will publish auto-discovery messages for Home Assistant to automatically configure the devices and entities.

<a id="opt_home_assistant_entity_id_prefix"></a>
### Entity Id Prefix
- CLI: `--hass-entity-id-prefix`
- ENV: `SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX`
- Config key: `home-assistant.entity-id-prefix`

The prefix that will be applied to all unique ids and entity ids.

<a id="opt_home_assistant_republish_discovery_interval"></a>
### Republish Discovery Interval
- CLI: `n/a`
- ENV: `n/a`
- Config key: `home-assistant.republish-discovery-interval`

The interval (in seconds) at which the Home Assistant discovery will be automatically republished.

<a id="opt_home_assistant_sensors_enabled_by_default"></a>
### Sensors Enabled By Default
- CLI: `n/a`
- ENV: `n/a`
- Config key: `home-assistant.sensors-enabled-by-default`

When sensors are initially discovered by Home Assistant, the majority will be disabled in the UI. If you want all sensors to be enabled, set this to true. Note that this setting is only applicable to the first time that the entity is discovered by Home Assistant. Once it has been discovered, you must control enabled/disabled through Home Assistant (unless you make the sensor unpublishable).

<a id="opt_home_assistant_unique_id_prefix"></a>
### Unique Id Prefix
- CLI: `--hass-unique-id-prefix`
- ENV: `SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX`
- Config key: `home-assistant.unique-id-prefix`

The prefix string that will be prepended to the Home Assistant MQTT unique id. This should NEVER be changed after initial discovery has been published.

<a id="opt_home_assistant_use_sigenergy_local_modbus_naming"></a>
### Use Sigenergy Local Modbus Naming
- CLI: `--use-sigenergy-local-modbus-naming`
- ENV: `SIGENERGY2MQTT_USE_SIGENERGY_LOCAL_MODBUS_NAMING`
- Config key: `home-assistant.use-sigenergy-local-modbus-naming`

If true, apply Sigenergy-Local-Modbus entity_id, gain and unit mappings where available to help migration. If enabled, entity-id-prefix must be 'sigen' (default).

<a id="opt_home_assistant_use_simplified_topics"></a>
### Use Simplified Topics
- CLI: `--hass-use-simplified-topics`
- ENV: `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS`
- Config key: `home-assistant.use-simplified-topics`

If true, sigenergy2mqtt will use a simplified topic structure for Home Assistant entities. The topic will be sigenergy2mqtt/object_id/state instead of the full Home Assistant topic structure of homeassistant/platform/device_id/object_id/state.


## InfluxDB

<a id="opt_influxdb_batch_size"></a>
### Batch Size
- CLI: `--influxdb-batch-size`
- ENV: `SIGENERGY2MQTT_INFLUX_BATCH_SIZE`
- Config key: `influxdb.batch-size`

The maximum number of records to buffer before flushing to InfluxDB.

<a id="opt_influxdb_bucket"></a>
### Bucket
- CLI: `--influxdb-bucket`
- ENV: `SIGENERGY2MQTT_INFLUX_BUCKET`
- Config key: `influxdb.bucket`

The InfluxDB v2 bucket name. If not specified, the value of 'database' will be used as the v2 bucket name.

<a id="opt_influxdb_database"></a>
### Database
- CLI: `--influxdb-database`
- ENV: `SIGENERGY2MQTT_INFLUX_DATABASE`
- Config key: `influxdb.database`

The name of the database to use. The default is sigenergy.

<a id="opt_influxdb_default_measurement"></a>
### Default Measurement
- CLI: `--influxdb-default-measurement`
- ENV: `SIGENERGY2MQTT_INFLUX_DEFAULT_MEASUREMENT`
- Config key: `influxdb.default-measurement`

The default measurement name to use for InfluxDB updates if a sensor does not have a Unit of Measurement defined. The default value is "state".

<a id="opt_influxdb_enabled"></a>
### Enabled
- CLI: `--influxdb-enabled`
- ENV: `SIGENERGY2MQTT_INFLUX_ENABLED`
- Config key: `influxdb.enabled`

If true, sigenergy2mqtt will publish the sensor data to InfluxDB.

<a id="opt_influxdb_exclude"></a>
### Exclude
- CLI: `--influxdb-exclude`
- ENV: `SIGENERGY2MQTT_INFLUX_EXCLUDE`
- Config key: `influxdb.exclude`

A list of sensors to include when publishing to InfluxDB, using either the full or partial entity id or sensor class name, or a regular expression to be matched against the entity id or sensor class name. If not specified, no sensors will be excluded.

<a id="opt_influxdb_flush_interval"></a>
### Flush Interval
- CLI: `--influxdb-flush-interval`
- ENV: `SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL`
- Config key: `influxdb.flush-interval`

The maximum interval (in seconds) between buffer flushes.

<a id="opt_influxdb_host"></a>
### Host
- CLI: `--influxdb-host`
- ENV: `SIGENERGY2MQTT_INFLUX_HOST`
- Config key: `influxdb.host`

The hostname or IP address of your InfluxDB database.

<a id="opt_influxdb_include"></a>
### Include
- CLI: `--influxdb-include`
- ENV: `SIGENERGY2MQTT_INFLUX_INCLUDE`
- Config key: `influxdb.include`

A list of sensors to include when publishing to InfluxDB, using either the full or partial entity id or sensor class name, or a regular expression to be matched against the entity id or sensor class name. If not specified, all sensors will be included.

<a id="opt_influxdb_load_hass_history"></a>
### Load Hass History
- CLI: `--influxdb-load-hass-history`
- ENV: `SIGENERGY2MQTT_INFLUX_LOAD_HASS_HISTORY`
- Config key: `influxdb.load-hass-history`

If true, sigenergy2mqtt will attempt to load historical data from the Home Assistant InfluxDB database. This will only work if sigenergy2mqtt is configured to use the same InfluxDB server as Home Assistant with the same credentials.

<a id="opt_influxdb_log_level"></a>
### Log Level
- CLI: `--influxdb-log-level`
- ENV: `SIGENERGY2MQTT_INFLUX_LOG_LEVEL`
- Config key: `influxdb.log-level`

The InfluxDB interface logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, or CRITICAL

<a id="opt_influxdb_max_retries"></a>
### Max Retries
- CLI: `--influxdb-max-retries`
- ENV: `SIGENERGY2MQTT_INFLUX_MAX_RETRIES`
- Config key: `influxdb.max-retries`

The maximum number of retry attempts for failed operations.

<a id="opt_influxdb_max_sync_workers"></a>
### Max Sync Workers
- CLI: `--influxdb-max-sync-workers`
- ENV: `SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS`
- Config key: `influxdb.max-sync-workers`

The maximum number of parallel sync operations.

<a id="opt_influxdb_org"></a>
### Org
- CLI: `--influxdb-org`
- ENV: `SIGENERGY2MQTT_INFLUX_ORGANIZATION`
- Config key: `influxdb.org`

The InfluxDB v2 organization name or ID. If not specified, the v1 API will be used.

<a id="opt_influxdb_password"></a>
### Password
- CLI: `--influxdb-password`
- ENV: `SIGENERGY2MQTT_INFLUX_PASSWORD`
- Config key: `influxdb.password`

The password for your InfluxDB database.

<a id="opt_influxdb_pool_connections"></a>
### Pool Connections
- CLI: `--influxdb-pool-connections`
- ENV: `SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS`
- Config key: `influxdb.pool-connections`

The number of connections to cache in the pool.

<a id="opt_influxdb_pool_maxsize"></a>
### Pool Maxsize
- CLI: `--influxdb-pool-maxsize`
- ENV: `SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE`
- Config key: `influxdb.pool-maxsize`

The maximum number of connections to allow in the pool.

<a id="opt_influxdb_port"></a>
### Port
- CLI: `--influxdb-port`
- ENV: `SIGENERGY2MQTT_INFLUX_PORT`
- Config key: `influxdb.port`

The listening port of the InfluxDB database. The default is 8086.

<a id="opt_influxdb_query_interval"></a>
### Query Interval
- CLI: `--influxdb-query-interval`
- ENV: `SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL`
- Config key: `influxdb.query-interval`

The minimum interval (in seconds) between subsequent queries (rate limiting).

<a id="opt_influxdb_read_timeout"></a>
### Read Timeout
- CLI: `--influxdb-read-timeout`
- ENV: `SIGENERGY2MQTT_INFLUX_READ_TIMEOUT`
- Config key: `influxdb.read-timeout`

The timeout for query and sync operations, in seconds.

<a id="opt_influxdb_sync_chunk_size"></a>
### Sync Chunk Size
- CLI: `--influxdb-sync-chunk-size`
- ENV: `SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE`
- Config key: `influxdb.sync-chunk-size`

The maximum number of records to buffer before flushing to InfluxDB.

<a id="opt_influxdb_token"></a>
### Token
- CLI: `--influxdb-token`
- ENV: `SIGENERGY2MQTT_INFLUX_TOKEN`
- Config key: `influxdb.token`

The InfluxDB v2 authentication token. If supplied, v2 APIs (client or HTTP) will be used in preference to v1.

<a id="opt_influxdb_username"></a>
### Username
- CLI: `--influxdb-username`
- ENV: `SIGENERGY2MQTT_INFLUX_USERNAME`
- Config key: `influxdb.username`

The username for your InfluxDB database.

<a id="opt_influxdb_write_timeout"></a>
### Write Timeout
- CLI: `--influxdb-write-timeout`
- ENV: `SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT`
- Config key: `influxdb.write-timeout`

The timeout for write operations to InfluxDB, in seconds.


## Modbus

<a id="opt_modbus"></a>
### Modbus
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus`

The array of Modbus device configurations. Each device configuration must contain a host, and may optionally contain the port, inverters, ac-chargers, dc-chargers, log-level, read-only, read-write, write-only, no-remote-ems, scan-interval-low, scan-interval-medium, scan-interval-high, scan-interval-realtime, and smart-port configurations. If you have multiple Sigenergy devices, you may specify multiple host/port configurations. You can also automatically discover Sigenergy devices on your network, using either the command line option --modbus-auto-discovery=once or the environment variable SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY=once.

<a id="opt_modbus_auto_discovery"></a>
### Modbus Auto Discovery
- CLI: `--modbus-auto-discovery`
- ENV: `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY`
- Config key: `modbus-auto-discovery`

Controls auto-discovery of Sigenergy Modbus hosts and device IDs. If `once` is specified, auto-discovery will only occur if no existing auto-discovery results are found. If `force`, auto-discovery will overwrite any previously discovered Modbus hosts and device IDs. If not specified, auto-discovery is disabled.

<a id="opt_modbus_auto_discovery_ping_timeout"></a>
### Modbus Auto Discovery Ping Timeout
- CLI: `--modbus-auto-discovery-ping-timeout`
- ENV: `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT`
- Config key: `modbus-auto-discovery-ping-timeout`

The ping timeout, in seconds, to use when performing auto-discovery of Sigenergy devices on the network. The default is `0.5` seconds.

<a id="opt_modbus_auto_discovery_retries"></a>
### Modbus Auto Discovery Retries
- CLI: `--modbus-auto-discovery-retries`
- ENV: `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES`
- Config key: `modbus-auto-discovery-retries`

The Modbus maximum retry count to use when performing auto-discovery of Sigenergy devices on the network. The default is `0`.

<a id="opt_modbus_auto_discovery_timeout"></a>
### Modbus Auto Discovery Timeout
- CLI: `--modbus-auto-discovery-timeout`
- ENV: `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT`
- Config key: `modbus-auto-discovery-timeout`

The Modbus timeout, in seconds, to use when performing auto-discovery of Sigenergy devices on the network. The default is `0.25` seconds.

<a id="opt_modbus_accharger_device_id"></a>
### Accharger Device Id
- CLI: `--modbus-accharger-device-id`
- ENV: `SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID`
- Config key: `modbus[].accharger-device-id`

The Sigenergy AC Charger Modbus Device ID. May be specified as a comma-separated list.

<a id="opt_modbus_dccharger_device_id"></a>
### Dccharger Device Id
- CLI: `--modbus-dccharger-device-id`
- ENV: `SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID`
- Config key: `modbus[].dccharger-device-id`

The Sigenergy DC Charger Modbus Device ID. May be specified as a comma-separated list.

<a id="opt_modbus_disable_chunking"></a>
### Disable Chunking
- CLI: `--modbus-disable-chunking`
- ENV: `SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING`
- Config key: `modbus[].disable-chunking`

If `true`, chunking of Modbus reads will be disabled and each register will be read individually. This is NOT recommended for production use.

<a id="opt_modbus_host"></a>
### Host
- CLI: `-m, --modbus-host`
- ENV: `SIGENERGY2MQTT_MODBUS_HOST`
- Config key: `modbus[].host`

The host name or IP address of a Sigenergy Modbus interface. There may be multiple hosts defined if there are multiple Sigenergy devices.

<a id="opt_modbus_host_ac_chargers"></a>
### Ac Chargers
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.ac-chargers`

The array of device ids to access the AC Charger registers. If do not have an AC Charger, use [ ].

<a id="opt_modbus_host_dc_chargers"></a>
### Dc Chargers
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.dc-chargers`

The array of device ids to access the DC Charger registers. This is normally the same as the inverter device id. If do not have an DC Charger, use [ ].

<a id="opt_modbus_host_disable_chunking"></a>
### Disable Chunking
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.disable-chunking`

If true, chunking of Modbus reads will be disabled and each register will be read individually. This is NOT recommended for production use.

<a id="opt_modbus_host_inverters"></a>
### Inverters
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.inverters`

The array of device ids to access the inverter registers. If you have multiple inverters, specify the device ids separated with commas e.g. [ 1, 2 ] At least 1 inverter device id must be specified (unless the host is an AC Charger).

<a id="opt_modbus_host_log_level"></a>
### Log Level
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.log-level`

The Modbus interface logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, or CRITICAL

<a id="opt_modbus_host_no_remote_ems"></a>
### No Remote Ems
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.no-remote-ems`

If true, read-write entities related to remote Energy Management System (EMS) integration will NOT be published to MQTT. Ignored if read-write option is false.

<a id="opt_modbus_host_port"></a>
### Port
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.port`

The port number used by the Sigenergy Modbus interface.

<a id="opt_modbus_host_read_only"></a>
### Read Only
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.read-only`

If true, all read-only entities will be published to MQTT.

<a id="opt_modbus_host_read_write"></a>
### Read Write
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.read-write`

If true, all read-write entities will be published to MQTT. Specify false to disable read-write entities.

<a id="opt_modbus_host_retries"></a>
### Retries
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.retries`

The maximum number of times to retry a Modbus operation if it fails. The default is 3.

<a id="opt_modbus_host_scan_interval_high"></a>
### Scan Interval High
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.scan-interval-high`

The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is 10 (seconds), and the minimum value is 1.

<a id="opt_modbus_host_scan_interval_low"></a>
### Scan Interval Low
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.scan-interval-low`

The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is 600 (seconds), and the minimum value is 1.

<a id="opt_modbus_host_scan_interval_medium"></a>
### Scan Interval Medium
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.scan-interval-medium`

The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is 60 (seconds), and the minimum value is 1.

<a id="opt_modbus_host_scan_interval_realtime"></a>
### Scan Interval Realtime
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.scan-interval-realtime`

The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is 5 (seconds), and the minimum value is 1.

<a id="opt_modbus_host_smart_port_enabled"></a>
### Enabled
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.enabled`

If true, sigenergy2mqtt will interrogate a third-party device for production data.

<a id="opt_modbus_host_smart_port_module_host"></a>
### Host
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.module.host`

The host name or IP address for the third-party API.

<a id="opt_modbus_host_smart_port_module_name"></a>
### Name
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.module.name`

The name of the module to be loaded to interrogate a third-party device. At this time, the only valid value is enphase.

<a id="opt_modbus_host_smart_port_module_password"></a>
### Password
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.module.password`

The password for authenticating to the third-party API.

<a id="opt_modbus_host_smart_port_module_port"></a>
### Port
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.module.port`

The port number used by the third-party API.

<a id="opt_modbus_host_smart_port_module_pv_power"></a>
### Pv Power
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.module.pv-power`

The Python sensor class used to report PV generation through the third-party API. If specified, the Sigenergy Plant PV Power entity will be disabled by default, and a new entity called Total PV Power will be published that will combine the Sigenergy and third-party PV generation into a single number.

<a id="opt_modbus_host_smart_port_module_username"></a>
### Username
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.module.username`

The username for authenticating to the third-party API.

<a id="opt_modbus_host_smart_port_mqtt_topic"></a>
### Topic
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.mqtt.topic`

The MQTT to subscribe to for updates to third-party PV production to be included in the Total PV Power. Multiple topic/gain configurations may be specified.

<a id="opt_modbus_host_smart_port_mqtt_topic_gain"></a>
### Gain
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.smart-port.mqtt.topic.gain`

The gain to be applied to the PV production published on the topic. For example, if the production is published in kWh, then the gain should be 1000.

<a id="opt_modbus_host_timeout"></a>
### Timeout
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.timeout`

The timeout for connecting and receiving Modbus data, in seconds (use decimals for milliseconds). The default is 1.0.

<a id="opt_modbus_host_write_only"></a>
### Write Only
- CLI: `n/a`
- ENV: `n/a`
- Config key: `modbus[].host.write-only`

If true, all write-only entities (usually power on/off buttons) will be published to MQTT. Specify false to disable write-only entities.

<a id="opt_modbus_inverter_device_id"></a>
### Inverter Device Id
- CLI: `--modbus-inverter-device-id`
- ENV: `SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID`
- Config key: `modbus[].inverter-device-id`

The Sigenergy device Modbus Device ID. May be specified as a comma-separated list (e.g. `1,2`). (default: `1`)

<a id="opt_modbus_log_level"></a>
### Log Level
- CLI: `--modbus-log-level`
- ENV: `SIGENERGY2MQTT_MODBUS_LOG_LEVEL`
- Config key: `modbus[].log-level`

Set the pymodbus log level. Valid values are: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `WARNING` (warnings, errors and critical failures)

<a id="opt_modbus_no_remote_ems"></a>
### No Remote Ems
- CLI: `--modbus-no-remote-ems`
- ENV: `SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS`
- Config key: `modbus[].no-remote-ems`

Do not publish any read-write sensors for remote Energy Management System (EMS) integration to MQTT. Ignored if --modbus-read-only is specified.

<a id="opt_modbus_port"></a>
### Port
- CLI: `--modbus-port`
- ENV: `SIGENERGY2MQTT_MODBUS_PORT`
- Config key: `modbus[].port`

The Sigenergy device Modbus port number (default: `502`)

<a id="opt_modbus_read_only"></a>
### Read Only
- CLI: `--modbus-readonly`
- ENV: `SIGENERGY2MQTT_MODBUS_READ_ONLY`
- Config key: `modbus[].read-only`

If `false`, read-only entities will not be published to MQTT. Default is `true`.

<a id="opt_modbus_read_write"></a>
### Read Write
- CLI: `n/a`
- ENV: `SIGENERGY2MQTT_MODBUS_READ_WRITE`
- Config key: `modbus[].read-write`

If `false`, read-write entities will not be published to MQTT. Default is `true`.

<a id="opt_modbus_retries"></a>
### Retries
- CLI: `--modbus-retries`
- ENV: `SIGENERGY2MQTT_MODBUS_RETRIES`
- Config key: `modbus[].retries`

The maximum number of times to retry a Modbus operation if it fails. The default is `3`.

<a id="opt_modbus_scan_interval_high"></a>
### Scan Interval High
- CLI: `--scan-interval-high`
- ENV: `SIGENERGY2MQTT_SCAN_INTERVAL_HIGH`
- Config key: `modbus[].scan-interval-high`

The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is `10` (seconds), and the minimum value is `1`.

<a id="opt_modbus_scan_interval_low"></a>
### Scan Interval Low
- CLI: `--scan-interval-low`
- ENV: `SIGENERGY2MQTT_SCAN_INTERVAL_LOW`
- Config key: `modbus[].scan-interval-low`

The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is `600` (seconds), and the minimum value is `1`.

<a id="opt_modbus_scan_interval_medium"></a>
### Scan Interval Medium
- CLI: `--scan-interval-medium`
- ENV: `SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM`
- Config key: `modbus[].scan-interval-medium`

The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is `60` (seconds), and the minimum value is `1`.

<a id="opt_modbus_scan_interval_realtime"></a>
### Scan Interval Realtime
- CLI: `--scan-interval-realtime`
- ENV: `SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME`
- Config key: `modbus[].scan-interval-realtime`

The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is `5` (seconds), and the minimum value is `1`.

<a id="opt_modbus_smart_port_enabled"></a>
### Enabled
- CLI: `--smartport-enabled`
- ENV: `SIGENERGY2MQTT_SMARTPORT_ENABLED`
- Config key: `modbus[].smart-port.enabled`

Set to `true` to enable interrogation of a third-party device for production data.

<a id="opt_modbus_smart_port_host"></a>
### Host
- CLI: `--smartport-host`
- ENV: `SIGENERGY2MQTT_SMARTPORT_HOST`
- Config key: `modbus[].smart-port.host`

The IP address or hostname of the third-party device.

<a id="opt_modbus_smart_port_module_name"></a>
### Module Name
- CLI: `--smartport-module-name`
- ENV: `SIGENERGY2MQTT_SMARTPORT_MODULE_NAME`
- Config key: `modbus[].smart-port.module-name`

The name of the module which will be used to obtain third-party device production data.

<a id="opt_modbus_smart_port_mqtt_gain"></a>
### Mqtt Gain
- CLI: `--smartport-mqtt-gain`
- ENV: `SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN`
- Config key: `modbus[].smart-port.mqtt-gain`

The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. `1000` if the data is in kW) Default is `1` (Watts).

<a id="opt_modbus_smart_port_mqtt_topic"></a>
### Mqtt Topic
- CLI: `--smartport-mqtt-topic`
- ENV: `SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC`
- Config key: `modbus[].smart-port.mqtt-topic`

The MQTT topic to which to subscribe to obtain the production data for the third-party device.

<a id="opt_modbus_smart_port_password"></a>
### Password
- CLI: `--smartport-password`
- ENV: `SIGENERGY2MQTT_SMARTPORT_PASSWORD`
- Config key: `modbus[].smart-port.password`

The password to authenticate to the third-party device.

<a id="opt_modbus_smart_port_pv_power"></a>
### Pv Power
- CLI: `--smartport-pv-power`
- ENV: `SIGENERGY2MQTT_SMARTPORT_PV_POWER`
- Config key: `modbus[].smart-port.pv-power`

The sensor class to hold the production data obtained from the third-party device.

<a id="opt_modbus_smart_port_username"></a>
### Username
- CLI: `--smartport-username`
- ENV: `SIGENERGY2MQTT_SMARTPORT_USERNAME`
- Config key: `modbus[].smart-port.username`

The username to authenticate to the third-party device.

<a id="opt_modbus_timeout"></a>
### Timeout
- CLI: `--modbus-timeout`
- ENV: `SIGENERGY2MQTT_MODBUS_TIMEOUT`
- Config key: `modbus[].timeout`

The timeout for connecting and receiving Modbus data, in seconds (use decimals for milliseconds). The default is `1.0`.

<a id="opt_modbus_write_only"></a>
### Write Only
- CLI: `n/a`
- ENV: `SIGENERGY2MQTT_MODBUS_WRITE_ONLY`
- Config key: `modbus[].write-only`

If `false`, write-only entities will not be published to MQTT. Default is `true`.


## MQTT

<a id="opt_mqtt_anonymous"></a>
### Anonymous
- CLI: `--mqtt-anonymous`
- ENV: `SIGENERGY2MQTT_MQTT_ANONYMOUS`
- Config key: `mqtt.anonymous`

If true, the MQTT broker does not require authentication. If false, username and password must be supplied.

<a id="opt_mqtt_broker"></a>
### Broker
- CLI: `-b, --mqtt-broker`
- ENV: `SIGENERGY2MQTT_MQTT_BROKER`
- Config key: `mqtt.broker`

The host name or IP address of the MQTT broker.

<a id="opt_mqtt_keepalive"></a>
### Keepalive
- CLI: `--mqtt-keepalive`
- ENV: `SIGENERGY2MQTT_MQTT_KEEPALIVE`
- Config key: `mqtt.keepalive`

The maximum period in seconds between communications with the broker. If no other messages are being exchanged, this controls the rate at which the client will send ping messages to the broker. Default is 60 and minimum is 1.

<a id="opt_mqtt_log_level"></a>
### Log Level
- CLI: `--mqtt-log-level`
- ENV: `SIGENERGY2MQTT_MQTT_LOG_LEVEL`
- Config key: `mqtt.log-level`

The MQTT interface logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, or CRITICAL

<a id="opt_mqtt_password"></a>
### Password
- CLI: `-p, --mqtt-password`
- ENV: `SIGENERGY2MQTT_MQTT_PASSWORD`
- Config key: `mqtt.password`

The password for authenticating to the MQTT broker. Not required if anonymous: true

<a id="opt_mqtt_port"></a>
### Port
- CLI: `--mqtt-port`
- ENV: `SIGENERGY2MQTT_MQTT_PORT`
- Config key: `mqtt.port`

The port number used by the MQTT broker.

<a id="opt_mqtt_tls"></a>
### Tls
- CLI: `--mqtt-tls`
- ENV: `SIGENERGY2MQTT_MQTT_TLS`
- Config key: `mqtt.tls`

If true, secure communication to the broker over TLS/SSL is enabled.

<a id="opt_mqtt_tls_insecure"></a>
### Tls Insecure
- CLI: `--mqtt-tls-insecure`
- ENV: `SIGENERGY2MQTT_MQTT_TLS_INSECURE`
- Config key: `mqtt.tls-insecure`

If true, allows insecure communication over TLS. If your broker is using a self-signed certificate, you must set this to true. If you are using a valid certificate, set this to false. Ignored unless tls is also true.

<a id="opt_mqtt_transport"></a>
### Transport
- CLI: `--mqtt-transport`
- ENV: `SIGENERGY2MQTT_MQTT_TRANSPORT`
- Config key: `mqtt.transport`

Sets the MQTT transport mechanism. Must be one of websockets or tcp.

<a id="opt_mqtt_username"></a>
### Username
- CLI: `-u, --mqtt-username`
- ENV: `SIGENERGY2MQTT_MQTT_USERNAME`
- Config key: `mqtt.username`

The username for authenticating to the MQTT broker. Not required if anonymous: true


## PVOutput

<a id="opt_pvoutput_api_key"></a>
### Api Key
- CLI: `--pvoutput-api-key`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_API_KEY`
- Config key: `pvoutput.api-key`

The PVOutput API key (create/find your key under https://pvoutput.org/account.jsp)

<a id="opt_pvoutput_calc_debug_logging"></a>
### Calc Debug Logging
- CLI: `n/a`
- ENV: `n/a`
- Config key: `pvoutput.calc-debug-logging`

If true, the aggregation of values for uploading to PVOutput will be logged at the DEBUG level. Only applicable if PVOUTPUT log-level is set to DEBUG.

<a id="opt_pvoutput_consumption"></a>
### Consumption
- CLI: `--pvoutput-consumption`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION`
- Config key: `pvoutput.consumption`

If specified with a value of 'true' or 'consumption', consumption data will be sent to PVOutput. (2025.8.31) With a value of 'imported', the energy imported from the grid will be sent as consumption. If not specified, or the value is 'false', no consumption data will be sent.

<a id="opt_pvoutput_enabled"></a>
### Enabled
- CLI: `--pvoutput-enabled`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_ENABLED`
- Config key: `pvoutput.enabled`

If true, sigenergy2mqtt will update the system status in PVOutput.

<a id="opt_pvoutput_exports"></a>
### Exports
- CLI: `--pvoutput-exports`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_EXPORTS`
- Config key: `pvoutput.exports`

If true, the energy exported to the grid will be sent to PVOutput. If false, exports will not be uploaded. If consumption is enabled, then PVOutput will ignore uploaded exports.

<a id="opt_pvoutput_imports"></a>
### Imports
- CLI: `--pvoutput-imports`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_IMPORTS`
- Config key: `pvoutput.imports`

If true, the energy imported from the grid will be sent to PVOutput. If false, imports will not be uploaded. If consumption is enabled, then PVOutput will ignore uploaded imports.

<a id="opt_pvoutput_log_level"></a>
### Log Level
- CLI: `--pvoutput-log-level`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL`
- Config key: `pvoutput.log-level`

The PVOutput interface logging level. Must be one of: DEBUG, INFO, WARNING, ERROR, or CRITICAL

<a id="opt_pvoutput_output_hour"></a>
### Output Hour
- CLI: `--pvoutput-output-hour`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR`
- Config key: `pvoutput.output-hour`

The hour of the day (20-23) at which the daily totals are sent to PVOutput. The default is 23 (11pm). Valid values are 20 to 23. The minute is randomly chosen between 56 and 59. (2025.10.1) If you specify -1, daily uploads will be sent at the same frequency as status updates.  If uploaded at the same interval as status updates, PVOutput can overwrite the uploaded values during the day. If this occurs, it will be fixed at end of day.

<a id="opt_pvoutput_system_id"></a>
### System Id
- CLI: `--pvoutput-system-id`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID`
- Config key: `pvoutput.system-id`

The PVOutput System ID (create/find your System id under https://pvoutput.org/account.jsp)

<a id="opt_pvoutput_temperature_topic"></a>
### Temperature Topic
- CLI: `--pvoutput-temp-topic`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC`
- Config key: `pvoutput.temperature-topic`

An MQTT topic from which the current temperature can be read. This is used to send the temperature to PVOutput. If not specified, the temperature will not be sent to PVOutput.

<a id="opt_pvoutput_time_periods"></a>
### Time Periods
- CLI: `n/a`
- ENV: `n/a`
- Config key: `pvoutput.time-periods`

An array of time periods that describe the peak, shoulder, high-shoulder and off-peak periods for a specific date range. THE TIME PERIODS SPECIFIED MUST MATCH THE TIME PERIODS CONFIGURED IN YOUR PVOUTPUT TARIFF DEFINITIONS. Multiple date ranges may be specified, and each will have the following attributes: - plan:      An optional name for the time period. Duplicates are permitted. from-date: The start date for the time period in YYYY-MM-DD format. If not specified, the time period is effective immediately. to-date:   The end date for the time period in YYYY-MM-DD format. If not specified, the time period is effective indefinitely. high-shoulder that will be used for all other times not specifically defined in the periods array. If not specified, the default is shoulder. - periods: An array of time period definitions. Each period has the following attributes: - type:  One of off-peak, peak, shoulder, or high-shoulder start: The period start time (0:00-24:00) end:   The period end time (0:00-24:00) days:  The optional array of days to which the period applies. Valid values are: - Mon - Tue - Wed - Thu - Fri - Sat - Sun - Weekdays - Weekends - All The default is [All]. If plans or time periods overlap, the first match will be used.

<a id="opt_pvoutput_update_debug_logging"></a>
### Update Debug Logging
- CLI: `n/a`
- ENV: `n/a`
- Config key: `pvoutput.update-debug-logging`

If true, the updating of values for uploading to PVOutput will be logged at the DEBUG level. Only applicable if PVOUTPUT log-level is set to DEBUG.

<a id="opt_pvoutput_v10"></a>
### V10
- CLI: `--pvoutput-ext-v10`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_EXT_V10`
- Config key: `pvoutput.v10`

A sensor class name that will be used to populate the v10 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. Classes that can be used for multiple sensors (e.g. PVVoltageSensor) will be averaged to determine a single value.

<a id="opt_pvoutput_v11"></a>
### V11
- CLI: `--pvoutput-ext-v11`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_EXT_V11`
- Config key: `pvoutput.v11`

A sensor class name that will be used to populate the v11 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. Classes that can be used for multiple sensors (e.g. PVVoltageSensor) will be averaged to determine a single value.

<a id="opt_pvoutput_v12"></a>
### V12
- CLI: `--pvoutput-ext-v12`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_EXT_V12`
- Config key: `pvoutput.v12`

A sensor class name that will be used to populate the v12 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. Classes that can be used for multiple sensors (e.g. PVVoltageSensor) will be averaged to determine a single value.

<a id="opt_pvoutput_v7"></a>
### V7
- CLI: `--pvoutput-ext-v7`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_EXT_V7`
- Config key: `pvoutput.v7`

A sensor class name that will be used to populate the v7 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. Classes that can be used for multiple sensors (e.g. PVVoltageSensor) will be averaged to determine a single value.

<a id="opt_pvoutput_v8"></a>
### V8
- CLI: `--pvoutput-ext-v8`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_EXT_V8`
- Config key: `pvoutput.v8`

A sensor class name that will be used to populate the v8 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. Classes that can be used for multiple sensors (e.g. PVVoltageSensor) will be averaged to determine a single value.

<a id="opt_pvoutput_v9"></a>
### V9
- CLI: `--pvoutput-ext-v9`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_EXT_V9`
- Config key: `pvoutput.v9`

A sensor class name that will be used to populate the v9 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. Classes that can be used for multiple sensors (e.g. PVVoltageSensor) will be averaged to determine a single value.

<a id="opt_pvoutput_voltage"></a>
### Voltage
- CLI: `--pvoutput-voltage`
- ENV: `SIGENERGY2MQTT_PVOUTPUT_VOLTAGE`
- Config key: `pvoutput.voltage`

The source of the voltage value to be sent to PVOutput. Valid values are: phase-a, phase-b, phase-c, l/n-avg (line to neutral average), l/l-avg (line to line average) or pv (average across PV strings). If not specified, defaults to 'l/n-avg'.


## Sensor Overrides

<a id="opt_sensor_overrides_entity_or_class_debug_logging"></a>
### Debug Logging
- CLI: `-d, --debug-sensor`
- ENV: `SIGENERGY2MQTT_DEBUG_SENSOR`
- Config key: `sensor-overrides.<entity_or_class>.debug-logging`

Specify a sensor to be debugged using either the full entity id, a partial entity id, the full sensor class name, or a partial sensor class name. For example, specifying 'daily' would match all sensors with daily in their entity id. From 2026.1.5, the sensor may also be specified as a regular expression (e.g. ^PowerFactor$ will match *only* the PowerFactor class name, but not InverterPowerFactorAdjustmentFeedback). If specified, `SIGENERGY2MQTT_LOG_LEVEL` is also forced to `DEBUG`.

<a id="opt_sensor_overrides_debug_logging"></a>
### Debug Logging
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.debug-logging`

If true, then debug messages will be logged when log-level is set to DEBUG.

<a id="opt_sensor_overrides_gain"></a>
### Gain
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.gain`

The Sigenergy Modbus Protocol defines a gain to be applied to the raw value read from the interface. e.g. an energy register may have a gain of 1000 to be expressed in kWh. If the gain is over-ridden, you must also over-ride the unit-of-measurement with a correct, corresponding unit.

<a id="opt_sensor_overrides_icon"></a>
### Icon
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.icon`

Specify a different icon for the sensor.

<a id="opt_sensor_overrides_max_failures"></a>
### Max Failures
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.max-failures`

The maximum number of failures before attempts to read the state are tapered off.

<a id="opt_sensor_overrides_max_failures_retry_interval"></a>
### Max Failures Retry Interval
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.max-failures-retry-interval`

After max-failures are reached, this option specifies how long (in seconds) to wait before retrying. The default is to not retry. If specified, this interval will increase by the same amount after each subsequent failure above max-failures.

<a id="opt_sensor_overrides_precision"></a>
### Precision
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.precision`

Specify the display precision (number of decimal places) for this sensor.

<a id="opt_sensor_overrides_publish_raw"></a>
### Publish Raw
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.publish-raw`

If true, the raw state will be published in addition to the state with gain and precision applied. The raw state topic is NOT included in Home Assistant discovery. Ignored if the sensor is not publishable.

<a id="opt_sensor_overrides_publishable"></a>
### Publishable
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.publishable`

If false, the sensor will not be published to MQTT and will not appear in Home Assistant at all.

<a id="opt_sensor_overrides_sanity_check_delta"></a>
### Sanity Check Delta
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.sanity-check-delta`

If true, the sanity check will be applied to the change in value since the last reading, rather than the value itself. This is useful for sensors that are expected to change rapidly, such as power sensors.

<a id="opt_sensor_overrides_sanity_check_max_value"></a>
### Sanity Check Max Value
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.sanity-check-max-value`

Sets a maximum allowable value for this sensor to allow anomalous readings to be ignored. This value must be a RAW value read from, for example, the Modbus interface, BEFORE the gain is applied.

<a id="opt_sensor_overrides_sanity_check_min_value"></a>
### Sanity Check Min Value
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.sanity-check-min-value`

Sets a minimum allowable value for this sensor to allow anomalous readings to be ignored. This value must be a RAW value read from, for example, the Modbus interface, BEFORE the gain is applied.

<a id="opt_sensor_overrides_scan_interval"></a>
### Scan Interval
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.scan-interval`

Change the default scan interval in seconds at which the state of this sensor is read.

<a id="opt_sensor_overrides_unit_of_measurement"></a>
### Unit Of Measurement
- CLI: `n/a`
- ENV: `n/a`
- Config key: `sensor-overrides.unit-of-measurement`

Change the unit of this sensor. Used in conjunction with gain.


## Other

<a id="opt_influxdb"></a>
### Influxdb
- CLI: `n/a`
- ENV: `n/a`
- Config key: `influxdb`

Configuration for sending the sensor data to InfluxDB. Both InfluxDB v2 (token/org/bucket) and v1 (username/password, retention-policy) authentication modes are supported; if a `token` is supplied the v2 API will be used.
