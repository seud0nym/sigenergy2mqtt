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

You _can_ configure `sigenergy2mqtt` via the [command line](#command-line-options) and/or [environment variables](#environment-variables), but using a persistent configuration file is a better option, as it provides access to all advanced feature configuration. 

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
  interval-minutes: 5
  consumption: true
```

Notes:
- Configure your MQTT broker IP address/host name and Sigenergy IP address/host name as appropriate for your environment. 
- The number in square brackets after `inverters` is the Device ID (slave address) as advised by your installer. It is usually `1`. If you have multiple inverters, separate them with commas (e.g. `[ 1,2 ]`)
- If your MQTT broker does not require authentication, add the option `anonymous: true` under `mqtt`.
- By default, only entities relating to production, consumption and battery charging/discharging are enabled (all other entities will still appear in Home Assistant, but will be disabled). All other entities are disabled by default. If you want _all_ entities to be initially enabled, set `sensors-enabled-by-default` to `true`. This setting _only_ applies the first time that Home Assistant auto-discovers devices and entities; changing this configuration after first discovery will have no effect. Entities can be enabled and disabled through the Home Assistant user interface.
- The default location for `sigenergy2mqtt.yaml` is in `/etc/`. However, it will also be found in `/data/`. You can also use the `-c` command line option or the `SIGENERGY2MQTT_CONFIG` environment variable to specify a different location and/or filename.

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
  --hass-device-name-prefix [SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX]
                        The prefix to use for Home Assistant entity names. Example: A prefix of 'prefix' will prepend 'prefix ' to names 
                        (default: '')
  --hass-discovery-only
                        Exit immediately after publishing discovery. Does not read values from the Modbus interface, 
                        except to probe for device configuration.
  -b [SIGENERGY2MQTT_MQTT_BROKER], --mqtt-broker [SIGENERGY2MQTT_MQTT_BROKER]
                        The hostname or IP address of an MQTT broker (default: 127.0.0.1)
  --mqtt-port [SIGENERGY2MQTT_MQTT_PORT]
                        The listening port of the MQTT broker (default: 1883)
  --mqtt-anonymous      Connect to MQTT anonymously (i.e. without username/password).
  -u [SIGENERGY2MQTT_MQTT_USERNAME], --mqtt-username [SIGENERGY2MQTT_MQTT_USERNAME]
                        A valid username for the MQTT broker
  -p [SIGENERGY2MQTT_MQTT_PASSWORD], --mqtt-password [SIGENERGY2MQTT_MQTT_PASSWORD]
                        A valid password for the MQTT broker username
  --mqtt-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the paho.mqtt log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. 
                        Default is WARNING (warnings, errors and critical failures)
  -m [SIGENERGY2MQTT_MODBUS_HOST], --modbus-host [SIGENERGY2MQTT_MODBUS_HOST]
                        The hostname or IP address of the Sigenergy device
  --modbus-port [SIGENERGY2MQTT_MODBUS_PORT]
                        The Sigenergy device Modbus port number (default: 502)
  --modbus-slave [SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE]
                        The Sigenergy Inverter Modbus Device ID (Slave ID). May be specified multiple times.
  --modbus-accharger-slave [SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE]
                        The Sigenergy AC Charger Modbus Device ID (Slave ID).
  --modbus-dccharger-slave [SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE]
                        The Sigenergy DC Charger Modbus Device ID (Slave ID).
  --modbus-readonly     Only publish read-only sensors to MQTT. Neither read-write or write-only sensors will be 
                        published if specified.
  --modbus-no-remote-ems
                        Do not publish any read-write sensors for remote Energy Management System (EMS) integration to MQTT. 
                        Ignored if --modbus-read-only is specified.
  --modbus-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. 
                        Default is WARNING (warnings, errors and critical failures)
  --scan-interval-low [SIGENERGY2MQTT_SCAN_INTERVAL_LOW]
                        The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is 600 (seconds), and the minimum value is 300.
  --scan-interval-medium [SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM]
                        The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is 60 (seconds), and the minimum value is 30.
  --scan-interval-high [SIGENERGY2MQTT_SCAN_INTERVAL_HIGH]
                        The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is 10 (seconds), and the minimum value is 5.
  --scan-interval-realtime [SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME]
                        The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is 5 (seconds), and the minimum value is 1.
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
  --pvoutput-consumption
                        Enable sending consumption status to PVOutput.
  --pvoutput-interval [SIGENERGY2MQTT_PVOUTPUT_INTERVAL]
                        The interval in minutes to send data to PVOutput (default: 5). Valid values are 5, 10 or 15 minutes.
  --pvoutput-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING 
                        (warnings, errors and critical failures)
  --clean               Publish empty discovery to delete existing devices, then exits immediately.
  -v, --version         Shows the version number, then exits immediately.
```

### Environment Variables

Environment variables override the configuration file, but *not* command line options.

| Name | Description |
|------|-------------|
| `SIGENERGY2MQTT_CONFIG` | The path to the JSON configuration file (default: /etc/sigenergy2mqtt.yaml) |
| `SIGENERGY2MQTT_LOG_LEVEL` | Set the log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |
| `SIGENERGY2MQTT_DEBUG_SENSOR` | Specify a sensor to be debugged using either the full entity id, a partial entity id, the full sensor class name, or a partial sensor class name. For example, specifying 'daily' would match all sensors with daily in their entity name. If specified, --debug-level is also forced to DEBUG |
| `SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW` | The default value in kW used for sanity checks to validate the maximum and minimum values for actual value of power sensors and the delta value of energy sensors. The default value is 100 kW per second, and readings outside the range are ignored. |
| `SIGENERGY2MQTT_HASS_ENABLED` | Set to 'true' to enable auto-discovery in Home Assistant. |
| `SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX` | The Home Assistant MQTT Discovery topic prefix to use (default: homeassistant) |
| `SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX` | The prefix to use for Home Assistant entity IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to entity IDs (default: sigen) |
| `SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX` | The prefix to use for Home Assistant unique IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to unique IDs (default: sigen). Once you have set this, you should NEVER change it, as it will break existing entities in Home Assistant. |
| `SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX` | The prefix to use for Home Assistant entity names. Example: A prefix of 'prefix' will prepend 'prefix ' to names (default: '') |
| `SIGENERGY2MQTT_HASS_DISCOVERY_ONLY`| Set to 'true' to e xit immediately after publishing discovery. Does not read values from the Modbus interface, except to probe for device configuration. |
| `SIGENERGY2MQTT_MQTT_BROKER` | The hostname or IP address of an MQTT broker (default: 127.0.0.1) |
| `SIGENERGY2MQTT_MQTT_PORT` | The listening port of the MQTT broker (default: 1883) |
| `SIGENERGY2MQTT_MQTT_ANONYMOUS` | Set to 'true' to connect to MQTT anonymously (i.e. without username/password). |
| `SIGENERGY2MQTT_MQTT_USERNAME` | A valid username for the MQTT broker |
| `SIGENERGY2MQTT_MQTT_PASSWORD` | A valid password for the MQTT broker username |
| `SIGENERGY2MQTT_MQTT_LOG_LEVEL` | Set the paho.mqtt log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |
| `SIGENERGY2MQTT_MODBUS_HOST` | The hostname or IP address of the Sigenergy device |
| `SIGENERGY2MQTT_MODBUS_PORT` | The Sigenergy device Modbus port number (default: 502) |
| `SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE` | The Sigenergy device Modbus Device ID (Slave ID). May be specified as a space-separated list (e.g. "1 2"). (default: 1) |
| `SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE` | The Sigenergy AC Charger Modbus Device ID (Slave ID). |
| `SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE` | The Sigenergy DC Charger Modbus Device ID (Slave ID). |
| `SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS`| If true, read-write sensors for remote Energy Management System (EMS) integration will NOT be published to MQTT. Default is false. Ignored if `SIGENERGY2MQTT_MODBUS_READ_WRITE` is false. |
| `SIGENERGY2MQTT_MODBUS_READ_ONLY` | If false, read-only entities will not be published to MQTT. Default is true. |
| `SIGENERGY2MQTT_MODBUS_READ_WRITE` | If false, read-write entities will not be published to MQTT. Default is true. |
| `SIGENERGY2MQTT_MODBUS_WRITE_ONLY` | If false, write-only entities will not be published to MQTT. Default is true. |
| `SIGENERGY2MQTT_MODBUS_LOG_LEVEL` | Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |
| `SIGENERGY2MQTT_SMARTPORT_ENABLED` | Enable interrogation of a third-party device for production data. |
| `SIGENERGY2MQTT_SMARTPORT_MODULE_NAME` | The name of the module which will be used to obtain third-party device production data. |
| `SIGENERGY2MQTT_SMARTPORT_HOST` | The IP address or hostname of the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_USERNAME` | The username to authenticate to the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_PASSWORD` | The password to authenticate to the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_PV_POWER` | The sensor class to hold the production data obtained from the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC` | The MQTT topic to which to subscribe to obtain the production data for the third-party device. |
| `SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN` | The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. 1000 if the data is in kW) Default is 1 (Watts). |
| `SIGENERGY2MQTT_SCAN_INTERVAL_LOW` | The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is 600 (seconds), and the minimum value is 300. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM` | The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is 60 (seconds), and the minimum value is 30. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_HIGH` | The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is 10 (seconds), and the minimum value is 5. |
| `SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME` | The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is 5 (seconds), and the minimum value is 1. |
| `SIGENERGY2MQTT_PVOUTPUT_ENABLED` | Set to 'true' to enable status updates to PVOutput. |
| `SIGENERGY2MQTT_PVOUTPUT_API_KEY` | The API Key for PVOutput |
| `SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID` | The PVOutput System ID |
| `SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION` | Set to 'true' to enable sending consumption status to PVOutput. |
| `SIGENERGY2MQTT_PVOUTPUT_INTERVAL` | The interval in minutes to send data to PVOutput (default: 5). Valid values are 5, 10 or 15 minutes. |
| `SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL` | Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures) |

## MQTT Publish and Subscribe Topics

The topics that are published and subscribed to by `sigenergy2mqtt` can be found [here](sigenergy2mqtt/sensors/README.md).

