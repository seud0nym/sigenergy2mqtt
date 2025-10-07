__all__ = ["Config", "SmartPortConfig", "RegisterAccess", "SIGENERGY_MODBUS_PROTOCOL", "SIGENERGY_MODBUS_PROTOCOL_PUBLISHED", "CONSUMPTION", "IMPORTED", "OutputField", "StatusField"]


from . import const
from .config import Config
from .modbus_config import RegisterAccess, SmartPortConfig
from .pvoutput_config import CONSUMPTION, IMPORTED, OutputField, StatusField
from .version import SIGENERGY_MODBUS_PROTOCOL, SIGENERGY_MODBUS_PROTOCOL_PUBLISHED
from pathlib import Path
import argparse
import logging
import os
import sys
import time

if os.isatty(sys.stdout.fileno()):
    logging.basicConfig(format="%(asctime)s %(levelname)-5s sigenergy2mqtt:%(module)s:%(lineno)s %(message)s", level=logging.INFO)
else:
    cgroup = Path("/proc/self/cgroup")
    if Path("/.dockerenv").is_file() or (cgroup.is_file() and "docker" in cgroup.read_text()):
        logging.basicConfig(format="%(asctime)s %(levelname)-5s %(module)s:%(lineno)s %(message)s", level=logging.INFO)
    else:
        logging.basicConfig(format="%(levelname)-5s %(module)s:%(lineno)s %(message)s", level=logging.INFO)
_logger = logging.getLogger("root")
_logger.info(f"Release {Config.origin['sw']}")

for _storage_base_path in ["/data/", "/var/lib/", str(Path.home()), "/tmp/"]:
    if os.path.isdir(_storage_base_path) and os.access(_storage_base_path, os.W_OK):
        path = Path(_storage_base_path, "sigenergy2mqtt")
        Config.persistent_state_path = path.resolve()
        if not path.is_dir():
            _logger.info(f"Persistent state folder '{Config.persistent_state_path}' created")
            path.mkdir()
        else:
            _logger.info(f"Persistent state folder '{Config.persistent_state_path}' already exists")
        break
if Config.persistent_state_path == ".":
    _logger.critical("Unable to create persistent state folder!")
    sys.exit(1)
persistent_state_path = Path(Config.persistent_state_path)
threshold_time = time.time() - (7 * 86400)
for file in persistent_state_path.iterdir():
    if file.is_file() and not file.name.endswith(".yaml") and not file.name.endswith(".publishable") and not file.name.endswith(".token") and file.stat().st_mtime < threshold_time:
        _logger.info(f"Removing stale state file: {file} (last modified: {time.ctime(file.stat().st_mtime)})")
        file.unlink()

