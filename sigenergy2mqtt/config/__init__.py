__all__ = ["Config", "SmartPortConfig", "RegisterAccess", "SIGENERGY_MODBUS_PROTOCOL"]


from . import const
from .config import Config
from .device_config import RegisterAccess, SmartPortConfig
from .version import SIGENERGY_MODBUS_PROTOCOL
from pathlib import Path
import argparse
import logging
import os
import sys

if os.isatty(sys.stdout.fileno()):
    logging.basicConfig(format="%(asctime)s %(levelname)-5s sigenergy2mqtt:%(module)s:%(lineno)s %(message)s", level=logging.INFO)
else:
    cgroup = Path('/proc/self/cgroup')
    if Path('/.dockerenv').is_file() or (cgroup.is_file() and 'docker' in cgroup.read_text()):
        logging.basicConfig(format="%(asctime)s %(levelname)-5s %(module)s:%(lineno)s %(message)s", level=logging.INFO)
    else:
        logging.basicConfig(format="%(levelname)-5s %(module)s:%(lineno)s %(message)s", level=logging.INFO)
_logger = logging.getLogger("root")
_logger.info(f"Release {Config.origin['sw']}")

# region Arguments
_parser = argparse.ArgumentParser(
    description="Reads the Sigenergy modbus interface and publishes the data to MQTT. The data will be published to MQTT in the Home Assistant MQTT Discovery format.",
    epilog="Command line options over-ride values in the configuration file.",
)
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
    help="Exit immediately after publishing discovery. Does not read values from the ModBus interface, except to probe for device configuration.",
)
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
    help="The listening port of the MQTT broker (default: 1883)",
)
_parser.add_argument(
    "--mqtt-anonymous",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MQTT_ANONYMOUS,
    help="Connect to MQTT anonymously (i.e. without username/password).",
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
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE, None),
    help="The Sigenergy Inverter Modbus Device ID (Slave ID). May be specified multiple times.",
)
_parser.add_argument(
    "--modbus-accharger-slave",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE, None),
    help="The Sigenergy AC Charger Modbus Device ID (Slave ID).",
)
_parser.add_argument(
    "--modbus-dccharger-slave",
    nargs="*",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE, None),
    help="The Sigenergy DC Charger Modbus Device ID (Slave ID).",
)
_parser.add_argument(
    "--modbus-readonly",
    action="store_true",
    dest=const.SIGENERGY2MQTT_MODBUS_READ_ONLY,
    help="Only publish read-only sensors to MQTT. Neither read-write or write-only sensors will be published if specified.",
)
_parser.add_argument(
    "--modbus-log-level",
    action="store",
    dest=const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL,
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default=os.getenv(const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL, None),
    help="Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)",
)
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
    action="store_true",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION,
    help="Enable sending consumption status to PVOutput.",
)
_parser.add_argument(
    "--pvoutput-interval",
    nargs="?",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_INTERVAL,
    type=int,
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_INTERVAL, None),
    help="The interval in minutes to send data to PVOutput (default: 5). Valid values are 5, 10 or 15 minutes.",
)
_parser.add_argument(
    "--pvoutput-log-level",
    action="store",
    dest=const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL,
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default=os.getenv(const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL, None),
    help="Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)",
)
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
        os.environ[variable] = str(value)
        _logger.debug(f"Environment variable '{variable}' overridden from command line: set to '{value}' (was '{was}')")
    else:
        if was is not None:
            os.environ[variable] = ""
            _logger.debug(f"Environment variable '{variable}' overridden from command line: cleared (was '{was}')")
        else:
            _logger.debug(f"Environment variable '{variable}' not set")

if _args.SIGENERGY2MQTT_LOG_LEVEL:
    _logger.setLevel(getattr(logging, _args.SIGENERGY2MQTT_LOG_LEVEL))

for arg in vars(_args):
    if arg == "clean":
        Config.clean = _args.clean
        continue
    elif (
        arg == const.SIGENERGY2MQTT_HASS_ENABLED or arg == const.SIGENERGY2MQTT_HASS_DISCOVERY_ONLY or arg == const.SIGENERGY2MQTT_MQTT_ANONYMOUS or arg == const.SIGENERGY2MQTT_PVOUTPUT_ENABLED or arg == const.SIGENERGY2MQTT_SMARTPORT_ENABLED
    ) and getattr(_args, arg) not in ["true", "True", True, 1]:
        continue
    elif arg == const.SIGENERGY2MQTT_MODBUS_READ_ONLY and getattr(_args, arg) in ["true", "True", True, 1]:
        apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_ONLY, "true")
        apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_WRITE, "false")
        apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY, "false")
        continue
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

for _storage_base_path in ["/data/", "/var/lib/", str(Path.home()), "/tmp/"]:
    if os.path.isdir(_storage_base_path) and os.access(_storage_base_path, os.W_OK):
        path = Path(_storage_base_path, "sigenergy2mqtt")
        Config.persistent_state_path = path.resolve()
        if not path.is_dir():
            path.mkdir()
        logging.debug(f"{Config.persistent_state_path=}")
        break
    else:
        logging.debug(f"Unable to create persistent state path in {_storage_base_path}: Not writable or does not exist")
if Config.persistent_state_path == ".":
    _logger.critical("Unable to create persistent state path!")
    sys.exit(1)
