import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

if not os.getcwd().endswith("resources"):
    os.chdir(str((Path(__file__).parent / "../resources").resolve()))

sys.path.insert(0, str((Path(__file__).parent / "..").resolve()))
sys.path.insert(0, str((Path(__file__).parent / "../resources").resolve()))

import requests
from pymodbus.client import AsyncModbusTcpClient as ModbusClient

from sigenergy2mqtt.common import ConsumptionMethod, HybridInverter, Protocol, PVInverter
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.main.main import INVERTER_ILLEGAL_DATA_ADDRESSES, PLANT_ILLEGAL_DATA_ADDRESSES
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, ModbusSensorMixin, ReadableSensorMixin, ReservedSensor, Sensor, TypedSensorMixin, WritableSensorMixin, WriteOnlySensor
from sigenergy2mqtt.sensors.plant_derived import PlantConsumedPower
from sigenergy2mqtt.sensors.plant_read_write import RemoteEMSLimit
from tests.utils import get_sensor_instances

HTTP_TIMEOUT = 15  # Default timeout (seconds) for all outbound GitHub API requests.
ILLEGAL_DATA_ADDRESSES: list[int] = INVERTER_ILLEGAL_DATA_ADDRESSES + PLANT_ILLEGAL_DATA_ADDRESSES
RANGE_PATTERN = r"Range:\s*\[(.*?)\]"
SENSORS: Path = Path("sensors/SENSORS.md")
TOPICS: Path = Path("sensors/TOPICS.md")
SIGENERGY_LOCAL_MODBUS_REGISTERS: Path = Path("../sigenergy2mqtt/sensors/base/_sigenergy_local_modbus_registers.py")


def write_naming_convention(f) -> None:
    """Write the sensor naming convention section to the given file handle."""
    f.write("\n\n> [!IMPORTANT]")
    f.write("\n> All `sigenergy2mqtt` sensor names begin with a prefix. The default is `sigen`, but this may be changed via configuration.")
    f.write("\n> This is always followed by `_`, then the index of the Modbus host from the configuration file (or auto-discovery), starting from `0`.")
    f.write(" (This is to prevent clashes with the <a href='https://github.com/TypQxQ/Sigenergy-Local-Modbus'>TypQxQ/Sigenergy-Local-Modbus</a> HACS integration.)")
    f.write("\n> ")
    f.write("\n> Of course, if you have enabled the option to use Sigenergy-Local-Modbus naming, then you can ignore this section.")
    f.write("\n\n> [!NOTE]")
    f.write("\n> **Naming Convention for Plant Sensors in `sigenergy2mqtt`**")
    f.write("\n>- Prefix")
    f.write("\n>- `_` separator")
    f.write("\n>- Index")
    f.write("\n>- `_` separator")
    f.write("\n>- The sensor description")
    f.write("\n> ")
    f.write("\n> **NOTE:**")
    f.write("\n>  - Plant sensors have no device type or device ID, but the description _may_ be prefixed with `plant_` for clarity")
    f.write("\n>  - The description for Smart Load sensors will be prefixed by `smart_load_` (not `plant_`)")
    f.write("\n>  - The description for Statistics Interface sensors will be prefixed by `si_` (not `plant_`)")
    f.write("\n\n> [!NOTE]")
    f.write("\n> **Naming Convention for Device Sensors in `sigenergy2mqtt`**")
    f.write("\n>- Prefix")
    f.write("\n>- `_` separator")
    f.write("\n>- Index")
    f.write("\n>- `_` separator")
    f.write("\n>- The device type (inverter, ac_charger, or dc_charger)")
    f.write("\n>- `_` separator")
    f.write("\n>- The Modbus device ID (normally **1** for the Inverter and DC Charger and **2** for an AC Charger, but depends on how the installer configured the Modbus interface)")
    f.write("\n>- `_` separator")
    f.write("\n>- The sensor description\n\n")