# region Arguments
_parser = argparse.ArgumentParser(
    description="Reads the Sigenergy modbus interface and publishes the data to MQTT. The data will be published to MQTT in the Home Assistant MQTT Discovery format.",
    epilog="Command line options over-ride values in the configuration file and environment variables.",
)
# region General Configuration
_parser.add_argument(
    "-c",
    "--config",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_CONFIG,
    default=os.getenv(const.SIGENERGY2MQTT_CONFIG, None),
    help="The path to the JSON configuration file (default: /etc/sigenergy2mqtt.yaml)",
)
_parser.add_argument(
    "-l",
    "--log-level",
    action="store",
    dest=const.SIGENERGY2MQTT_LOG_LEVEL,
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default=os.getenv(const.SIGENERGY2MQTT_LOG_LEVEL, None),
    help="Set the log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)",
)
_parser.add_argument(
    "-d",
    "--debug-sensor",
    action="store",
    dest=const.SIGENERGY2MQTT_DEBUG_SENSOR,
    default=os.getenv(const.SIGENERGY2MQTT_DEBUG_SENSOR, None),
    help="Specify a sensor to be debugged using either the full entity id, a partial entity id, the full sensor class name, or a partial sensor class name. For example, specifying 'daily' would match all sensors with daily in their entity name. If specified, --debug-level is also forced to DEBUG",
)
_parser.add_argument(
    "--sanity-check-default-kw",
    action="store",
    dest=const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW,
    type=float,
    default=os.getenv(const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW, None),
    help="The default value in kW used for sanity checks to validate the maximum and minimum values for actual value of power sensors and the delta value of energy sensors. The default value is 100 kW per second, and readings outside the range are ignored.",
)
_parser.add_argument(
    "--no-metrics",
    action="store_true",
    dest=const.SIGENERGY2MQTT_NO_METRICS,
    help="Do not publish any sigenergy2mqtt metrics.",
)
# endregion
# region Home Assistant Configuration
_parser.add_argument(
    "--hass-enabled",
    action="store_true",
    dest=const.SIGENERGY2MQTT_HASS_ENABLED,
    help="Enable auto-discovery in Home Assistant.",
)
_parser.add_argument(
    "--hass-discovery-prefix",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX,
    default=os.getenv(const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX, None),
    help="The Home Assistant MQTT Discovery topic prefix to use (default: homeassistant)",
)
_parser.add_argument(
    "--hass-entity-id-prefix",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX,
    default=os.getenv(const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX, None),
    help="The prefix to use for Home Assistant entity IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to entity IDs (default: sigen)",
)
_parser.add_argument(
    "--hass-unique-id-prefix",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX,
    default=os.getenv(const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX, None),
    help="The prefix to use for Home Assistant unique IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to unique IDs (default: sigen). Once you have set this, you should NEVER change it, as it will break existing entities in Home Assistant.",
)
_parser.add_argument(
    "--hass-use-simplified-topics",
    action="store_true",
    dest=const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS,
    help="Enable the simplified topic structure (sigenergy2mqtt/object_id/state) instead of the full Home Assistant topic structure (homeassistant/platform/device_id/object_id/state)",
)
_parser.add_argument(
    "--hass-device-name-prefix",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX,
    default=os.getenv(const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX, None),
    help="The prefix to use for Home Assistant entity names. Example: A prefix of 'prefix' will prepend 'prefix ' to names (default: '')",
)
_parser.add_argument(
    "--hass-discovery-only",
    action="store_true",
    dest=const.SIGENERGY2MQTT_HASS_DISCOVERY_ONLY,
    help="Exit immediately after publishing discovery. Does not read values from the Modbus interface, except to probe for device configuration.",
)
# endregion
# region MQTT Configuration
_parser.add_argument(
    "-b",
    "--mqtt-broker",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_MQTT_BROKER,
    default=os.getenv(const.SIGENERGY2MQTT_MQTT_BROKER, None),
    help="The hostname or IP address of an MQTT broker (default: 127.0.0.1)",
)
_parser.add_argument(
    "--mqtt-port",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_MQTT_PORT,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_MQTT_PORT, None),
    help="The listening port of the MQTT broker (default is 1883, unless --mqtt-tls is specified, in which case the default is 8883)",
)
_parser.add_argument(
    "--mqtt-tls",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MQTT_TLS,
    help="Enable secure communication to MQTT broker over TLS/SSL. If specified, the default MQTT port is 8883.",
)
_parser.add_argument(
    "--mqtt-tls-insecure",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MQTT_TLS_INSECURE,
    help="Enables insecure communication over TLS. If your broker is using a self-signed certificate, you must specify this option. Ignored unless --mqtt-tls is also specified.",
)
_parser.add_argument(
    "--mqtt-anonymous",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MQTT_ANONYMOUS,
    help="Allow anonymous connection to MQTT broker (i.e. without username/password). If specified, the --mqtt-username and --mqtt-password options are ignored.",
)
_parser.add_argument(
    "-u",
    "--mqtt-username",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_MQTT_USERNAME,
    default=os.getenv(const.SIGENERGY2MQTT_MQTT_USERNAME, None),
    help="A valid username for the MQTT broker",
)
_parser.add_argument(
    "-p",
    "--mqtt-password",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_MQTT_PASSWORD,
    default=os.getenv(const.SIGENERGY2MQTT_MQTT_PASSWORD, None),
    help="A valid password for the MQTT broker username",
)
_parser.add_argument(
    "--mqtt-log-level",
    action="store",
    dest=const.SIGENERGY2MQTT_MQTT_LOG_LEVEL,
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default=os.getenv(const.SIGENERGY2MQTT_MQTT_LOG_LEVEL, None),
    help="Set the paho.mqtt log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)",
)
# endregion
# region Modbus Configuration
_parser.add_argument(
    "--modbus-auto-discovery",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY,
    choices=["once", "force"],
    help="Attempt to auto-discover Sigenergy Modbus hosts and device IDs. If 'once' is specified, auto-discovery will only occur if no existing auto-discovery results are found. If 'force', auto-discovery will overwrite any previously discovered Modbus hosts and device IDs. If not specified, auto-discovery is disabled.",
)
_parser.add_argument(
    "-m",
    "--modbus-host",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_HOST,
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_HOST, None),
    help="The hostname or IP address of the Sigenergy device",
)
_parser.add_argument(
    "--modbus-port",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_PORT,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_PORT, None),
    help="The Sigenergy device Modbus port number (default: 502)",
)
_parser.add_argument(
    "--modbus-slave",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE,
    type=int,
    help="** DEPRECATED ** Use --modbus-inverter-device-id instead.",
)
_parser.add_argument(
    "--modbus-inverter-device-id",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID, None),
    help="**The Sigenergy Inverter Modbus Device ID. Multiple device IDS may be specified, separated by spaces.",
)
_parser.add_argument(
    "--modbus-accharger-slave",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE,
    type=int,
    help="** DEPRECATED ** Use --modbus-accharger-device-id instead.",
)
_parser.add_argument(
    "--modbus-accharger-device-id",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID, None),
    help="The Sigenergy AC Charger Modbus Device ID.",
)
_parser.add_argument(
    "--modbus-dccharger-slave",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE,
    type=int,
    help="** DEPRECATED ** Use --modbus-dccharger-device-id instead.",
)
_parser.add_argument(
    "--modbus-dccharger-device-id",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID, None),
    help="The Sigenergy DC Charger Modbus Device ID.",
)
_parser.add_argument(
    "--modbus-readonly",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MODBUS_READ_ONLY,
    help="Only publish read-only sensors to MQTT. Neither read-write or write-only sensors will be published if specified.",
)
_parser.add_argument(
    "--modbus-no-remote-ems",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS,
    help="Do not publish any read-write sensors for remote Energy Management System (EMS) integration to MQTT. Ignored if --modbus-read-only is specified.",
)
_parser.add_argument(
    "--modbus-disable-chunking",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING,
    help="Disable Modbus chunking when reading registers and read each register individually.",
)
_parser.add_argument(
    "--modbus-log-level",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL,
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL, None),
    help="Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)",
)
# endregion
# region Scan Interval Configuration
_parser.add_argument(
    "--scan-interval-low",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW, None),
    help="The scan interval in seconds for Modbus registers that are to be scanned at a low frequency. Default is 600 (seconds), and the minimum value is 300.",
)
_parser.add_argument(
    "--scan-interval-medium",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM, None),
    help="The scan interval in seconds for Modbus registers that are to be scanned at a medium frequency. Default is 60 (seconds), and the minimum value is 30.",
)
_parser.add_argument(
    "--scan-interval-high",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH, None),
    help="The scan interval in seconds for Modbus registers that are to be scanned at a high frequency. Default is 10 (seconds), and the minimum value is 5.",
)
_parser.add_argument(
    "--scan-interval-realtime",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME, None),
    help="The scan interval in seconds for Modbus registers that are to be scanned in near-real time. Default is 5 (seconds), and the minimum value is 1.",
)
# endregion
# region SmartPort Configuration
_parser.add_argument(
    "--smartport-enabled",
    action="store_true",
    dest=const.SIGENERGY2MQTT_SMARTPORT_ENABLED,
    help="Enable interrogation of a third-party device for production data.",
)
_parser.add_argument(
    "--smartport-module-name",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME,
    default=os.getenv(const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME, None),
    help="The name of the module which will be used to obtain third-party device production data.",
)
_parser.add_argument(
    "--smartport-host",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SMARTPORT_HOST,
    default=os.getenv(const.SIGENERGY2MQTT_SMARTPORT_HOST, None),
    help="The IP address or hostname of the third-party device.",
)
_parser.add_argument(
    "--smartport-username",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SMARTPORT_USERNAME,
    default=os.getenv(const.SIGENERGY2MQTT_SMARTPORT_USERNAME, None),
    help="The username to authenticate to the third-party device.",
)
_parser.add_argument(
    "--smartport-password",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SMARTPORT_PASSWORD,
    default=os.getenv(const.SIGENERGY2MQTT_SMARTPORT_PASSWORD, None),
    help="The password to authenticate to the third-party device.",
)
_parser.add_argument(
    "--smartport-pv-power",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SMARTPORT_PV_POWER,
    default=os.getenv(const.SIGENERGY2MQTT_SMARTPORT_PV_POWER, None),
    help="The sensor class to hold the production data obtained from the third-party device.",
)
_parser.add_argument(
    "--smartport-mqtt-topic",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC,
    default=os.getenv(const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC, None),
    help="The MQTT topic to which to subscribe to obtain the production data for the third-party device.",
)
_parser.add_argument(
    "--smartport-mqtt-gain",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN, None),
    help="The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. 1000 if the data is in kW) Default is 1 (Watts).",
)
# endregion
# region PVOutput Configuration
_parser.add_argument(
    "--pvoutput-enabled",
    action="store_true",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_ENABLED,
    help="Enable status updates to PVOutput.",
)
_parser.add_argument(
    "--pvoutput-api-key",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_API_KEY,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_API_KEY, None),
    help="The API Key for PVOutput",
)
_parser.add_argument(
    "--pvoutput-system-id",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID, None),
    help="The PVOutput System ID",
)
_parser.add_argument(
    "--pvoutput-consumption",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION,
    const="true",
    help="Enable to send consumption data to PVOutput. If specified without a value, or with a value of 'true' or 'consumption', consumption data will be sent. With a value of 'imported', the energy imported from the grid will be sent as consumption. If not specified, no consumption data is sent.",
)
_parser.add_argument(
    "--pvoutput-exports",
    action="store_true",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS,
    help="Enable to send export data to PVOutput.",
)
_parser.add_argument(
    "--pvoutput-imports",
    action="store_true",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS,
    help="Enable to send import data to PVOutput.",
)
_parser.add_argument(
    "--pvoutput-output-hour",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR, None),
    help="The hour of the day (20-23) at which the daily totals are sent to PVOutput. The default is 23 (11pm). Valid values are 20 to 23. The minute is randomly chosen between 51 and 58. If you specify -1, daily uploads will be sent at the same frequency as status updates.",
)
_parser.add_argument(
    "--pvoutput-interval",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_INTERVAL,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_INTERVAL, None),
    help="** DEPRECATED ** The Status Interval is now determined from the settings on pvoutput.org.",
)
_parser.add_argument(
    "--pvoutput-temp-topic",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC, None),
    help="An MQTT topic from which the current temperature can be read. This is used to send the temperature to PVOutput. If not specified, the temperature will not be sent to PVOutput.",
)
_parser.add_argument(
    "--pvoutput-ext-v7",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7, None),
    help="A sensor class name that will be used to populate the v7 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value.",
)
_parser.add_argument(
    "--pvoutput-ext-v8",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8, None),
    help="A sensor class name that will be used to populate the v8 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value.",
)
_parser.add_argument(
    "--pvoutput-ext-v9",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9, None),
    help="A sensor class name that will be used to populate the v9 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value.",
)
_parser.add_argument(
    "--pvoutput-ext-v10",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10, None),
    help="A sensor class name that will be used to populate the v10 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value.",
)
_parser.add_argument(
    "--pvoutput-ext-v11",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11, None),
    help="A sensor class name that will be used to populate the v11 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value.",
)
_parser.add_argument(
    "--pvoutput-ext-v12",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12, None),
    help="A sensor class name that will be used to populate the v12 extended field in PVOutput. If not specified, OR your donation status is not current, this field will not be sent to PVOutput. You can use any sensor with a numeric value.",
)
_parser.add_argument(
    "--pvoutput-log-level",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL,
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL, None),
    help="Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)",
)
# endregion
_parser.add_argument(
    "--clean",
    action="store_true",
    dest="clean",
    help="Publish empty discovery to delete existing devices, then exits immediately.",
)
_parser.add_argument(
    "-v",
    "--version",
    action="store_true",
    dest="show_version",
    help="Shows the version number, then exits immediately.",
)
_args = _parser.parse_args()
# endregion

