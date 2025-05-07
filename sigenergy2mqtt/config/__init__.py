__all__ = ["Config", "SmartPortConfig", "RegisterAccess"]


from .config import Config
from .device_config import RegisterAccess, SmartPortConfig
from pathlib import Path
import argparse
import logging
import os
import sys

if os.isatty(sys.stdout.fileno()):
    logging.basicConfig(format="%(asctime)s %(levelname)-5s sigenergy2mqtt:%(module)s:%(lineno)s %(message)s", level=logging.INFO)
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
    dest="config",
    default="/etc/sigenergy2mqtt.yaml",
    help="The path to the JSON configuration file (default: /etc/sigenergy2mqtt.yaml)",
)
_parser.add_argument(
    "-l",
    "--log-level",
    action="store",
    dest="log_level",
    type=int,
    choices=[
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ],
    help=f"Set the log level. Valid values are: {logging.DEBUG}=DEBUG {logging.INFO}=INFO {logging.WARNING}=WARNING {logging.ERROR}=ERROR {logging.CRITICAL}=CRITICAL. Default is {logging.WARNING} (warnings, errors and critical failures)",
)
_parser.add_argument(
    "-v",
    "--version",
    action="store_true",
    dest="show_version",
    help="Shows the version number, then exits immediately.",
)
_parser.add_argument(
    "--modbus-log-level",
    action="store",
    dest="modbus_log_level",
    type=int,
    choices=[
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ],
    help=f"Set the pymodbus log level. Valid values are: {logging.DEBUG}=DEBUG {logging.INFO}=INFO {logging.WARNING}=WARNING {logging.ERROR}=ERROR {logging.CRITICAL}=CRITICAL. Default is the setting of --log-level.",
)
_parser.add_argument(
    "--mqtt-log-level",
    action="store",
    dest="mqtt_log_level",
    type=int,
    choices=[
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ],
    help=f"Set the paho.mqtt log level. Valid values are: {logging.DEBUG}=DEBUG {logging.INFO}=INFO {logging.WARNING}=WARNING {logging.ERROR}=ERROR {logging.CRITICAL}=CRITICAL. Default is the setting of --log-level.",
)
_parser.add_argument(
    "--hass-discovery-only",
    action="store_true",
    dest="discovery_only",
    help="Exit immediately after publishing discovery. Does not read values from the ModBus interface, except to probe for device configuration.",
)
_parser.add_argument(
    "--clean",
    action="store_true",
    dest="clean",
    help="Publish empty discovery to delete existing devices, then exits immediately.",
)
_args = _parser.parse_args()
# endregion

if _args.show_version:
    sys.exit(0)

# region Load the configuration
if _args.config != "/etc/sigenergy2mqtt.yaml":
    if Path(_args.config).is_file():
        Config.load(_args.config)
    else:
        raise FileNotFoundError(f"Specified config file {_args.config} does not exist!")
elif Path("/etc/sigenergy2mqtt.yaml").is_file():
    Config.load("/etc/sigenergy2mqtt.yaml")
elif Path("./sigenergy2mqtt.yaml").is_file():
    Config.load("./sigenergy2mqtt.yaml")
else:
    raise FileNotFoundError("No config file specified and none found in default locations!")
# endregion

Config.clean = _args.clean
if _args.discovery_only or Config.clean:
    Config.home_assistant.discovery_only = True

# region Logging configuration
if _args.log_level is not None:
    Config.log_level = _args.log_level
if _args.modbus_log_level is not None:
    Config.set_modbus_log_level(_args.modbus_log_level)
if _args.mqtt_log_level is not None:
    Config.mqtt.log_level = _args.mqtt_log_level
# endregion Logging configuration


for _storage_base_path in ["/var/lib/", str(Path.home()), "/tmp/"]:
    if os.access(_storage_base_path, os.W_OK):
        path = Path(_storage_base_path, "sigenergy2mqtt")
        Config.persistent_state_path = path.resolve()
        if not path.is_dir():
            path.mkdir()
            logging.debug(f"Created persistent state path: {Config.persistent_state_path}")
        break
if Config.persistent_state_path == ".":
    _logger.warning("Unable to create persistent state path! Defaulting to current directory")

