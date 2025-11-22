from pathlib import Path
from datetime import datetime, timedelta, timezone
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
import asyncio
import logging
import requests
import sys
import os

if not os.getcwd().endswith("resources"):
    os.chdir("resources")


os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.sensors.base import Sensor, WriteOnlySensor
from test import get_sensor_instances, cancel_sensor_futures

TOPICS: Path = Path("sensors/TOPICS.md")
SENSORS: Path = Path("sensors/SENSORS.md")


async def sensor_index():
    def metrics_topics(index_only: bool = False):
        if not index_only:
            f.write("| Metric | Interval | Unit | State Topic|\n")
            f.write("|--------|---------:|------|-------------|\n")
        metrics = MetricsService._discovery["cmps"]
        for metric in sorted(metrics.values(), key=lambda x: x["name"]):
            if index_only:
                f.write(f"<li><a href='#{metric['unique_id']}'>{metric['name']}</a></li>\n")
            else:
                f.write(f"| {metric['name']} | 1 | {metric['unit_of_measurement'] if 'unit_of_measurement' in metric else ''} | {metric['state_topic']} |\n")

    def published_topics(device: str, index_only: bool = False):
        for key in [key for key, value in sorted(mqtt_sensors.items(), key=lambda x: x[1]["name"]) if "state_topic" in value and not isinstance(value, WriteOnlySensor)]:
            sensor: Sensor = mqtt_sensors[key]
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device and sensor.publishable:
                if index_only:
                    f.write(f"<a href='#{sensor.unique_id}' style='font-size:small;'>")
                    if hasattr(sensor, "string_number"):
                        f.write(f"PV String {sensor.string_number} ")
                    f.write(f"{sensor['name']}</a><br>\n")
                    continue
                sensor_name = sensor.__class__.__name__
                attributes = sensor.get_attributes()
                f.write(f"<h5><a id='{sensor.unique_id}'>")
                if hasattr(sensor, "string_number"):
                    f.write(f"PV String {sensor.string_number} ")
                f.write(f"{sensor['name']}")
                f.write("</a></h5>\n")
                f.write("<table>\n")
                f.write(f"<tr><td>Sensor Class</td><td>{sensor.__class__.__name__}</td></tr>\n")
                if hasattr(sensor, "scan_interval"):
                    f.write(f"<tr><td>Scan Interval</td><td>{sensor.scan_interval}s</td></tr>\n")
                if sensor.unit:
                    f.write(f"<tr><td>Unit of Measurement</td><td>{sensor.unit}</td></tr>\n")
                if sensor._gain:
                    f.write(f"<tr><td>Gain</td><td>{sensor.gain}</td></tr>\n")
                f.write(f"<tr><td>Home Assistant Sensor</td><td>sensor.{sensor['object_id']}</td></tr>\n")
                f.write(f"<tr><td>Home Assistant State Topic</td><td>{hass_sensors[key].state_topic}</td></tr>\n")
                f.write(f"<tr><td>Simplified State Topic</td><td>{sensor.state_topic}</td></tr>\n")
                f.write("<tr><td>Source</td><td>")
                if "source" in attributes:
                    f.write(f"{attributes['source']}")
                elif hasattr(sensor, "_address"):
                    f.write(f"Modbus Register {sensor._address}")
                else:
                    logging.getLogger("root").error(f"Sensor {sensor_name} ({key}) does not have a Modbus address or derived description.")
                f.write("</td></tr>\n")
                if "comment" in attributes:
                    f.write(f"<tr><td>Comment</td><td>{attributes['comment']}</td></tr>\n")
                if sensor_parent in ("Inverter", "ESS", "PVString"):
                    f.write("<tr><td>Applicable To</td><td>")
                    if isinstance(sensor, HybridInverter) and isinstance(sensor, PVInverter):
                        f.write(" Hybrid Inverter and PV Inverter ")
                    elif isinstance(sensor, HybridInverter):
                        f.write(" Hybrid Inverter only")
                    elif isinstance(sensor, PVInverter):
                        f.write(" PV Inverter only")
                    f.write("</td></tr>\n")
                f.write("</table>\n")

    def subscribed_topics(device, index_only: bool = False):
        for key in [key for key, value in sorted(mqtt_sensors.items(), key=lambda x: x[1]["name"]) if "command_topic" in value]:
            sensor = mqtt_sensors[key]
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device:
                if index_only:
                    f.write(f"<a href='#{sensor.unique_id}' style='font-size:small;'>{sensor['name']}</a><br>\n")
                    continue
                f.write(f"<h5><a id='{sensor.unique_id}'>")
                f.write(f"{sensor['name']}")
                if sensor["name"] == "Power":
                    f.write(" On/Off")
                f.write("\n")
                f.write("</a></h5>\n")
                f.write("<table>\n")
                f.write(f"<tr><td>Simplified State Topic</td><td>{sensor.state_topic}</td></tr>\n")
                f.write(f"<tr><td>Simplified Update Topic</td><td>{sensor.command_topic}</td></tr>\n")
                if sensor_parent in ("Inverter", "ESS", "PVString"):
                    f.write("<tr><td>Applicable To</td><td>")
                    if isinstance(sensor, HybridInverter) and isinstance(sensor, PVInverter):
                        f.write(" Hybrid Inverter and PV Inverter ")
                    elif isinstance(sensor, HybridInverter):
                        f.write(" Hybrid Inverter only")
                    elif isinstance(sensor, PVInverter):
                        f.write(" PV Inverter only")
                    f.write("</td></tr>\n")
                f.write("</table>\n")

    hass_sensors = await get_sensor_instances(hass=True)
    mqtt_sensors = await get_sensor_instances(hass=False)
    with TOPICS.open("w") as f:
        f.write("# MQTT Topics\n")
        f.write("\nTopics prefixed with `homeassistant/` are used when the `home-assistant` configuration `enabled` option in the configuration file,\n")
        f.write("or the `SIGENERGY2MQTT_HASS_ENABLED` environment variable, are set to true, or the `--hass-enabled` command line option is specified\n")
        f.write("Otherwise, the topics prefixed with `sigenergy2mqtt/` are used.\n")
        f.write(
            "\nYou can also enable the `sigenergy2mqtt/` topics when Home Assistant discovery is enabled by setting the `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` environment variable to true,\n"
        )
        f.write("or by specifying the `--hass-use-simplified-topics` command line option.\n")
        f.write("\nDefault Scan Intervals are shown in seconds, but may be overridden via configuration. Intervals for derived sensors are dependent on the source sensors.\n")
        write_naming_convention(f)
        # Index
        f.write("<table>\n")
        f.write("<tr><th>Published Topics</th><th>Subscribed Topics</th></tr>\n")
        f.write("<tr><td>\n")
        f.write("\n<h6>Plant</h6>\n")
        published_topics("PowerPlant", index_only=True)
        f.write("\n<h6>Grid Sensor</h6>\n")
        published_topics("GridSensor", index_only=True)
        f.write("\n<h6>Statistics</h6>\n")
        published_topics("PlantStatistics", index_only=True)
        f.write("\n<h6>Inverter</h6>\n")
        published_topics("Inverter", index_only=True)
        f.write("\n<h6>Energy Storage System</h6>\n")
        published_topics("ESS", index_only=True)
        f.write("\n<h6>PV String</h6>\n")
        published_topics("PVString", index_only=True)
        f.write("\n<h6>AC Charger</h6>\n")
        published_topics("ACCharger", index_only=True)
        f.write("\n<h6>DC Charger</h6>\n")
        published_topics("DCCharger", index_only=True)
        f.write("\n<h6>Smart-Port (Enphase Envoy only)</h6>\n")
        published_topics("SmartPort", index_only=True)
        f.write("\n<h6>Metrics</h6>\n")
        metrics_topics(index_only=True)
        f.write("</td><td style='vertical-align: top;'>\n")
        f.write("\n<h6>Plant</h6>\n")
        subscribed_topics("PowerPlant", index_only=True)
        f.write("\n<h6>Inverter</h6>\n")
        subscribed_topics("Inverter", index_only=True)
        f.write("\n<h6>AC Charger</h6>\n")
        subscribed_topics("ACCharger", index_only=True)
        f.write("\n<h6>DC Charger</h6>\n")
        subscribed_topics("DCCharger", index_only=True)
        f.write("</td></tr>\n")
        f.write("</table>\n")
        # Details
        f.write("\n## Published Topics\n")
        f.write("\n### Plant\n")
        published_topics("PowerPlant")
        f.write("\n#### Grid Sensor\n")
        published_topics("GridSensor")
        f.write("\n#### Statistics\n")
        published_topics("PlantStatistics")
        f.write("\n### Inverter\n")
        published_topics("Inverter")
        f.write("\n#### Energy Storage System\n")
        published_topics("ESS")
        f.write("\n#### PV String\n")
        f.write("\nThe actual number of PV Strings is determined from `PV String Count` in the Inverter.\n")
        published_topics("PVString")
        f.write("\n### AC Charger\n")
        published_topics("ACCharger")
        f.write("\n### DC Charger\n")
        published_topics("DCCharger")
        f.write("\n#### Smart-Port (Enphase Envoy only)\n")
        published_topics("SmartPort")
        f.write("\n### Metrics\n")
        f.write("\nMetrics are _only_ published to the sigenergy2mqtt/metrics topics, even when Home Assistant discovery is enabled. The scan interval cannot be altered.\n")
        metrics_topics()
        f.write("\n## Subscribed Topics\n")
        f.write("\n### Plant\n")
        subscribed_topics("PowerPlant")
        f.write("\n### Inverter\n")
        subscribed_topics("Inverter")
        f.write("\n### AC Charger\n")
        subscribed_topics("ACCharger")
        f.write("\n### DC Charger\n")
        subscribed_topics("DCCharger")
        logging.info(f"{TOPICS} successfully updated")


