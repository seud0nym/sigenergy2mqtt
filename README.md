<img src="https://github.com/seud0nym/sigenergy2mqtt/raw/main/resources/logo.png" alt="sigenergy2mqtt" height="50"><br>
[![License](https://img.shields.io/github/license/seud0nym/sigenergy2mqtt.svg?style=flat)](https://github.com/seud0nym/sigenergy2mqtt/blob/master/LICENSE) 
![Dynamic YAML Badge](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fseud0nym%2Fhome-assistant-addons%2Frefs%2Fheads%2Fmain%2Fsigenergy2mqtt%2Fconfig.yaml&query=%24.version&prefix=v&label=add-on)
[![PyPI - Version](https://img.shields.io/pypi/v/sigenergy2mqtt)](https://pypi.org/project/sigenergy2mqtt/)
[![Docker Image Version](https://img.shields.io/docker/v/seud0nym/sigenergy2mqtt?label=docker)](https://hub.docker.com/r/seud0nym/sigenergy2mqtt)
![Maintenance](https://img.shields.io/maintenance/yes/2025)

`sigenergy2mqtt` is a bridge between the Modbus interface of the Sigenergy energy system and the MQTT lightweight publish/subscribe messaging protocol.

In addition, `sigenergy2mqtt` has several optional features: 

1. It can publish the appropriate messages to allow Home Assistant to automatically discover the Sigenergy devices, simplifying Home Assistant configuration. 
1. Production and consumption data can automatically be uploaded to PVOutput. 
1. It can auto-discover Sigenergy devices and their device IDs.

`sigenergy2mqtt` was inspired the Home Assistant integrations developed by [TypQxQ](https://github.com/TypQxQ/).

# Contents

- [Disclaimer](#disclaimer)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Configuration File](#configuration-file)
  - [Command Line Options](#command-line-options)
  - [Environment Variables](#environment-variables)
- [MQTT Publish and Subscribe Topics](#mqtt-publish-and-subscribe-topics)

## Disclaimer

`sigenergy2mqtt` was developed for my own use, and as such has only been tested in my single-phase environment without AC or DC chargers. In addition, there has been only cursory testing of the write functions. If you find a problem, please raise an issue.

## Installation

Follow the installation guides for supported environments:

* [Home Assistant](resources/home-assistant/README.md)
* [Docker](resources/docker/README.md)
* [Linux](resources/linux/README.md)

## Configuration

When parsing configuration options, `sigenergy2mqtt` looks at the configuration sources in the following order:

1. [Configuration File](#configuration-file)
2. [Environment Variables](#environment-variables) (not applicable to the Home Assistant Add-On)
3. [Command Line Options](#command-line-options) (not applicable to the Home Assistant Add-On)
4. [Home Assistant Add-On UI](#home-assistant-add-on)

This means, for example, that the options specified in the configuration file can be overridden by environment variables and command line options.

### Home Assistant Add-On

The Home Assistant Add-On has its own configuration interface. You can also create a [configuration file](#configuration-file) for more advanced configuration, but where an option is configured in the Home Assistant user interface, it will override the same option in the configuration file.

### Configuration File

The complete list of configuration options with associated comments can be found in [sigenergy2mqtt.yaml](resources/sigenergy2mqtt.yaml).

Example:
```yaml
home-assistant:
  enabled: true
mqtt:
  broker: 127.0.0.1
  username: ""
  password: ""
modbus:
  - host: sigenergy.local
    inverters: [ 1 ]
pvoutput:
  enabled: false
  api-key: your_api_key
  system-id: your_system_id
  consumption: true
```

Notes:
- Configure your MQTT broker IP address/host name and Sigenergy IP address/host name as appropriate for your environment. 
- The number in square brackets after `inverters` is the Device ID as advised by your installer. It is usually `1`. If you have multiple inverters, separate them with commas (e.g. `[ 1,2 ]`)
- If your MQTT broker does not require authentication, add the option `anonymous: true` under `mqtt`.
- By default, only entities relating to production, consumption and battery charging/discharging are enabled in Home Assistant (all other published entities will still appear, but will be disabled). All other entities are disabled by default. If you want _all_ entities to be initially enabled, set `sensors-enabled-by-default` to `true`. This setting _only_ applies the first time that Home Assistant auto-discovers devices and entities; changing this configuration after first discovery will have no effect. Entities can be enabled and disabled through the Home Assistant user interface.
- The default location for `sigenergy2mqtt.yaml` is in `/etc/`. However, it will also be found in `/data/`, and for the Home Assistant add-on, it should be placed in `/config/`. You can also use the `-c` command line option or the `SIGENERGY2MQTT_CONFIG` environment variable to specify a different location and/or filename.

#### Modbus Auto-Discovery

You can automatically discover Sigenergy devices on your network, using either the command line option `--modbus-auto-discovery` or the  environment variable `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY`. Both of these take a value of either `once` or `force`:  If `once` is specified, auto-discovery will only occur if no existing auto-discovery results are found. If `force`, auto-discovery will overwrite any previously discovered Modbus hosts and device IDs. If not specified, auto-discovery is disabled.

Auto-discovery is a lengthy process because your local network has to be scanned for potential Modbus hosts, and once detected there are 247 potential device IDs to be scanned on each host.

<details>
<summary>
<h4>Configuring Smart-Port Production</h4>
</summary>

Prior to the V100R001C00SPC108 firmware update, production systems connected to the Sigenergy Gateway Smart-Port were included in the Plant `PV Power` reported by the Modbus interface. In firmware V100R001C00SPC108, the `PV Power` register only reports production from panels connected directly to Sigenergy. Firmware V100R001C00SPC109 adds a new sensor for `Third-Party PV Power`. This register, however, only appears to be updated every 8-10 seconds in my testing with my Enphase micro-inverters, so if you want more frequent updates of `Total PV Power` and `Consumed Power`, then you should enable smart-port in the configuration and configure either the [Enphase Envoy](#enphase-envoy) and/or the [MQTT](#any-system-already-integrated-with-home-assistant) smart-port integrations.

- When smart-port is _not_ enabled in the configuration, the Plant `Total PV Power` sensor will be the sum of Plant `PV Power` and `Third-Party PV Power`. 
- When smart-port _is_ enabled in the configuration, the Plant `Total PV Power` sensor will be the sum of `PV Power` and all configured Smart-Port PV Power sensors ([Enphase Envoy](#enphase-envoy) and/or [MQTT](#any-system-already-integrated-with-home-assistant)). Also, if the Smart-Port PV Power sensor fails to provide updates, `sigenergy2mqtt` will automatically fail-over to using the `Third-Party PV Power` sensor, and fail-back when it becomes available again.

##### Enphase Envoy

This configuration only works with Enphase Envoy firmware versions prefixed with D7 and D8. Add the Envoy host and login details to your `sigenergy2mqtt` configuration file:

```yaml
...
modbus:
  - host: your_sigenergy_ip_address
    inverters: [ 1 ]
    log-level: INFO
    smart-port:
      enabled: true
      module: 
        name: enphase
        host: your_enphase_envoy_ip_address
        username: your_enphase_enlighten_username
        password: your_enphase_enlighten_password
        pv-power: EnphasePVPower
...
```

Notes:
1. The module `name` must be set to `enphase`.
1. The module `pv-power` configuration must be set to `EnphasePVPower` to create the Plant `Total PV Power` sensor to accumulate the Enphase PV production and Sigenergy PV production.

##### Any System Already Integrated with Home Assistant

This configuration requires adding the MQTT topics to which `sigenergy2mqtt` will subscribe to get the third-party PV power production updates, and setting up an automation within Home Assistant to publish the third-party PV power production to MQTT whenever it changes.

###### 1. `sigenergy2mqtt` Configuration File
```yaml
...
modbus:
  - host: your_sigenergy_ip_address
    inverters: [ 1 ]
    log-level: INFO
    smart-port:
      enabled: true
      mqtt:
        - topic: sigenergy2mqtt/smartport/envoy_nnnnnnnnnn_current_power_production/state
          gain: 1
...
```

Notes:
- The topic can be anything meaningful.
- The gain represents the multiplier to convert the state to watts (so if it is provided in kWh, 1000 is the multiplier).
- You can specify multiple MQTT topic/gain pairs in the configuration file (but command line and environment overrides are limited to a single topic).

###### 2. Home Assistant Automation

Create a new automation and enter a YAML configuration similar to this, using the entity_id that contains the current PV power production from your third-party inverter (this example uses Enphase again):

```yaml
alias: Publish Envoy PV Production
description: "Update sigenergy2mqtt with the current PV production reported by Enphase Envoy"
triggers:
  - trigger: state
    entity_id:
      - sensor.envoy_nnnnnnnnnn_current_power_production
conditions: []
actions:
  - action: mqtt.publish
    data:
      topic: sigenergy2mqtt/smartport/envoy_nnnnnnnnnn_current_power_production/state
      payload: "{{ trigger.to_state.state }}"
mode: queued
```

Notes:
- The topic(s) must match in both the `sigenergy2mqtt` configuration and the Home Assistant automation.
</details>

### Environment Variables

Environment variables override the configuration file, but *not* command line options.

#### General Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_CONFIG` | The path to the JSON configuration file (defaults: `/etc/sigenergy2mqtt.yaml` for Linux, `/data/sigenergy2mqtt.yaml` for Docker and `/config/sigenergy2mqtt.yaml` for Home Assistant) |
| `SIGENERGY2MQTT_LOG_LEVEL` | Set the log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |
| `SIGENERGY2MQTT_DEBUG_SENSOR` | Specify a sensor to be debugged using either the full entity id, a partial entity id, the full sensor class name, or a partial sensor class name. For example, specifying 'daily' would match all sensors with daily in their entity name. If specified, --debug-level is also forced to DEBUG |
| `SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW` | The default value in kW used for sanity checks to validate the maximum and minimum values for actual value of power sensors and the delta value of energy sensors. The default value is 100 kW per second, and readings outside the range are ignored. |
| `SIGENERGY2MQTT_NO_METRICS` | Set to 'true' to prevent sigenergy2mqtt from publishing metrics to MQTT. |

#### Home Assistant Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_HASS_ENABLED` | Set to 'true' to enable auto-discovery in Home Assistant. |
| `SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX` | The Home Assistant MQTT Discovery topic prefix to use (default: homeassistant) |
| `SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX` | The prefix to use for Home Assistant entity IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to entity IDs (default: sigen) |
| `SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX` | The prefix to use for Home Assistant unique IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to unique IDs (default: sigen). Once you have set this, you should NEVER change it, as it will break existing entities in Home Assistant. |
| `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` | Enable the simplified topic structure (sigenergy2mqtt/object_id/state) instead of the full Home Assistant topic structure (homeassistant/platform/device_id/object_id/state) |
| `SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX` | The prefix to use for Home Assistant entity names. Example: A prefix of 'prefix' will prepend 'prefix ' to names (default: '') |
| `SIGENERGY2MQTT_HASS_DISCOVERY_ONLY`| Set to 'true' to e xit immediately after publishing discovery. Does not read values from the Modbus interface, except to probe for device configuration. |

#### MQTT Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_MQTT_BROKER` | The hostname or IP address of an MQTT broker (default: 127.0.0.1) |
| `SIGENERGY2MQTT_MQTT_PORT` | The listening port of the MQTT broker (default is 1883, unless `--mqtt-tls` or `SIGENERGY2MQTT_MQTT_TLS` is specified, in which case the default is 8883) |
| `SIGENERGY2MQTT_MQTT_TLS` | Set to 'true' to enable secure communication to MQTT broker over TLS/SSL. If specified, the default MQTT port is 8883. |
| `SIGENERGY2MQTT_MQTT_TLS_INSECURE` | If 'true', allows insecure communication over TLS. If your broker is using a self-signed certificate, you _must_ set this to 'true'. If you are using a valid certificate, set this to 'false' (or do not set at all). Ignored unless `SIGENERGY2MQTT_MQTT_TLS` is also 'true'. |
| `SIGENERGY2MQTT_MQTT_ANONYMOUS` | Set to 'true' to connect to MQTT anonymously (i.e. without username/password). |
| `SIGENERGY2MQTT_MQTT_USERNAME` | A valid username for the MQTT broker |
| `SIGENERGY2MQTT_MQTT_PASSWORD` | A valid password for the MQTT broker username |
| `SIGENERGY2MQTT_MQTT_LOG_LEVEL` | Set the paho.mqtt log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |

#### Modbus Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY` | Controls auto-discovery of Sigenergy Modbus hosts and device IDs. If 'once' is specified, auto-discovery will only occur if no existing auto-discovery results are found. If 'force', auto-discovery will overwrite any previously discovered Modbus hosts and device IDs. If not specified, auto-discovery is disabled. |
| `SIGENERGY2MQTT_MODBUS_HOST` | The hostname or IP address of the Sigenergy device |
| `SIGENERGY2MQTT_MODBUS_PORT` | The Sigenergy device Modbus port number (default: 502) |
| `SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID` | The Sigenergy device Modbus Device ID. May be specified as a space-separated list (e.g. "1 2"). (default: 1) |
| `SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID` | The Sigenergy AC Charger Modbus Device ID. |
| `SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID` | The Sigenergy DC Charger Modbus Device ID. |
| `SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS`| If true, read-write sensors for remote Energy Management System (EMS) integration will NOT be published to MQTT. Default is false. Ignored if `SIGENERGY2MQTT_MODBUS_READ_WRITE` is false. |
| `SIGENERGY2MQTT_MODBUS_READ_ONLY` | If false, read-only entities will not be published to MQTT. Default is true. |
| `SIGENERGY2MQTT_MODBUS_READ_WRITE` | If false, read-write entities will not be published to MQTT. Default is true. |
| `SIGENERGY2MQTT_MODBUS_WRITE_ONLY` | If false, write-only entities will not be published to MQTT. Default is true. |
| `SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING` | If true, chunking of Modbus reads will be disabled and each register will be read individually. |
| `SIGENERGY2MQTT_MODBUS_LOG_LEVEL` | Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |
| `SIGENERGY2MQTT_SCAN_INTERVAL_LOW` | The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is 600 (seconds), and the minimum value is 300. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM` | The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is 60 (seconds), and the minimum value is 30. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_HIGH` | The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is 10 (seconds), and the minimum value is 5. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME` | The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is 5 (seconds), and the minimum value is 1. |

#### PVOutput Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_PVOUTPUT_ENABLED` | Set to 'true' to enable status updates to PVOutput. |
| `SIGENERGY2MQTT_PVOUTPUT_API_KEY` | The API Key for PVOutput |
| `SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID` | The PVOutput System ID |
| `SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION` | If specified with a value of 'true' or 'consumption', consumption data will be sent to PVOutput. With a value of 'imported', the energy imported from the grid will be sent as consumption. If not specified or the value is 'false', no consumption data will be sent. |
| `SIGENERGY2MQTT_PVOUTPUT_EXPORTS` | Set to 'true' to upload export data to PVOutput. |
| `SIGENERGY2MQTT_PVOUTPUT_IMPORTS` | Set to 'true' to upload import data to PVOutput. |
| `SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR` | The hour of the day (20-23) at which the daily totals are sent to PVOutput. The default is 23 (11pm). Valid values are 20 to 23. The minute is randomly chosen between 51 and 58. If you specify -1, daily uploads will be sent at the same frequency as status updates. |
| `SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC` | An MQTT topic from which the current temperature can be read. This is used to send the temperature to PVOutput. If not specified, the temperature will not be sent to PVOutput. |
| `SIGENERGY2MQTT_PVOUTPUT_EXT_V7` | A sensor class name that will be used to populate the v7 extended data field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. |
| `SIGENERGY2MQTT_PVOUTPUT_EXT_V8` | A sensor class name that will be used to populate the v8 extended data field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. |
| `SIGENERGY2MQTT_PVOUTPUT_EXT_V9` | A sensor class name that will be used to populate the v9 extended data field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. |
 | `SIGENERGY2MQTT_PVOUTPUT_EXT_V10` | A sensor class name that will be used to populate the v10 extended data field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. |
| `SIGENERGY2MQTT_PVOUTPUT_EXT_V11` | A sensor class name that will be used to populate the v11 extended data field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. |
| `SIGENERGY2MQTT_PVOUTPUT_EXT_V12` | A sensor class name that will be used to populate the v12 extended data field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value. |
| `SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL` | Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |

#### Third Party PV Production Configuration Variables

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_SMARTPORT_ENABLED` | Enable interrogation of a third-party device for production data. |
| `SIGENERGY2MQTT_SMARTPORT_MODULE_NAME` | The name of the module which will be used to obtain third-party device production data. |
| `SIGENERGY2MQTT_SMARTPORT_HOST` | The IP address or hostname of the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_USERNAME` | The username to authenticate to the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_PASSWORD` | The password to authenticate to the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_PV_POWER` | The sensor class to hold the production data obtained from the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC` | The MQTT topic to which to subscribe to obtain the production data for the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN` | The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. 1000 if the data is in kW) Default is 1 (Watts). |

### Command Line Options

Command line options override both environment variables and the configuration file.

```
  -h, --help            show this help message and exit
  -c [SIGENERGY2MQTT_CONFIG], --config [SIGENERGY2MQTT_CONFIG]
                        The path to the JSON configuration file (default: /etc/sigenergy2mqtt.yaml)
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING 
                        (warnings, errors and critical failures)
  -d SIGENERGY2MQTT_DEBUG_SENSOR, --debug-sensor SIGENERGY2MQTT_DEBUG_SENSOR
                        Specify a sensor to be debugged using either the full entity id, a partial entity id, the full sensor class name, 
                        or a partial sensor class name. For example, specifying 'daily' would match all sensors with daily in their entity 
                        name. If specified, --debug-level is also forced to DEBUG
  --sanity-check-default-kw SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW
                        The default value in kW used for sanity checks to validate the maximum and minimum values for actual value of 
                        power sensors and the delta value of energy sensors. The default value is 100 kW per second, and readings outside 
                        the range are ignored. 
  --no-metrics          Do not publish any sigenergy2mqtt metrics.
  --hass-enabled        Enable auto-discovery in Home Assistant.
  --hass-discovery-prefix [SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX]
                        The Home Assistant MQTT Discovery topic prefix to use (default: homeassistant)
  --hass-entity-id-prefix [SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX]
                        The prefix to use for Home Assistant entity IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to entity IDs
                         (default: sigen)
  --hass-unique-id-prefix [SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX]
                        The prefix to use for Home Assistant unique IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to unique IDs
                         (default: sigen). Once you have set this, you should NEVER change it, as it will break existing entities in 
                         Home Assistant.
  --hass-use-simplified-topics
                        Enable the simplified topic structure (sigenergy2mqtt/object_id/state) instead of the full Home Assistant topic
                        structure (homeassistant/platform/device_id/object_id/state)
  --hass-device-name-prefix [SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX]
                        The prefix to use for Home Assistant entity names. Example: A prefix of 'prefix' will prepend 'prefix ' to names 
                        (default: '')
  --hass-discovery-only
                        Exit immediately after publishing discovery. Does not read values from the Modbus interface, 
                        except to probe for device configuration.
  -b [SIGENERGY2MQTT_MQTT_BROKER], --mqtt-broker [SIGENERGY2MQTT_MQTT_BROKER]
                        The hostname or IP address of an MQTT broker (default: 127.0.0.1)
  --mqtt-port [SIGENERGY2MQTT_MQTT_PORT]
                        The listening port of the MQTT broker (default is 1883, unless --mqtt-tls is specified, in which case the default 
                        is 8883)
  --mqtt-tls            Enable secure communication to MQTT broker over TLS/SSL. If specified, the default MQTT port is 8883.
  --mqtt-tls-insecure   Enables insecure communication over TLS. If your broker is using a self-signed certificate, you must specify this 
                        option. Ignored unless --mqtt-tls is also specified.
  --mqtt-anonymous      Connect to MQTT anonymously (i.e. without username/password).  If specified, the --mqtt-username and 
                        --mqtt-password options are ignored.
  -u [SIGENERGY2MQTT_MQTT_USERNAME], --mqtt-username [SIGENERGY2MQTT_MQTT_USERNAME]
                        A valid username for the MQTT broker
  -p [SIGENERGY2MQTT_MQTT_PASSWORD], --mqtt-password [SIGENERGY2MQTT_MQTT_PASSWORD]
                        A valid password for the MQTT broker username
  --modbus-disable-chunking
                        Disable Modbus chunking when reading registers and read each register individually.
  --mqtt-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the paho.mqtt log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. 
                        Default is WARNING (warnings, errors and critical failures)
  --modbus-auto-discovery {once,force}
                        Attempt to auto-discover Sigenergy Modbus hosts and device IDs. If 'once' is specified, auto-discovery will only 
                        occur if no existing auto-discovery results are found. If 'force', auto-discovery will overwrite any previously 
                        discovered Modbus hosts and device IDs. If not specified, auto-discovery is disabled.
  -m [SIGENERGY2MQTT_MODBUS_HOST], --modbus-host [SIGENERGY2MQTT_MODBUS_HOST]
                        The hostname or IP address of the Sigenergy device
  --modbus-port [SIGENERGY2MQTT_MODBUS_PORT]
                        The Sigenergy device Modbus port number (default: 502)
  --modbus-inverter-device-id [SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID]
                        The Sigenergy Inverter Modbus Device ID. Multiple device IDS may be specified, separated by spaces.
  --modbus-accharger-device-id [SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID]
                        The Sigenergy AC Charger Modbus Device ID.
  --modbus-dccharger-device-id [SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID]
                        The Sigenergy DC Charger Modbus Device ID.
  --modbus-readonly     Only publish read-only sensors to MQTT. Neither read-write or write-only sensors will be 
                        published if specified.
  --modbus-no-remote-ems
                        Do not publish any read-write sensors for remote Energy Management System (EMS) integration to MQTT. 
                        Ignored if --modbus-read-only is specified.
  --modbus-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. 
                        Default is WARNING (warnings, errors and critical failures)
  --scan-interval-low [SIGENERGY2MQTT_SCAN_INTERVAL_LOW]
                        The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is 600, 
                        and the minimum value is 300.
  --scan-interval-medium [SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM]
                        The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is 60, 
                        and the minimum value is 30.
  --scan-interval-high [SIGENERGY2MQTT_SCAN_INTERVAL_HIGH]
                        The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is 10, 
                        and the minimum value is 5.
  --scan-interval-realtime [SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME]
                        The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is 5, 
                        and the minimum value is 1.
  --smartport-enabled   Enable interrogation of a third-party device for production data.
  --smartport-module-name [SIGENERGY2MQTT_SMARTPORT_MODULE_NAME]
                        The name of the module which will be used to obtain third-party device production data.
  --smartport-host [SIGENERGY2MQTT_SMARTPORT_HOST]
                        The IP address or hostname of the third-party device.
  --smartport-username [SIGENERGY2MQTT_SMARTPORT_USERNAME]
                        The username to authenticate to the third-party device.
  --smartport-password [SIGENERGY2MQTT_SMARTPORT_PASSWORD]
                        The password to authenticate to the third-party device.
  --smartport-pv-power [SIGENERGY2MQTT_SMARTPORT_PV_POWER]
                        The sensor class to hold the production data obtained from the third-party device.
  --smartport-mqtt-topic [SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC]
                        The MQTT topic to which to subscribe to obtain the production data for the third-party device.
  --smartport-mqtt-gain [SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN]
                        The gain to be applied to the production data for the third-party device obtained from the MQTT topic. 
                        (e.g. 1000 if the data is in kW) Default is 1 (Watts).
  --pvoutput-enabled    Enable status updates to PVOutput.
  --pvoutput-api-key [SIGENERGY2MQTT_PVOUTPUT_API_KEY]
                        The API Key for PVOutput
  --pvoutput-system-id [SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID]
                        The PVOutput System ID
  --pvoutput-consumption [SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION]
                        Enable consumption data to be sent to PVOutput. If specified without a value, or with a value of 'true'
                        or 'consumption', consumption data will be sent. With a value of 'imported', the energy imported from  
                        the grid will be sent. If not specified, no consumption data is sent.
  --pvoutput-exports    Enable to send export data to PVOutput.
  --pvoutput-imports    Enable to send import data to PVOutput.
  --pvoutput-output-hour [SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR]
                        The hour of the day (20-23) at which the daily totals are sent to PVOutput. The default is 23 (11pm). 
                        Valid values are 20 to 23. The minute is randomly chosen between 51 and 58. If you specify -1, daily 
                        uploads will be sent at the same frequency as status updates.
  --pvoutput-temp-topic [SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC]
                        An MQTT topic from which the current temperature can be read. This is used to send the temperature to PVOutput. 
                        If not specified, the temperature will not be sent to PVOutput.
  --pvoutput-ext-v7 [SIGENERGY2MQTT_PVOUTPUT_EXT_V7]
                        An sensor class name that will be used to populate the v7 extended data field in PVOutput. If not specified,
                        OR your donation status is not current, this field will not be sent to PVOutput. 
                        You can use any sensor with a numeric value.
  --pvoutput-ext-v8 [SIGENERGY2MQTT_PVOUTPUT_EXT_V8]
                        An sensor class name that will be used to populate the v8 extended data field in PVOutput. If not specified,
                        OR your donation status is not current, this field will not be sent to PVOutput. 
                        You can use any sensor with a numeric value.
  --pvoutput-ext-v9 [SIGENERGY2MQTT_PVOUTPUT_EXT_V9]
                        An sensor class name that will be used to populate the v9 extended data field in PVOutput. If not specified,
                        OR your donation status is not current, this field will not be sent to PVOutput. 
                        You can use any sensor with a numeric value.
  --pvoutput-ext-v10 [SIGENERGY2MQTT_PVOUTPUT_EXT_V10]
                        An sensor class name that will be used to populate the v10 extended data field in PVOutput. If not specified,
                        OR your donation status is not current, this field will not be sent to PVOutput. 
                        You can use any sensor with a numeric value.
  --pvoutput-ext-v11 [SIGENERGY2MQTT_PVOUTPUT_EXT_V11]
                        An sensor class name that will be used to populate the v11 extended data field in PVOutput. If not specified,
                        OR your donation status is not current, this field will not be sent to PVOutput. 
                        You can use any sensor with a numeric value.
  --pvoutput-ext-v12 [SIGENERGY2MQTT_PVOUTPUT_EXT_V12]
                        An sensor class name that will be used to populate the v12 extended data field in PVOutput. If not specified,
                        OR your donation status is not current, this field will not be sent to PVOutput. 
                        You can use any sensor with a numeric value.
  --pvoutput-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING 
                        (warnings, errors and critical failures)
  --clean               Publish empty discovery to delete existing devices, then exits immediately.
  -v, --version         Shows the version number, then exits immediately.
```

## MQTT Publish and Subscribe Topics

The topics that are published and subscribed to by `sigenergy2mqtt` can be found [here](sigenergy2mqtt/sensors/README.md).