async def sensor_index() -> None:
    """Generate TOPICS.md by iterating over all sensor instances.

    Builds an index table followed by detailed per-sensor sections covering
    published (state) topics and subscribed (command) topics for every device
    category, plus the metrics service.
    """
    with _swap_active_config(Config()):
        hass_sensors = await get_sensor_instances(home_assistant_enabled=True, concrete_sensor_check=True)
    with _swap_active_config(Config()):
        mqtt_sensors = await get_sensor_instances(home_assistant_enabled=False, concrete_sensor_check=True)

    def extract_min_max(range_string: str, precision: int | None, gain: float):
        """Parse a 'Range: [...]' annotation and return (min, max) as floats where possible.

        Values are rounded to *precision* decimal places. Returns ``(None, None)``
        when the pattern is absent or the content cannot be parsed.

        The sentinel value ``0xFFFFFFFE`` is a reserved Modbus indicator meaning
        "no upper limit defined"; it is mapped to 4294967.295 (i.e. 0xFFFFFFFE / 1000,
        the maximum representable kW value for a U32 register with gain 0.001).
        """
        match = re.search(RANGE_PATTERN, range_string, re.DOTALL)
        if match:
            content = match.group(1).strip()

            # The pattern below identifies potential "values" (numbers, formulas, hex)
            # It looks for sequences of characters that form numbers, hex, or formula components:
            # [-\w\d.*]+ covers negative signs, words (like 'base value'), digits, hex letters, periods, and asterisks.

            # We look for sequences that are either simple numbers/formulas OR hex numbers
            # This is a general approach to capture the *components* of the range definition.

            # Refined pattern to capture potential values/formulas more accurately:
            # Captures:
            # 1. Standard decimal/formula part (potentially negative, includes words/ops)
            #    [-\w\d\s.*]+?
            #    OR
            # 2. Hex numbers starting with 0x (case-insensitive for a-f)
            #    0x[0-9a-fA-F]+

            # A simple non-greedy pattern to find components separated by , or U
            # For simplicity, we capture the entire component string

            # Use simple string splitting and stripping for better control than complex regex here

            # Split by the delimiters we expect to separate values
            components = re.split(r",|\s*U\s*", content)

            # Strip extraneous parentheses and whitespace from components
            cleaned_components = [comp.strip("() \t\n") for comp in components if comp.strip("() \t\n")]

            if cleaned_components:
                try:
                    min_val = round(float(cleaned_components[0]), precision)
                except ValueError:
                    min_val = cleaned_components[0]
                try:
                    if cleaned_components[-1] == "0xFFFFFFFE":
                        # Reserved sentinel: "no upper limit". Mapped to the maximum
                        # representable value for a U32 register with gain 0.001.
                        max_val = 4294967.295
                    else:
                        max_val = round(float(cleaned_components[-1]), precision)
                except ValueError:
                    max_val = cleaned_components[-1]
                return (min_val, max_val)
            else:
                logging.error(f"Could not parse min/max values from {range_string}")
        return None, None

    def metrics_topics(f, index_only: bool = False) -> int:
        """Write metrics sensor rows to *f* and return the number of sensors written.

        When *index_only* is True, only anchor links are emitted (for the index
        table); otherwise a full Markdown table is written.
        """
        count = 0
        if not index_only:
            f.write("| Metric | Interval | Unit | State Topic| Command Topic |\n")
            f.write("|--------|---------:|------|------------|---------------|\n")
        metrics = MetricsService(Protocol.N_A)
        for metric in [s for s in sorted(metrics.all_sensors.values(), key=lambda x: x.name)]:
            count += 1
            if index_only:
                f.write(f"<a href='#{metric.unique_id}'>{metric['name']}</a><br>\n")
            elif metric.__class__.__name__ == "ResetMetrics":
                f.write(f"| <a id='{metric.unique_id}'>{metric['name']}</a> |||| {metric['command_topic']} |\n")
            else:
                f.write(f"| <a id='{metric.unique_id}'>{metric['name']}</a> | 1 | {metric['unit_of_measurement'] if metric['unit_of_measurement'] else ''} | {metric['state_topic']} ||\n")
        return count

    def published_topics(f, device: str, index_only: bool = False) -> int:
        """Write published-topic entries for all sensors belonging to *device* to *f*.

        When *index_only* is True, only anchor links are emitted; otherwise full
        HTML tables are written for each sensor. Returns the number of sensors written.
        """
        count = 0
        for key in [key for key, value in sorted(mqtt_sensors.items(), key=lambda x: x[1].name) if "state_topic" in value and not isinstance(value, WriteOnlySensor)]:
            sensor: Sensor = mqtt_sensors[key]
            if isinstance(sensor, ReservedSensor):
                continue
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device and sensor.publishable:
                count += 1
                string_number: int | None = getattr(sensor, "string_number", None)
                protocol = "N/A" if sensor.protocol_version == Protocol.N_A else sensor.protocol_version.value
                if index_only:
                    f.write(f"<a href='#{sensor.unique_id}'>")
                    if string_number:
                        f.write(f"PV String {string_number} ")
                    f.write(f"{sensor['name']}</a><br>\n")
                    continue
                sensor_name = sensor.__class__.__name__
                attributes = sensor.get_attributes()
                f.write(f"<h5><a id='{sensor.unique_id}'>")
                if string_number:
                    f.write(f"PV String {string_number} ")
                f.write(f"{sensor['name']}")
                f.write("</a></h5>\n")
                f.write("<table>\n")
                f.write(f"<tr><td>Sensor&nbsp;Class</td><td>{sensor_name}</td></tr>\n")
                if isinstance(sensor, ReadableSensorMixin):
                    f.write(f"<tr><td>Scan&nbsp;Interval</td><td>{sensor.scan_interval}s</td></tr>\n")
                if isinstance(sensor, Sensor) and sensor.unit:
                    f.write(f"<tr><td>Unit&nbsp;of&nbsp;Measurement</td><td>{sensor.unit}</td></tr>\n")
                if sensor._gain:
                    f.write(f"<tr><td>Gain</td><td>{sensor.gain}</td></tr>\n")
                f.write(f"<tr><td>Home&nbsp;Assistant&nbsp;Sensor</td><td>sensor.{sensor['object_id']}</td></tr>\n")
                f.write(f"<tr><td>Home&nbsp;Assistant&nbsp;State&nbsp;Topic</td><td>{hass_sensors[key].state_topic}</td></tr>\n")
                f.write(f"<tr><td>Simplified&nbsp;State&nbsp;Topic</td><td>{sensor.state_topic}</td></tr>\n")
                if sensor.publish_raw:
                    f.write(f"<tr><td>Raw&nbsp;State&nbsp;Topic</td><td>{sensor['raw_state_topic']}</td></tr>\n")
                f.write("<tr><td>Source</td><td>")
                if "source" in attributes:
                    if isinstance(sensor, PlantConsumedPower):
                        f.write("<dl>")
                        for method in ConsumptionMethod:
                            sensor.method = method
                            source = sensor.get_attributes()["source"]
                            f.write(f"<dt>{method.name} Configuration Option:</dt><dd>{source}")
                            if method != ConsumptionMethod.CALCULATED:
                                f.write(" (Protocol V2.8+ only)")
                            f.write("</dd>")
                        f.write("</dl>")
                        protocol = "N/A"
                    else:
                        f.write(f"{attributes['source']}")
                        if attributes["source"] in ILLEGAL_DATA_ADDRESSES:
                            f.write(" (may not be available on all devices)")
                elif isinstance(sensor, ModbusSensorMixin):
                    f.write(f"{sensor.address}")
                    if sensor.address in ILLEGAL_DATA_ADDRESSES:
                        f.write(" (may not be available on all devices)")
                else:
                    logging.getLogger().error(f"Sensor {sensor_name} ({key}) does not have a Modbus address or derived description.")
                f.write("</td></tr>\n")
                if "options" in sensor:
                    options = cast(list[str], sensor["options"])
                    f.write("<tr><td>Options<br><br>(Number == Raw value)</td><td><ol start='0'>")
                    for i in range(0, len(options)):
                        if options[i] != "":
                            f.write(f"<li value='{i}'>{options[i]}</li>")
                    f.write("</ol></td></tr>\n")
                if "comment" in attributes:
                    f.write(f"<tr><td>Comment</td><td>{attributes['comment']}")
                    if isinstance(sensor, RemoteEMSLimit):
                        f.write("<br><i>NOTE: For Firmware SPC113 and later, available globally and not restricted by Remote EMS Control Mode.</i>")
                    f.write("</td></tr>\n")
                if sensor_parent in ("Inverter", "ESS", "PVString"):
                    f.write("<tr><td>Applicable To</td><td>")
                    if isinstance(sensor, HybridInverter) and isinstance(sensor, PVInverter):
                        f.write(" Hybrid Inverter and PV Inverter ")
                    elif isinstance(sensor, HybridInverter):
                        f.write(" Hybrid Inverter only")
                    elif isinstance(sensor, PVInverter):
                        f.write(" PV Inverter only")
                    f.write("</td></tr>\n")
                f.write(f"<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>{protocol}</td></tr>\n")
                if sensor.sanity_check.is_enabled:
                    f.write(f"<tr><td>Modbus&nbsp;Read&nbsp;Sanity&nbsp;Check</td><td>{sensor.sanity_check}</td></tr>\n")
                f.write("</table>\n")
        return count

    def subscribed_topics(f, device, index_only: bool = False) -> int:
        """Write subscribed-topic entries for all writable sensors belonging to *device* to *f*.

        When *index_only* is True, only anchor links are emitted; otherwise full
        HTML tables are written for each sensor. Returns the number of sensors written.
        """
        count = 0
        for key in [key for key, value in sorted(mqtt_sensors.items(), key=lambda x: x[1].name) if "command_topic" in value]:
            if isinstance(mqtt_sensors[key], ReservedSensor):
                continue
            sensor = mqtt_sensors[key]
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device:
                protocol = "N/A" if sensor.protocol_version == Protocol.N_A else sensor.protocol_version.value
                count += 1
                if index_only:
                    f.write(f"<a href='#{sensor.unique_id}_set'>{sensor['name']}</a><br>\n")
                    continue
                f.write(f"<h5><a id='{sensor.unique_id}_set'>")
                f.write(f"{sensor['name']}")
                if sensor["name"] == "Power":
                    f.write("&nbsp;On/Off")
                f.write("\n")
                f.write("</a></h5>\n")
                f.write("<table>\n")
                f.write(f"<tr><td>Home&nbsp;Assistant&nbsp;Update&nbsp;Topic</td><td>{cast(WritableSensorMixin, hass_sensors[key]).command_topic}</td></tr>\n")
                f.write(f"<tr><td>Simplified&nbsp;Update&nbsp;Topic</td><td>{cast(WritableSensorMixin, sensor).command_topic}</td></tr>\n")
                attributes = sensor.get_attributes()
                min, max = None, None
                if "comment" in attributes:
                    comment: str = cast(str, attributes["comment"])
                    if re.match(r"0:(Start|Stop)\s+1:(Start|Stop)", comment):
                        f.write(f"<tr><td>Valid&nbsp;Values</td><td>{comment}</td></tr>\n")
                    else:
                        f.write(f"<tr><td>Comment</td><td>{comment}</td></tr>\n")
                        if "min" in sensor and "max" in sensor and isinstance(sensor["min"], (float, int)) and isinstance(sensor["max"], (float, int)):
                            min, max = extract_min_max(comment, sensor.precision, sensor.gain)
                if "min" in sensor:
                    f.write(f"<tr><td>Minimum&nbsp;Value</td><td>{min if min is not None else sensor['min']}</td></tr>\n")
                if "max" in sensor:
                    f.write(f"<tr><td>Maximum&nbsp;Value</td><td>{max if max is not None else sensor['max']}</td></tr>\n")
                if "options" in sensor:
                    f.write("<tr><td>Valid&nbsp;Values</td><td><ul>")
                    options = cast(list[str], sensor["options"])
                    for i in range(0, len(options)):
                        if options[i] is not None:
                            f.write(f"<li value='{i}'>\"{options[i]}\"</li>")
                    f.write("</ol></td></tr>\n")
                if sensor_parent in ("Inverter", "ESS", "PVString"):
                    f.write("<tr><td>Applicable&nbsp;To</td><td>")
                    if isinstance(sensor, HybridInverter) and isinstance(sensor, PVInverter):
                        f.write(" Hybrid Inverter and PV Inverter ")
                    elif isinstance(sensor, HybridInverter):
                        f.write(" Hybrid Inverter only")
                    elif isinstance(sensor, PVInverter):
                        f.write(" PV Inverter only")
                    f.write("</td></tr>\n")
                f.write(f"<tr><td>Since&nbsp;Protocol&nbsp;Version</td><td>{protocol}</td></tr>\n")
                f.write("</table>\n")
        return count

    with TOPICS.open("w") as f:
        f.write("<!-- Generated by scripts/update_md.py. Do not edit manually. -->\n")
        f.write("# MQTT Topics\n")
        f.write("\nTopics prefixed with `homeassistant/` are used when the `home-assistant` configuration `enabled` option in the configuration file,\n")
        f.write("or the `SIGENERGY2MQTT_HASS_ENABLED` environment variable, are set to true, or the `--hass-enabled` command line option is specified\n")
        f.write("Otherwise, the topics prefixed with `sigenergy2mqtt/` are used.\n")
        f.write("\nYou can also enable the `sigenergy2mqtt/` topics when Home Assistant discovery is enabled by setting the `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` environment variable to true,\n")
        f.write("or by specifying the `--hass-use-simplified-topics` command line option.\n")
        f.write("\nDefault Scan Intervals are shown in seconds, but may be overridden via configuration. Intervals for derived sensors are dependent on the source sensors.\n")
        write_naming_convention(f)
        # Index
        published = 0
        subscribed = 0
        f.write("<table>\n")
        f.write("<tr><th>Published Topics</th><th>Subscribed Topics</th></tr>\n")
        f.write("<tr><td>\n")
        f.write("\n<h6>Plant</h6>\n")
        published += 2 + published_topics(f, "PowerPlant", index_only=True)
        f.write("\n<h6>Grid Sensor</h6>\n")
        published += 2 + published_topics(f, "GridSensor", index_only=True)
        f.write("\n<h6>Statistics</h6>\n")
        published += 2 + published_topics(f, "PlantStatistics", index_only=True)
        f.write("\n<h6>Inverter</h6>\n")
        published += 2 + published_topics(f, "Inverter", index_only=True)
        f.write("\n<h6>Energy Storage System</h6>\n")
        published += 2 + published_topics(f, "ESS", index_only=True)
        f.write("\n<h6>PV String</h6>\n")
        published += 2 + published_topics(f, "PVString", index_only=True)
        f.write("\n<h6>AC Charger</h6>\n")
        published += 2 + published_topics(f, "ACCharger", index_only=True)
        f.write("\n<h6>DC Charger</h6>\n")
        published += 2 + published_topics(f, "DCCharger", index_only=True)
        f.write("\n<h6>Smart-Port (Enphase Envoy only)</h6>\n")
        published += 2 + published_topics(f, "SmartPort", index_only=True)
        f.write("\n<h6>Metrics</h6>\n")
        published += metrics_topics(f, index_only=True)
        f.write("</td><td>\n")
        f.write("\n<h6>Plant</h6>\n")
        subscribed += 2 + subscribed_topics(f, "PowerPlant", index_only=True)
        f.write("\n<h6>Inverter</h6>\n")
        subscribed += 1 + subscribed_topics(f, "Inverter", index_only=True)
        f.write("\n<h6>AC Charger</h6>\n")
        subscribed += 1 + subscribed_topics(f, "ACCharger", index_only=True)
        f.write("\n<h6>DC Charger</h6>\n")
        subscribed += 1 + subscribed_topics(f, "DCCharger", index_only=True)
        for _ in range(subscribed, published):
            f.write("<br>")
        f.write("</td></tr>\n")
        f.write("</table>\n")
        # Details
        f.write("\n## Published Topics\n")
        f.write("\n### Plant\n")
        published_topics(f, "PowerPlant")
        f.write("\n#### Grid Sensor\n")
        published_topics(f, "GridSensor")
        f.write("\n#### Statistics\n")
        published_topics(f, "PlantStatistics")
        f.write("\n### Inverter\n")
        published_topics(f, "Inverter")
        f.write("\n#### Energy Storage System\n")
        published_topics(f, "ESS")
        f.write("\n#### PV String\n")
        f.write("\nThe actual number of PV Strings is determined from `PV String Count` in the Inverter.\n")
        published_topics(f, "PVString")
        f.write("\n### AC Charger\n")
        published_topics(f, "ACCharger")
        f.write("\n### DC Charger\n")
        published_topics(f, "DCCharger")
        f.write("\n#### Smart-Port (Enphase Envoy only)\n")
        published_topics(f, "SmartPort")
        f.write("\n### Metrics\n")
        f.write("\nMetrics are _only_ published to the sigenergy2mqtt/metrics topics, even when Home Assistant discovery is enabled. The scan interval cannot be altered.\n")
        f.write("\nInfluxDB Metrics are only published when the InfluxDB integration is enabled.\n\n")
        metrics_topics(f)
        f.write("\n## Subscribed Topics\n")
        f.write("\n### Plant\n")
        subscribed_topics(f, "PowerPlant")
        f.write("\n### Inverter\n")
        subscribed_topics(f, "Inverter")
        f.write("\n### AC Charger\n")
        subscribed_topics(f, "ACCharger")
        f.write("\n### DC Charger\n")
        subscribed_topics(f, "DCCharger")
        logging.info(f"{TOPICS} successfully updated")