def download_latest(path: str) -> None:
    file = Path(Path(path).name)

    if file.exists() and file.stat().st_mtime >= (datetime.now(tz=timezone.utc) - timedelta(days=1)).timestamp():
        logging.info(f"{file} was updated less than a day ago.")
        return

    # 1. Find the latest commit that modified the file
    commits_url = "https://api.github.com/repos/TypQxQ/Sigenergy-Local-Modbus/commits"
    headers = {"Accept": "application/vnd.github.v3+json"}
    params = {"path": path, "per_page": 1}  # only need the latest commit
    commits_response = requests.get(commits_url, headers=headers, params=params)
    commits_response.raise_for_status()
    latest_commit = commits_response.json()[0]
    commit_sha = latest_commit["sha"]
    commit_date = datetime.strptime(latest_commit["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    logging.info(f"Latest commit for {path}: {commit_sha} ({commit_date})")

    if file.exists() and file.stat().st_mtime >= commit_date.timestamp():
        logging.info(f"{file} is already up to date.")
        return

    # 2. Download the file contents at that commit
    contents_url = f"https://api.github.com/repos/TypQxQ/Sigenergy-Local-Modbus/contents/{path}"
    params = {"ref": commit_sha}
    file_response = requests.get(contents_url, headers={"Accept": "application/vnd.github.v3.raw"}, params=params)
    file_response.raise_for_status()

    # Save to local file
    with file.open("wb") as f:
        f.write(file_response.content)

    logging.info(f"{file} downloaded from commit {commit_sha}")


def invert_dict_by_field(original_dict, field):
    if not isinstance(original_dict, dict):
        raise TypeError("original_dict must be a dictionary")
    new_dict = {}
    for orig_key, value in original_dict.items():
        if not isinstance(value, dict):
            raise ValueError(f"Value for key '{orig_key}' is not a dictionary")
        field_value = getattr(value, field, None)
        if field_value is None:
            continue
        if field_value not in new_dict:
            new_dict[field_value] = []
        new_dict[field_value].append(orig_key)
    return new_dict


def write_naming_convention(f):
    f.write("\n#### Naming Convention for Sensors in `sigenergy2mqtt`\n\n")
    f.write("\n- Sensor names begin with a prefix. The default is `sigen`, but this may be changed via configuration.")
    f.write("\n- _ separator")
    f.write("\n- The index of the Modbus host from the configuration file (or auto-discovery), starting from 0.")
    f.write(" (This is to prevent clashes with the <a href='https://github.com/TypQxQ/Sigenergy-Local-Modbus'>TypQxQ Sigenergy-Local-Modbus</a> HACS integration.)")
    f.write("\n- _ separator")
    f.write("\n##### _Followed by:_")
    f.write("\n###### Plant Sensors\n\n")
    f.write("\n- The sensor description.")
    f.write("\n  - Plant sensors have no device type or device ID, but the description _may_ be prefixed with `plant_` for clarity.")
    f.write("\n  - The description for Smart Load sensors will be prefixed by `smart_load_` (not `plant_`).")
    f.write("\n  - The description for Statistics Interface sensors will be prefixed by `si_` (not `plant_`).")
    f.write("\n##### _OR:_")
    f.write("\n###### Device Sensors\n\n")
    f.write("\n- The device type (inverter, ac_charger, or dc_charger).")
    f.write("\n- _ separator")
    f.write("\n- The Modbus device ID. Normally 1 for the Inverter and DC Charger and 2 for an AC Charger, but depends on how the installer configured the Modbus interface.")
    f.write("\n- _ separator")
    f.write("\n- The sensor description.\n\n")


async def compare_sensor_instances():
    typqxq_instances = {}
    sensor_instances = await get_sensor_instances()
    registers = invert_dict_by_field(sensor_instances, "_address")

    from modbusregisterdefinitions import (
        DataType,
        PLANT_RUNNING_INFO_REGISTERS,
        PLANT_PARAMETER_REGISTERS,
        INVERTER_RUNNING_INFO_REGISTERS,
        INVERTER_PARAMETER_REGISTERS,
        AC_CHARGER_RUNNING_INFO_REGISTERS,
        AC_CHARGER_PARAMETER_REGISTERS,
        DC_CHARGER_RUNNING_INFO_REGISTERS,
        DC_CHARGER_PARAMETER_REGISTERS,
    )

    datatype_map = {
        DataType.U16: ModbusClient.DATATYPE.UINT16,
        DataType.U32: ModbusClient.DATATYPE.UINT32,
        DataType.U64: ModbusClient.DATATYPE.UINT64,
        DataType.S16: ModbusClient.DATATYPE.INT16,
        DataType.S32: ModbusClient.DATATYPE.INT32,
        DataType.STRING: ModbusClient.DATATYPE.STRING,
    }

    for map in (
        PLANT_RUNNING_INFO_REGISTERS,
        PLANT_PARAMETER_REGISTERS,
        INVERTER_RUNNING_INFO_REGISTERS,
        INVERTER_PARAMETER_REGISTERS,
        AC_CHARGER_RUNNING_INFO_REGISTERS,
        AC_CHARGER_PARAMETER_REGISTERS,
        DC_CHARGER_RUNNING_INFO_REGISTERS,
        DC_CHARGER_PARAMETER_REGISTERS,
    ):
        for k, v in map.items():
            typqxq_instances[v.address] = (k, v)
            if v.address not in registers:
                logging.warning(f"Register {v.address} ({k}) not found in sensor instances")

    for k, v in registers.items():
        if isinstance(k, int) and k not in typqxq_instances:
            logging.warning(f"Register {k} ({v}) found in sensor instances but not defined in TypQxQ")

    with SENSORS.open("w") as f:
        f.write("# Home Assistant Sensors\n")
        f.write("\nThe following is a list of the Modbus sensors published by the <a href='https://github.com/TypQxQ/Sigenergy-Local-Modbus'>TypQxQ Sigenergy-Local-Modbus</a> HACS integration,")
        f.write("\nand the corresponding sensor in `sigenergy2mqtt`. You can click on the `sigenergy2mqtt` sensor for more information.\n\n")
        write_naming_convention(f)
        f.write("| Sigenergy-Local-Modbus | `sigenergy2mqtt` |\n")
        f.write("|------------------------|------------------|\n")

        for address, (typqxq_name, typqxq_def) in dict(sorted(typqxq_instances.items(), key=lambda item: item[1][0])).items():
            sensor_names = registers.get(address, [])
            f.write(f"| sigen_{typqxq_name} ")
            if not sensor_names:
                f.write("| N/A |\n")
                logging.warning(f"Register {address} found in TypQxQ but not in sensor instances")
                continue
            f.write("| ")
            for sensor_name in sensor_names:
                sensor_instance = sensor_instances[sensor_name]
                # Compare data type
                typqxq_type = getattr(typqxq_def, "data_type", None)
                sensor_type = sensor_instance._data_type
                mapped_typqxq_type = datatype_map.get(typqxq_type, None)
                if mapped_typqxq_type is None or mapped_typqxq_type != sensor_type:
                    logging.warning(f"Data type mismatch for register {address} ({typqxq_name} vs {sensor_name}): '{typqxq_type}' != '{sensor_type}'")
                # Compare count
                typqxq_count = getattr(typqxq_def, "count", None)
                sensor_count = sensor_instance._count
                sensor_alarms = getattr(sensor_instance, "_alarms", [])
                if typqxq_count != sensor_count and not (len(sensor_alarms) > 0 and sensor_count / len(sensor_alarms) == typqxq_count):
                    logging.warning(f"Count mismatch for register {address} ({typqxq_name} vs {sensor_name}): '{typqxq_count}' != '{sensor_count}'")
                # Compare unit
                typqxq_unit = getattr(typqxq_def, "unit", None)
                sensor_unit = sensor_instance.unit
                if (
                    typqxq_unit is not None
                    and typqxq_unit != sensor_unit
                    and not ((typqxq_unit == "kW" and sensor_unit == "W") or (typqxq_unit == "kvar" and sensor_unit == "var") or (typqxq_unit in ("s", "min") and sensor_unit is None))
                ):
                    logging.warning(f"Unit mismatch for register {address} ({typqxq_name} vs {sensor_name}): '{typqxq_unit}' != '{sensor_unit}'")
                # Compare gain
                typqxq_type = getattr(typqxq_def, "data_type", None)
                typqxq_gain = getattr(typqxq_def, "gain", None)
                sensor_gain = sensor_instance.gain
                if typqxq_type != DataType.STRING and typqxq_gain != sensor_gain and typqxq_unit == sensor_unit:
                    logging.warning(f"Gain mismatch for register {address} ({typqxq_name} vs {sensor_name}): '{typqxq_gain}' != '{sensor_gain}'")
                f.write(f"<a href='./TOPICS.md#{sensor_instance.unique_id}'>{sensor_instance['object_id']}")
                if len(sensor_alarms) > 0:
                    f.write(" (Combined Alarm)")
                f.write("</a><br>")
            f.write(" |\n")

        logging.info(f"{SENSORS} successfully updated")
        logging.info("Comparison of sensor instances completed")


if __name__ == "__main__":
    download_latest("custom_components/sigen/modbusregisterdefinitions.py")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sensor_index())
    loop.run_until_complete(compare_sensor_instances())
    cancel_sensor_futures()
    loop.close()