if _args.show_version:
    sys.exit(0)


def apply_cli_to_env(variable: str, value: str) -> None:
    was = os.getenv(variable)
    if value is not None:
        if value != was:
            os.environ[variable] = str(value)
            if was is not None:
                _logger.debug(f"Environment variable '{variable}' overridden from command line: set to '{'[REDACTED]' if 'PASSWORD' in variable or 'API_KEY' in variable else value}' (was '{was}')")
    else:
        if was is not None:
            os.environ[variable] = ""
            _logger.debug(f"Environment variable '{variable}' overridden from command line: cleared (was '{was}')")
        else:
            _logger.debug(f"Environment variable '{variable}' not set")


if _args.SIGENERGY2MQTT_LOG_LEVEL:
    Config.log_level = getattr(logging, _args.SIGENERGY2MQTT_LOG_LEVEL)
    _logger.setLevel(getattr(logging, _args.SIGENERGY2MQTT_LOG_LEVEL))
    _logger.log(_logger.level, f"sigenergy2mqtt log-level changed to {logging.getLevelName(Config.log_level)}")

for key in os.environ.keys():
    if key.startswith("SIGENERGY2MQTT_"):
        if key.endswith("_SLAVE"):
            _logger.warning(f"The environment variable '{key}' is deprecated and will be removed in a future version. Use '{key.replace('_SLAVE', '_DEVICE_ID')}' instead.")
        elif key == const.SIGENERGY2MQTT_PVOUTPUT_INTERVAL:
            _logger.warning(f"The environment variable '{key}' is deprecated and will be removed in a future version. The Status Interval is now determined from the settings on pvoutput.org.")

