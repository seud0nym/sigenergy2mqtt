# Configuration File

The default location for `sigenergy2mqtt.yaml` is in `/etc/` for Linux installations, `/data/` for Docker and `/config/` for Home Assistant (for the Home Assistant app, it should be placed in the `addon_configs/4cee8162_sigenergy2mqtt/` directory). You can also use the `-c` command line option or the `SIGENERGY2MQTT_CONFIG` environment variable to specify a different location and/or filename.

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