def invert_dict_by_attr(original_dict: dict, attr: str) -> dict:
    """Invert *original_dict* by grouping keys under the attribute value of their values.

    For each ``(key, value)`` pair in *original_dict*, the attribute named *attr*
    is read from *value* via ``getattr``. Entries where the attribute is ``None``
    (or absent) are skipped. The result maps each distinct attribute value to the
    list of original keys that shared it.

    Args:
        original_dict: A mapping whose values are objects exposing *attr*.
        attr: The attribute name to read from each value object.

    Returns:
        A dict mapping ``attr`` values → lists of original keys.

    Raises:
        TypeError: If *original_dict* is not a dict.
    """
    if not isinstance(original_dict, dict):
        raise TypeError("original_dict must be a dictionary")
    new_dict: dict = {}
    for orig_key, value in original_dict.items():
        field_value = getattr(value, attr, None)
        if field_value is None:
            continue
        new_dict.setdefault(field_value, []).append(orig_key)
    return new_dict


def write_sigenergy_local_modbus_registers(typqxq_instances: dict[int, tuple[str, Any]]) -> None:
    """Write static register mappings for Sigenergy-Local-Modbus compatibility."""
    lines = [
        '"""Generated by scripts/update_md.py. Do not edit manually."""',
        "",
        "from __future__ import annotations",
        "",
        "SIGENERGY_LOCAL_MODBUS_REGISTERS: dict[int, dict[str, str | float | None]] = {",
    ]

    for address, (typqxq_name, typqxq_def) in sorted(typqxq_instances.items()):
        object_id = f"sigen_{typqxq_name}"
        gain = getattr(typqxq_def, "gain", None)
        unit = getattr(typqxq_def, "unit", None)
        uom = f"{unit!r}"
        if unit is not None and "<UnitOf" in uom:
            uom = f"{unit.value!r}"
        lines.append(f"    {address}: {{'object_id': {object_id!r}, 'gain': {gain!r}, 'unit': {uom}}},")

    lines.append("}")
    lines.append("")

    with SIGENERGY_LOCAL_MODBUS_REGISTERS.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logging.info(f"{SIGENERGY_LOCAL_MODBUS_REGISTERS} successfully updated")