for arg in vars(_args):
    if arg == "clean":
        Config.clean = _args.clean
        continue
    elif (
        arg == const.SIGENERGY2MQTT_HASS_ENABLED
        or arg == const.SIGENERGY2MQTT_HASS_DISCOVERY_ONLY
        or arg == const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS
        or arg == const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS
        or arg == const.SIGENERGY2MQTT_MQTT_ANONYMOUS
        or arg == const.SIGENERGY2MQTT_MQTT_TLS
        or arg == const.SIGENERGY2MQTT_MQTT_TLS_INSECURE
        or arg == const.SIGENERGY2MQTT_PVOUTPUT_ENABLED
        or arg == const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS
        or arg == const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS
        or arg == const.SIGENERGY2MQTT_SMARTPORT_ENABLED
        or arg == const.SIGENERGY2MQTT_NO_METRICS
        or arg == const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING
    ) and getattr(_args, arg) not in ["true", "True", True, 1]:  # argparse will store false by default, so ignore unless actually specified (and therefore true)
        continue
    elif arg == const.SIGENERGY2MQTT_MODBUS_READ_ONLY and getattr(_args, arg) in ["true", "True", True, 1]:
        apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_ONLY, "true")
        apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_WRITE, "false")
        apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY, "false")
        continue
    elif arg == const.SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE and getattr(_args, arg) is not None:
        _logger.warning("** DEPRECATED ** The '--modbus-inverter-slave' option is deprecated and will be removed in a future version. Use '--modbus-inverter-device-id' instead.")
    elif arg == const.SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE and getattr(_args, arg) is not None:
        _logger.warning("** DEPRECATED ** The '--modbus-accharger-slave' option is deprecated and will be removed in a future version. Use '--modbus-accharger-device-id' instead.")
    elif arg == const.SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE and getattr(_args, arg) is not None:
        _logger.warning("** DEPRECATED ** The '--modbus-dccharger-slave' option is deprecated and will be removed in a future version. Use '--modbus-dccharger-device-id' instead.")
    override = getattr(_args, arg)
    if override:
        if isinstance(override, list):
            apply_cli_to_env(arg, ",".join([str(x) for x in override]))
        else:
            apply_cli_to_env(arg, override)

try:
    if _args.SIGENERGY2MQTT_CONFIG:
        filename = str(_args.SIGENERGY2MQTT_CONFIG).strip()
        if Path(filename).is_file():
            Config.load(filename)
        else:
            raise FileNotFoundError(f"Specified config file '{filename}' does not exist!")
    elif Path("/etc/sigenergy2mqtt.yaml").is_file():
        Config.load("/etc/sigenergy2mqtt.yaml")
    elif Path("/data/sigenergy2mqtt.yaml").is_file():
        Config.load("/data/sigenergy2mqtt.yaml")
    else:
        Config.reload()
except Exception as e:
    _logger.critical(f"Error processing configuration: {e}")
    sys.exit(1)
