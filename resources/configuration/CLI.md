# Command Line Options

```
usage: -c [-h] [-c [SIGENERGY2MQTT_CONFIG]]
          [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
          [-d SIGENERGY2MQTT_DEBUG_SENSOR]
          [--sanity-check-default-kw SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW]
          [--no-metrics] [--hass-enabled]
          [--hass-discovery-prefix [SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX]]
          [--hass-entity-id-prefix [SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX]]
          [--hass-unique-id-prefix [SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX]]
          [--hass-use-simplified-topics]
          [--hass-device-name-prefix [SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX]]
          [--hass-discovery-only] [-b [SIGENERGY2MQTT_MQTT_BROKER]]
          [--mqtt-port [SIGENERGY2MQTT_MQTT_PORT]]
          [--mqtt-keepalive [SIGENERGY2MQTT_MQTT_KEEPALIVE]] [--mqtt-tls]
          [--mqtt-tls-insecure] [--mqtt-anonymous]
          [-u [SIGENERGY2MQTT_MQTT_USERNAME]]
          [-p [SIGENERGY2MQTT_MQTT_PASSWORD]]
          [--mqtt-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
          [--modbus-auto-discovery {once,force}]
          [--modbus-auto-discovery-ping-timeout [SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT]]
          [--modbus-auto-discovery-timeout [SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT]]
          [--modbus-auto-discovery-retries [SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES]]
          [-m [SIGENERGY2MQTT_MODBUS_HOST]]
          [--modbus-port [SIGENERGY2MQTT_MODBUS_PORT]]
          [--modbus-slave [SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE ...]]
          [--modbus-inverter-device-id [SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID ...]]
          [--modbus-accharger-slave [SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE ...]]
          [--modbus-accharger-device-id [SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID ...]]
          [--modbus-dccharger-slave [SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE ...]]
          [--modbus-dccharger-device-id [SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID ...]]
          [--modbus-readonly] [--modbus-no-remote-ems]
          [--modbus-timeout [SIGENERGY2MQTT_MODBUS_TIMEOUT]]
          [--modbus-retries [SIGENERGY2MQTT_MODBUS_RETRIES]]
          [--modbus-disable-chunking]
          [--modbus-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
          [--scan-interval-low [SIGENERGY2MQTT_SCAN_INTERVAL_LOW]]
          [--scan-interval-medium [SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM]]
          [--scan-interval-high [SIGENERGY2MQTT_SCAN_INTERVAL_HIGH]]
          [--scan-interval-realtime [SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME]]
          [--smartport-enabled]
          [--smartport-module-name [SIGENERGY2MQTT_SMARTPORT_MODULE_NAME]]
          [--smartport-host [SIGENERGY2MQTT_SMARTPORT_HOST]]
          [--smartport-username [SIGENERGY2MQTT_SMARTPORT_USERNAME]]
          [--smartport-password [SIGENERGY2MQTT_SMARTPORT_PASSWORD]]
          [--smartport-pv-power [SIGENERGY2MQTT_SMARTPORT_PV_POWER]]
          [--smartport-mqtt-topic [SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC]]
          [--smartport-mqtt-gain [SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN]]
          [--pvoutput-enabled]
          [--pvoutput-api-key [SIGENERGY2MQTT_PVOUTPUT_API_KEY]]
          [--pvoutput-system-id [SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID]]
          [--pvoutput-consumption [SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION]]
          [--pvoutput-exports] [--pvoutput-imports]
          [--pvoutput-output-hour [SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR]]
          [--pvoutput-interval [SIGENERGY2MQTT_PVOUTPUT_INTERVAL]]
          [--pvoutput-temp-topic [SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC]]
          [--pvoutput-voltage [{phase-a,phase-b,phase-c,l/n-avg,l/l-avg}]]
          [--pvoutput-ext-v7 [SIGENERGY2MQTT_PVOUTPUT_EXT_V7]]
          [--pvoutput-ext-v8 [SIGENERGY2MQTT_PVOUTPUT_EXT_V8]]
          [--pvoutput-ext-v9 [SIGENERGY2MQTT_PVOUTPUT_EXT_V9]]
          [--pvoutput-ext-v10 [SIGENERGY2MQTT_PVOUTPUT_EXT_V10]]
          [--pvoutput-ext-v11 [SIGENERGY2MQTT_PVOUTPUT_EXT_V11]]
          [--pvoutput-ext-v12 [SIGENERGY2MQTT_PVOUTPUT_EXT_V12]]
          [--pvoutput-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--clean]
          [-v]

Reads the Sigenergy modbus interface and publishes the data to MQTT. The data
will be published to MQTT in the Home Assistant MQTT Discovery format.

options:
  -h, --help            show this help message and exit
  -c, --config [SIGENERGY2MQTT_CONFIG]
                        The path to the JSON configuration file (default:
                        /etc/sigenergy2mqtt.yaml)
  -l, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the log level. Valid values are: DEBUG, INFO,
                        WARNING, ERROR or CRITICAL. Default is WARNING
                        (warnings, errors and critical failures)
  -d, --debug-sensor SIGENERGY2MQTT_DEBUG_SENSOR
                        Specify a sensor to be debugged using either the full
                        entity id, a partial entity id, the full sensor class
                        name, or a partial sensor class name. For example,
                        specifying 'daily' would match all sensors with daily
                        in their entity name. If specified, --debug-level is
                        also forced to DEBUG
  --sanity-check-default-kw SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW
                        The default value in kW used for sanity checks to
                        validate the maximum and minimum values for actual
                        value of power sensors and the delta value of energy
                        sensors. The default value is 100 kW per second, and
                        readings outside the range are ignored.
  --no-metrics          Do not publish any sigenergy2mqtt metrics.
  --hass-enabled        Enable auto-discovery in Home Assistant.
  --hass-discovery-prefix [SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX]
                        The Home Assistant MQTT Discovery topic prefix to use
                        (default: homeassistant)
  --hass-entity-id-prefix [SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX]
                        The prefix to use for Home Assistant entity IDs.
                        Example: A prefix of 'prefix' will prepend 'prefix_'
                        to entity IDs (default: sigen)
  --hass-unique-id-prefix [SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX]
                        The prefix to use for Home Assistant unique IDs.
                        Example: A prefix of 'prefix' will prepend 'prefix_'
                        to unique IDs (default: sigen). Once you have set
                        this, you should NEVER change it, as it will break
                        existing entities in Home Assistant.
  --hass-use-simplified-topics
                        Enable the simplified topic structure
                        (sigenergy2mqtt/object_id/state) instead of the full
                        Home Assistant topic structure
                        (homeassistant/platform/device_id/object_id/state)
  --hass-device-name-prefix [SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX]
                        The prefix to use for Home Assistant entity names.
                        Example: A prefix of 'prefix' will prepend 'prefix '
                        to names (default: '')
  --hass-discovery-only
                        Exit immediately after publishing discovery. Does not
                        read values from the Modbus interface, except to probe
                        for device configuration.
  -b, --mqtt-broker [SIGENERGY2MQTT_MQTT_BROKER]
                        The hostname or IP address of an MQTT broker (default:
                        127.0.0.1)
  --mqtt-port [SIGENERGY2MQTT_MQTT_PORT]
                        The listening port of the MQTT broker (default is
                        1883, unless --mqtt-tls is specified, in which case
                        the default is 8883)
  --mqtt-keepalive [SIGENERGY2MQTT_MQTT_KEEPALIVE]
                        The maximum period in seconds between communications
                        with the broker. If no other messages are being
                        exchanged, this controls the rate at which the client
                        will send ping messages to the broker. Default is 60
                        and minimum is 1.
  --mqtt-tls            Enable secure communication to MQTT broker over
                        TLS/SSL. If specified, the default MQTT port is 8883.
  --mqtt-tls-insecure   Enables insecure communication over TLS. If your
                        broker is using a self-signed certificate, you must
                        specify this option. Ignored unless --mqtt-tls is also
                        specified.
  --mqtt-anonymous      Allow anonymous connection to MQTT broker (i.e.
                        without username/password). If specified, the --mqtt-
                        username and --mqtt-password options are ignored.
  -u, --mqtt-username [SIGENERGY2MQTT_MQTT_USERNAME]
                        A valid username for the MQTT broker
  -p, --mqtt-password [SIGENERGY2MQTT_MQTT_PASSWORD]
                        A valid password for the MQTT broker username
  --mqtt-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the paho.mqtt log level. Valid values are: DEBUG,
                        INFO, WARNING, ERROR or CRITICAL. Default is WARNING
                        (warnings, errors and critical failures)
  --modbus-auto-discovery {once,force}
                        Attempt to auto-discover Sigenergy Modbus hosts and
                        device IDs. If 'once' is specified, auto-discovery
                        will only occur if no existing auto-discovery results
                        are found. If 'force', auto-discovery will overwrite
                        any previously discovered Modbus hosts and device IDs.
                        If not specified, auto-discovery is disabled.
  --modbus-auto-discovery-ping-timeout [SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT]
                        The ping timeout, in seconds, to use when performing
                        auto-discovery of Sigenergy devices on the network.
                        The default is 0.5 seconds.
  --modbus-auto-discovery-timeout [SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT]
                        The Modbus timeout, in seconds, to use when performing
                        auto-discovery of Sigenergy devices on the network.
                        The default is 0.25 seconds.
  --modbus-auto-discovery-retries [SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES]
                        The Modbus maximum retry count to use when performing
                        auto-discovery of Sigenergy devices on the network.
                        The default is 0.
  -m, --modbus-host [SIGENERGY2MQTT_MODBUS_HOST]
                        The hostname or IP address of the Sigenergy device
  --modbus-port [SIGENERGY2MQTT_MODBUS_PORT]
                        The Sigenergy device Modbus port number (default: 502)
  --modbus-slave [SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE ...]
                        ** DEPRECATED ** Use --modbus-inverter-device-id
                        instead.
  --modbus-inverter-device-id [SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID ...]
                        **The Sigenergy Inverter Modbus Device ID. Multiple
                        device IDS may be specified, separated by spaces.
  --modbus-accharger-slave [SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE ...]
                        ** DEPRECATED ** Use --modbus-accharger-device-id
                        instead.
  --modbus-accharger-device-id [SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID ...]
                        The Sigenergy AC Charger Modbus Device ID.
  --modbus-dccharger-slave [SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE ...]
                        ** DEPRECATED ** Use --modbus-dccharger-device-id
                        instead.
  --modbus-dccharger-device-id [SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID ...]
                        The Sigenergy DC Charger Modbus Device ID.
  --modbus-readonly     Only publish read-only sensors to MQTT. Neither read-
                        write or write-only sensors will be published if
                        specified.
  --modbus-no-remote-ems
                        Do not publish any read-write sensors for remote
                        Energy Management System (EMS) integration to MQTT.
                        Ignored if --modbus-read-only is specified.
  --modbus-timeout [SIGENERGY2MQTT_MODBUS_TIMEOUT]
                        The timeout for connecting and receiving Modbus data,
                        in seconds (use decimals for milliseconds). The
                        default is 1.0.
  --modbus-retries [SIGENERGY2MQTT_MODBUS_RETRIES]
                        The maximum number of times to retry a Modbus
                        operation if it fails. The default is 3.
  --modbus-disable-chunking
                        Disable Modbus chunking when reading registers and
                        read each register individually.
  --modbus-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the pymodbus log level. Valid values are: DEBUG,
                        INFO, WARNING, ERROR or CRITICAL. Default is WARNING
                        (warnings, errors and critical failures)
  --scan-interval-low [SIGENERGY2MQTT_SCAN_INTERVAL_LOW]
                        The scan interval in seconds for Modbus registers that
                        are to be scanned at a low frequency. Default is 600
                        (seconds), and the minimum value is 1.
  --scan-interval-medium [SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM]
                        The scan interval in seconds for Modbus registers that
                        are to be scanned at a medium frequency. Default is 60
                        (seconds), and the minimum value is 1.
  --scan-interval-high [SIGENERGY2MQTT_SCAN_INTERVAL_HIGH]
                        The scan interval in seconds for Modbus registers that
                        are to be scanned at a high frequency. Default is 10
                        (seconds), and the minimum value is 1.
  --scan-interval-realtime [SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME]
                        The scan interval in seconds for Modbus registers that
                        are to be scanned in near-real time. Default is 5
                        (seconds), and the minimum value is 1.
  --smartport-enabled   Enable interrogation of a third-party device for
                        production data.
  --smartport-module-name [SIGENERGY2MQTT_SMARTPORT_MODULE_NAME]
                        The name of the module which will be used to obtain
                        third-party device production data.
  --smartport-host [SIGENERGY2MQTT_SMARTPORT_HOST]
                        The IP address or hostname of the third-party device.
  --smartport-username [SIGENERGY2MQTT_SMARTPORT_USERNAME]
                        The username to authenticate to the third-party
                        device.
  --smartport-password [SIGENERGY2MQTT_SMARTPORT_PASSWORD]
                        The password to authenticate to the third-party
                        device.
  --smartport-pv-power [SIGENERGY2MQTT_SMARTPORT_PV_POWER]
                        The sensor class to hold the production data obtained
                        from the third-party device.
  --smartport-mqtt-topic [SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC]
                        The MQTT topic to which to subscribe to obtain the
                        production data for the third-party device.
  --smartport-mqtt-gain [SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN]
                        The gain to be applied to the production data for the
                        third-party device obtained from the MQTT topic. (e.g.
                        1000 if the data is in kW) Default is 1 (Watts).
  --pvoutput-enabled    Enable status updates to PVOutput.
  --pvoutput-api-key [SIGENERGY2MQTT_PVOUTPUT_API_KEY]
                        The API Key for PVOutput
  --pvoutput-system-id [SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID]
                        The PVOutput System ID
  --pvoutput-consumption [SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION]
                        Enable to send consumption data to PVOutput. May be
                        specified without a value (in which case defaults to
                        'consumption') or one of 'net-of-battery',
                        'consumption', or 'imported'. If not specified, no
                        consumption data is sent.
  --pvoutput-exports    Enable to send export data to PVOutput.
  --pvoutput-imports    Enable to send import data to PVOutput.
  --pvoutput-output-hour [SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR]
                        The hour of the day (20-23) at which the daily totals
                        are sent to PVOutput. The default is 23 (11pm). Valid
                        values are 20 to 23. The minute is randomly chosen
                        between 56 and 59. If you specify -1, daily uploads
                        will be sent at the same frequency as status updates.
  --pvoutput-interval [SIGENERGY2MQTT_PVOUTPUT_INTERVAL]
                        ** DEPRECATED ** The Status Interval is now determined
                        from the settings on pvoutput.org.
  --pvoutput-temp-topic [SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC]
                        An MQTT topic from which the current temperature can
                        be read. This is used to send the temperature to
                        PVOutput. If not specified, the temperature will not
                        be sent to PVOutput.
  --pvoutput-voltage [{phase-a,phase-b,phase-c,l/n-avg,l/l-avg}]
                        The source of the voltage value to be sent to
                        PVOutput. Valid values are: phase-a, phase-b, phase-c,
                        l/n-avg (line to neutral average), l/l-avg (line to
                        line average) or pv (average across PV strings). If
                        not specified, defaults to 'l/n-avg'.
  --pvoutput-ext-v7 [SIGENERGY2MQTT_PVOUTPUT_EXT_V7]
                        A sensor class name, or entity id without the
                        'sensor.' prefix, that will be used to populate the v7
                        extended field in PVOutput. If not specified, OR your
                        donation status is not current, this field will not be
                        sent to PVOutput. You can use any sensor with a
                        numeric value.
  --pvoutput-ext-v8 [SIGENERGY2MQTT_PVOUTPUT_EXT_V8]
                        A sensor class name, or entity id without the
                        'sensor.' prefix, that will be used to populate the v8
                        extended field in PVOutput. If not specified, OR your
                        donation status is not current, this field will not be
                        sent to PVOutput. You can use any sensor with a
                        numeric value.
  --pvoutput-ext-v9 [SIGENERGY2MQTT_PVOUTPUT_EXT_V9]
                        A sensor class name, or entity id without the
                        'sensor.' prefix, that will be used to populate the v9
                        extended field in PVOutput. If not specified, OR your
                        donation status is not current, this field will not be
                        sent to PVOutput. You can use any sensor with a
                        numeric value.
  --pvoutput-ext-v10 [SIGENERGY2MQTT_PVOUTPUT_EXT_V10]
                        A sensor class name, or entity id without the
                        'sensor.' prefix, that will be used to populate the
                        v10 extended field in PVOutput. If not specified, OR
                        your donation status is not current, this field will
                        not be sent to PVOutput. You can use any sensor with a
                        numeric value.
  --pvoutput-ext-v11 [SIGENERGY2MQTT_PVOUTPUT_EXT_V11]
                        A sensor class name, or entity id without the
                        'sensor.' prefix, that will be used to populate the
                        v11 extended field in PVOutput. If not specified, OR
                        your donation status is not current, this field will
                        not be sent to PVOutput. You can use any sensor with a
                        numeric value.
  --pvoutput-ext-v12 [SIGENERGY2MQTT_PVOUTPUT_EXT_V12]
                        A sensor class name, or entity id without the
                        'sensor.' prefix, that will be used to populate the
                        v12 extended field in PVOutput. If not specified, OR
                        your donation status is not current, this field will
                        not be sent to PVOutput. You can use any sensor with a
                        numeric value.
  --pvoutput-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the PVOutput log level. Valid values are: DEBUG,
                        INFO, WARNING, ERROR or CRITICAL. Default is WARNING
                        (warnings, errors and critical failures)
  --clean               Publish empty discovery to delete existing devices,
                        then exits immediately.
  -v, --version         Shows the version number, then exits immediately.

Command line options over-ride values in the configuration file and
environment variables.