async def compare_sensor_instances() -> None:
    """Compare sigenergy2mqtt sensor instances against the TypQxQ register definitions.

    Downloads (or reuses a cached copy of) the TypQxQ Modbus register definition
    module, then cross-checks every register address for data-type, count, unit,
    and gain mismatches, logging warnings for any discrepancies found.
    Writes the result to SENSORS.md.

    Note: The import of ``resources.modbusregisterdefinitions`` is intentionally
    deferred to this function because the module is fetched at runtime by
    ``download_latest`` and may not exist when the script is first loaded.
    """
    typqxq_instances: dict[int, tuple[str, Any]] = {}
    with _swap_active_config(Config()):
        sensor_instances = await get_sensor_instances(home_assistant_enabled=True)
        registers = invert_dict_by_attr(sensor_instances, "address")

    # Deferred import: modbusregisterdefinitions.py is downloaded at runtime
    # by download_latest() and cannot be imported at module load time.
    from resources.modbusregisterdefinitions import (
        AC_CHARGER_PARAMETER_REGISTERS,
        AC_CHARGER_RUNNING_INFO_REGISTERS,
        DC_CHARGER_PARAMETER_REGISTERS,
        DC_CHARGER_RUNNING_INFO_REGISTERS,
        INVERTER_PARAMETER_REGISTERS,
        INVERTER_RUNNING_INFO_REGISTERS,
        PLANT_PARAMETER_REGISTERS,
        PLANT_RUNNING_INFO_REGISTERS,
        DataType,
    )

    datatype_map: dict[DataType, ModbusClient.DATATYPE] = {
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

    write_sigenergy_local_modbus_registers(typqxq_instances)

    for k, v in registers.items():
        if isinstance(k, int) and k not in typqxq_instances:
            for i in v:
                if isinstance(sensor_instances[i], ReservedSensor):
                    continue
                logging.warning(f"V{sensor_instances[i].protocol_version} Register {k} ({sensor_instances[i].name}) found in sensor instances but not defined in TypQxQ")

    with SENSORS.open("w") as f:
        f.write("<!-- Generated by scripts/update_md.py. Do not edit manually. -->\n")
        f.write("# Home Assistant Sensors\n")
        f.write("\nThe following is a list of the Modbus sensors published by the <a href='https://github.com/TypQxQ/Sigenergy-Local-Modbus'>TypQxQ/Sigenergy-Local-Modbus</a> HACS integration,")
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
                if isinstance(sensor_instance, TypedSensorMixin) and not isinstance(sensor_instance, AlarmCombinedSensor):
                    # Compare data type
                    typqxq_type = getattr(typqxq_def, "data_type")
                    sensor_type = sensor_instance.data_type
                    mapped_typqxq_type = datatype_map.get(typqxq_type, None)
                    if mapped_typqxq_type is None or mapped_typqxq_type != sensor_type:
                        logging.warning(f"Data type mismatch for register {address} ({typqxq_name} vs {sensor_name}): '{typqxq_type}' != '{sensor_type}'")
                if isinstance(sensor_instance, ModbusSensorMixin):
                    # Compare count
                    typqxq_count = getattr(typqxq_def, "count", None)
                    sensor_count = sensor_instance.count
                    sensor_alarms = getattr(sensor_instance, "alarms", [])
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
                typqxq_type = getattr(typqxq_def, "data_type")
                typqxq_gain = getattr(typqxq_def, "gain", None)
                sensor_gain = sensor_instance.gain
                if typqxq_type != DataType.STRING and typqxq_gain != sensor_gain and typqxq_unit == sensor_unit:
                    logging.warning(f"Gain mismatch for register {address} ({typqxq_name} vs {sensor_name}): '{typqxq_gain}' != '{sensor_gain}'")
                f.write(f"<a href='./TOPICS.md#{sensor_instance.unique_id}'>{sensor_instance['object_id']}")
                if isinstance(sensor_instance, AlarmCombinedSensor):
                    f.write(" (Combined Alarm)")
                f.write("</a><br>")
            f.write(" |\n")

        logging.info(f"{SENSORS} successfully updated")
        logging.info("Comparison of sensor instances completed")


def download_latest(path: str) -> None:
    """Download the most recently committed version of *path* from the TypQxQ GitHub repo.

    Checks every branch for the latest commit that touched *path* and downloads
    the file at that commit SHA. Skips the download if the local copy is already
    up to date (mtime >= commit date), and skips altogether if the local file was
    modified within the last 24 hours (to avoid repeated API calls).

    Args:
        path: Repository-relative path to the file to download
              (e.g. ``"custom_components/sigen/modbusregisterdefinitions.py"``).
    """
    OWNER = "TypQxQ"
    REPO = "Sigenergy-Local-Modbus"
    BASE = f"https://api.github.com/repos/{OWNER}/{REPO}"

    file = Path(Path(path).name)

    if file.exists() and file.stat().st_mtime >= (datetime.now(tz=timezone.utc) - timedelta(days=1)).timestamp():
        logging.info(f"{file} was updated less than a day ago.")
        return

    def get_branches() -> list:
        r = requests.get(f"{BASE}/branches", timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return r.json()

    def get_latest_commit_for_file(branch: str, path: str) -> dict | None:
        url = f"{BASE}/commits"
        params = {"sha": branch, "path": path, "per_page": 1}
        r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        commits = r.json()
        return commits[0] if commits else None

    try:
        branches = get_branches()
        latest = None

        for b in branches:  # pyrefly: ignore
            branch_name = b["name"]
            commit = get_latest_commit_for_file(branch_name, path)
            if not commit:
                continue

            commit_date = commit["commit"]["committer"]["date"]

            if latest is None or commit_date > latest["date"]:
                latest = {
                    "branch": branch_name,
                    "sha": commit["sha"],
                    "date": commit_date,
                    "message": commit["commit"]["message"],
                    "url": commit["html_url"],
                }

        if latest is not None:
            commit_date = datetime.strptime(latest["date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            commit_sha = latest["sha"]

            logging.info(f"Latest commit for {path}: {commit_sha} ({commit_date})")

            if file.exists() and file.stat().st_mtime >= commit_date.timestamp():
                logging.info(f"{file} is already up to date.")
                file.touch()
                return

            contents_url = f"https://api.github.com/repos/TypQxQ/Sigenergy-Local-Modbus/contents/{path}"
            params = {"ref": commit_sha}
            file_response = requests.get(contents_url, headers={"Accept": "application/vnd.github.v3.raw"}, params=params, timeout=HTTP_TIMEOUT)
            file_response.raise_for_status()

            with file.open("wb") as f:
                f.write(file_response.content)

            logging.info(f"{file} downloaded from commit {commit_sha}")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status == 429:
            logging.warning(f"GitHub rate limit hit (HTTP 429); proceeding with cached {file.name} file.")
        else:
            logging.error(f"HTTP {status} error downloading {file.name}: {e}")
        # Ensure the file exists so the deferred import in compare_sensor_instances() doesn't fail.
        file.touch()


async def main() -> None:
    """Entry point: download latest TypQxQ definitions then regenerate both MD files."""
    download_latest("custom_components/sigen/modbusregisterdefinitions.py")

    await sensor_index()
    await compare_sensor_instances()


if __name__ == "__main__":
    os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
    logging.getLogger().setLevel(logging.INFO)
    asyncio.run(main())
