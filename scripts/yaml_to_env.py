#!/usr/bin/env python3
import datetime
import json
import sys
from pathlib import Path

from ruamel.yaml import YAML

# Add project root to path to import constants
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

try:
    from sigenergy2mqtt.config import const
except ImportError:
    print("Error: Could not import sigenergy2mqtt.config.const. Run this script from the project root.", file=sys.stderr)
    sys.exit(1)


def json_serial(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def yaml_to_env(yaml_data):
    env_vars = {}

    # Helper to set if value exists
    def set_env(key, value):
        if value is not None:
            if isinstance(value, bool):
                env_vars[key] = "true" if value else "false"
            elif isinstance(value, (list, dict)):
                if key == const.SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON or key == const.SIGENERGY2MQTT_SENSOR_OVERRIDES_JSON:
                    env_vars[key] = json.dumps(value, default=json_serial)
                elif all(isinstance(x, (int, float, str, bool)) for x in value if x is not None):
                    env_vars[key] = ",".join(map(str, value))
                else:
                    # Fallback for complex structures if any
                    env_vars[key] = json.dumps(value, default=json_serial)
            else:
                env_vars[key] = str(value)

    # Top level
    set_env(const.SIGENERGY2MQTT_LOG_LEVEL, yaml_data.get("log-level"))
    set_env(const.SIGENERGY2MQTT_LANGUAGE, yaml_data.get("language"))
    set_env(const.SIGENERGY2MQTT_CONSUMPTION, yaml_data.get("consumption"))
    set_env(const.SIGENERGY2MQTT_REPEATED_STATE_PUBLISH_INTERVAL, yaml_data.get("repeated-state-publish-interval"))
    set_env(const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW, yaml_data.get("sanity-check-default-kw"))
    set_env(const.SIGENERGY2MQTT_SANITY_CHECK_FAILURES_INCREMENT, yaml_data.get("sanity-check-failures-increment"))

    # no-ems-mode-check is inverted in env
    if "ems-mode-check" in yaml_data:
        set_env(const.SIGENERGY2MQTT_NO_EMS_MODE_CHECK, not yaml_data["ems-mode-check"])

    # no-metrics is inverted
    if "metrics-enabled" in yaml_data:
        set_env(const.SIGENERGY2MQTT_NO_METRICS, not yaml_data["metrics-enabled"])

    debug_val = yaml_data.get("sensor-debug-logging")
    if debug_val is not None:
        if isinstance(debug_val, bool):
            if debug_val:
                set_env(const.SIGENERGY2MQTT_DEBUG_SENSOR, "true")
        else:
            set_env(const.SIGENERGY2MQTT_DEBUG_SENSOR, debug_val)

    # Sensor overrides
    set_env(const.SIGENERGY2MQTT_SENSOR_OVERRIDES_JSON, yaml_data.get("sensor-overrides"))

    # Home Assistant
    hass = yaml_data.get("home-assistant", {})
    if hass:
        set_env(const.SIGENERGY2MQTT_HASS_ENABLED, hass.get("enabled"))
        set_env(const.SIGENERGY2MQTT_HASS_SENSORS_ENABLED_BY_DEFAULT, hass.get("sensors-enabled-by-default"))
        set_env(const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX, hass.get("device-name-prefix"))
        set_env(const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX, hass.get("discovery-prefix"))
        set_env(const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX, hass.get("entity-id-prefix"))
        set_env(const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX, hass.get("unique-id-prefix"))
        set_env(const.SIGENERGY2MQTT_HASS_SIGENERGY_LOCAL_MODBUS_NAMING, hass.get("sigenergy-local-modbus-naming"))
        set_env(const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS, hass.get("use-simplified-topics"))
        set_env(const.SIGENERGY2MQTT_HASS_EDIT_PCT_BOX, hass.get("edit-pct-box"))

    # MQTT
    mqtt = yaml_data.get("mqtt", {})
    if mqtt:
        set_env(const.SIGENERGY2MQTT_MQTT_BROKER, mqtt.get("broker"))
        set_env(const.SIGENERGY2MQTT_MQTT_PORT, mqtt.get("port"))
        set_env(const.SIGENERGY2MQTT_MQTT_KEEPALIVE, mqtt.get("keepalive"))
        set_env(const.SIGENERGY2MQTT_MQTT_TLS, mqtt.get("tls"))
        set_env(const.SIGENERGY2MQTT_MQTT_TLS_INSECURE, mqtt.get("tls-insecure"))
        set_env(const.SIGENERGY2MQTT_MQTT_TRANSPORT, mqtt.get("transport"))
        set_env(const.SIGENERGY2MQTT_MQTT_ANONYMOUS, mqtt.get("anonymous"))
        set_env(const.SIGENERGY2MQTT_MQTT_USERNAME, mqtt.get("username"))
        set_env(const.SIGENERGY2MQTT_MQTT_PASSWORD, mqtt.get("password"))
        set_env(const.SIGENERGY2MQTT_MQTT_LOG_LEVEL, mqtt.get("log-level"))

    # Modbus (Taking the first one)
    modbus_list = yaml_data.get("modbus", [])
    if modbus_list and isinstance(modbus_list, list):
        m = modbus_list[0]
        set_env(const.SIGENERGY2MQTT_MODBUS_HOST, m.get("host"))
        set_env(const.SIGENERGY2MQTT_MODBUS_PORT, m.get("port"))
        set_env(const.SIGENERGY2MQTT_MODBUS_TIMEOUT, m.get("timeout"))
        set_env(const.SIGENERGY2MQTT_MODBUS_RETRIES, m.get("retries"))
        set_env(const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING, m.get("disable-chunking"))
        set_env(const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL, m.get("log-level"))
        set_env(const.SIGENERGY2MQTT_MODBUS_READ_ONLY, m.get("read-only"))
        set_env(const.SIGENERGY2MQTT_MODBUS_READ_WRITE, m.get("read-write"))
        set_env(const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY, m.get("write-only"))
        set_env(const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS, m.get("no-remote-ems"))
        set_env(const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID, m.get("inverters"))
        set_env(const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID, m.get("ac-chargers"))
        set_env(const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID, m.get("dc-chargers"))
        set_env(const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW, m.get("scan-interval-low"))
        set_env(const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM, m.get("scan-interval-medium"))
        set_env(const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH, m.get("scan-interval-high"))
        set_env(const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME, m.get("scan-interval-realtime"))

        # Smart-port
        sp = m.get("smart-port", {})
        if sp:
            set_env(const.SIGENERGY2MQTT_SMARTPORT_ENABLED, sp.get("enabled"))
            mod = sp.get("module", {})
            if mod:
                set_env(const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME, mod.get("name"))
                set_env(const.SIGENERGY2MQTT_SMARTPORT_HOST, mod.get("host"))
                set_env(const.SIGENERGY2MQTT_SMARTPORT_USERNAME, mod.get("username"))
                set_env(const.SIGENERGY2MQTT_SMARTPORT_PASSWORD, mod.get("password"))
                set_env(const.SIGENERGY2MQTT_SMARTPORT_PV_POWER, mod.get("pv-power"))

            sp_mqtt_list = sp.get("mqtt", [])
            if sp_mqtt_list and isinstance(sp_mqtt_list, list):
                sm = sp_mqtt_list[0]
                set_env(const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC, sm.get("topic"))
                set_env(const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN, sm.get("gain"))

    # PVOutput
    pvo = yaml_data.get("pvoutput", {})
    if pvo:
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_ENABLED, pvo.get("enabled"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_API_KEY, pvo.get("api-key"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID, pvo.get("system-id"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION, pvo.get("consumption"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS, pvo.get("exports"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS, pvo.get("imports"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR, pvo.get("output-hour"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC, pvo.get("temperature-topic"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_VOLTAGE, pvo.get("voltage"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7, pvo.get("v7"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8, pvo.get("v8"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9, pvo.get("v9"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10, pvo.get("v10"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11, pvo.get("v11"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12, pvo.get("v12"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL, pvo.get("log-level"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING, pvo.get("calc-debug-logging"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING, pvo.get("update-debug-logging"))
        set_env(const.SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON, pvo.get("time-periods"))

    # InfluxDB
    influx = yaml_data.get("influxdb", {})
    if influx:
        set_env(const.SIGENERGY2MQTT_INFLUX_ENABLED, influx.get("enabled"))
        set_env(const.SIGENERGY2MQTT_INFLUX_HOST, influx.get("host"))
        set_env(const.SIGENERGY2MQTT_INFLUX_PORT, influx.get("port"))
        set_env(const.SIGENERGY2MQTT_INFLUX_USERNAME, influx.get("username"))
        set_env(const.SIGENERGY2MQTT_INFLUX_PASSWORD, influx.get("password"))
        set_env(const.SIGENERGY2MQTT_INFLUX_DATABASE, influx.get("database"))
        set_env(const.SIGENERGY2MQTT_INFLUX_ORG, influx.get("org"))
        set_env(const.SIGENERGY2MQTT_INFLUX_TOKEN, influx.get("token"))
        set_env(const.SIGENERGY2MQTT_INFLUX_BUCKET, influx.get("bucket"))
        set_env(const.SIGENERGY2MQTT_INFLUX_DEFAULT_MEASUREMENT, influx.get("default-measurement"))
        set_env(const.SIGENERGY2MQTT_INFLUX_LOAD_HASS_HISTORY, influx.get("load-hass-history"))
        set_env(const.SIGENERGY2MQTT_INFLUX_INCLUDE, influx.get("include"))
        set_env(const.SIGENERGY2MQTT_INFLUX_EXCLUDE, influx.get("exclude"))
        set_env(const.SIGENERGY2MQTT_INFLUX_LOG_LEVEL, influx.get("log-level"))
        set_env(const.SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT, influx.get("write-timeout"))
        set_env(const.SIGENERGY2MQTT_INFLUX_READ_TIMEOUT, influx.get("read-timeout"))
        set_env(const.SIGENERGY2MQTT_INFLUX_BATCH_SIZE, influx.get("batch-size"))
        set_env(const.SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL, influx.get("flush-interval"))
        set_env(const.SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL, influx.get("query-interval"))
        set_env(const.SIGENERGY2MQTT_INFLUX_MAX_RETRIES, influx.get("max-retries"))
        set_env(const.SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS, influx.get("pool-connections"))
        set_env(const.SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE, influx.get("pool-maxsize"))
        set_env(const.SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE, influx.get("sync-chunk-size"))
        set_env(const.SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS, influx.get("max-sync-workers"))

    return env_vars


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <yaml_file>")
        sys.exit(1)

    yaml_file = Path(sys.argv[1])
    if not yaml_file.exists():
        print(f"Error: File {yaml_file} not found.", file=sys.stderr)
        sys.exit(1)

    yaml = YAML(typ="safe")
    with open(yaml_file, "r") as f:
        data = yaml.load(f)

    if not data:
        print("Error: Empty or invalid YAML.", file=sys.stderr)
        sys.exit(1)

    env_vars = yaml_to_env(data)

    # Export format for shell sourcing
    for k, v in env_vars.items():
        # Escape single quotes for shell
        escaped_v = v.replace("'", "'\\''")
        print(f"export {k}='{escaped_v}'")


if __name__ == "__main__":
    main()
