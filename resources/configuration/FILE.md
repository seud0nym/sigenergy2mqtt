# Configuration File

The default location for `sigenergy2mqtt.yaml` is in `/etc/`. However, it will also be found in `/data/`, and for the Home Assistant app, it should be placed in the `addon_configs/4cee8162_sigenergy2mqtt/` directory. You can also use the `-c` command line option or the `SIGENERGY2MQTT_CONFIG` environment variable to specify a different location and/or filename.

The configuration file can be overridden by environment variables and command line parameters.

The complete list of configuration options with associated comments can be found in [sigenergy2mqtt.yaml](sigenergy2mqtt.yaml).

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

## Configuring PVOutput Time Periods

You can define time periods so that `sigenergy2mqtt` can upload exports and imports into their correct tariff time slot (peak, off-peak, shoulder and high-shoulder). The following is a basic example of the `time-periods` configuration:

```yaml
...
pvoutput:
  enabled: true
  ...
  time-periods:
  - plan: Zero Hero
    to-date: 2026-05-31
    periods:
      - type: off-peak
        start: 11:00
        end: 14:00
      - type: peak
        start: 15:00
        end: 21:00
  - plan: Four Free
    from-date: 2026-06-01
    default: peak
    periods:
      - type: off-peak
        start: 10:00
        end: 14:00
```

This example configuration defines two time periods:
  - The first will be active until 2026-05-31, and defines off-peak and peak time ranges. At all other times, shoulder will be applied.
  - The second takes effect from 2026.06.01, and defines only the off-peak period. At all other times, the overridden default of peak will be applied.

The `time-periods` element contains an array of time periods that describe the peak, shoulder, high-shoulder and off-peak periods for a specific date range. THE TIME PERIODS SPECIFIED MUST MATCH THE TIME PERIODS CONFIGURED IN YOUR PVOUTPUT TARIFF DEFINITIONS. Multiple date ranges may be specified, and each can have the following attributes:

- plan:      
  - An optional name for the time period. Duplicates are permitted.
- from-date: 
  - The start date for the time period in YYYY-MM-DD format. If not specified, the time period is effective immediately.
  - **NOTE**: When initially configuring time-periods, it is _strongly_ recommended that you configure the from-date as _tomorrows date_, so that there is no mismatch between the total exports and the sum of the off-peak/peak/shoulder/high-shoulder export figures today.
- to-date:
  - The end date for the time period in YYYY-MM-DD format. If not specified, the time period is effective indefinitely.
- default:
  - One of off-peak, peak, shoulder, or high-shoulder that will be used for all other times not specifically defined in the `periods` array (below). If not specified, the default is `shoulder`.
- periods: 
  - An array of time period definitions. At least one must be specified. Each period has the following attributes:
    - type:  
      - One of off-peak, peak, shoulder, or high-shoulder.
    - start: 
      - The period start time in H:MM format.
    - end:
      - The period end time in H:MM format. 24:00 may be specified for the end of the day.
    - days:
      - The optional array of days to which the period applies. The default is `[All]`. Valid values are:
          - Mon
          - Tue
          - Wed
          - Thu
          - Fri
          - Sat
          - Sun
          - Weekdays
          - Weekends
          - All
                                   
If plans or time periods overlap, the first match will be used.

## Configuring Smart-Port Production

Prior to the V100R001C00SPC108 firmware update, production systems connected to the Sigenergy Gateway Smart-Port were included in the Plant `PV Power` reported by the Modbus interface. In firmware V100R001C00SPC108, the `PV Power` register only reports production from panels connected directly to Sigenergy. Firmware V100R001C00SPC109 adds a new sensor for `Third-Party PV Power`. This register, however, only appears to be updated every 8-10 seconds in my testing with my Enphase micro-inverters, so if you want more frequent updates of `Total PV Power` and `Consumed Power`, then you should enable smart-port in the configuration and configure either the [Enphase Envoy](#enphase-envoy) and/or the [MQTT](#any-system-already-integrated-with-home-assistant) smart-port integrations.

- When smart-port is _not_ enabled in the configuration, the Plant `Total PV Power` sensor will be the sum of Plant `PV Power` and `Third-Party PV Power`. 
- When smart-port _is_ enabled in the configuration, the Plant `Total PV Power` sensor will be the sum of `PV Power` and all configured Smart-Port PV Power sensors ([Enphase Envoy](#enphase-envoy) and/or [MQTT](#any-system-already-integrated-with-home-assistant)). Also, if the Smart-Port PV Power sensor fails to provide updates, `sigenergy2mqtt` will automatically fail-over to using the `Third-Party PV Power` sensor, and fail-back when it becomes available again.

### Enphase Envoy

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

### Any System Already Integrated with Home Assistant

This configuration requires adding the MQTT topics to which `sigenergy2mqtt` will subscribe to get the third-party PV power production updates, and setting up an automation within Home Assistant to publish the third-party PV power production to MQTT whenever it changes.

#### 1. `sigenergy2mqtt` Configuration File
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

#### 2. Home Assistant Automation

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
