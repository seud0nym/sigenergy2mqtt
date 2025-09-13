from pathlib import Path
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.sensors.base import Sensor, WriteOnlySensor
from test import get_sensor_instances, cancel_sensor_futures


async def sensor_index():
    def metrics_topics():
        f.write("| Metric | Interval | Unit | State Topic|\n")
        f.write("|--------|---------:|------|-------------|\n")
        metrics = MetricsService._discovery["cmps"]
        for metric in sorted(metrics.values(), key=lambda x: x["name"]):
            f.write(f"| {metric['name']} | 1 | {metric['unit_of_measurement'] if 'unit_of_measurement' in metric else ''} | {metric['state_topic']} |\n")

    def published_topics(device: str):
        for key in [key for key, value in sorted(mqtt_sensors.items(), key=lambda x: x[1]["name"]) if "state_topic" in value and not isinstance(value, WriteOnlySensor)]:
            sensor: Sensor = mqtt_sensors[key]
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device and sensor.publishable:
                sensor_name = sensor.__class__.__name__
                attributes = sensor.get_attributes()
                f.write("<details>\n")
                f.write("<summary>\n")
                if hasattr(sensor, "string_number"):
                    f.write(f"PV String {sensor.string_number} ")
                f.write(f"{sensor['name']}\n")
                f.write("</summary>\n")
                f.write("<table>\n")
                f.write(f"<tr><td>Sensor Class</td><td>{sensor.__class__.__name__}</td></tr>\n")
                if hasattr(sensor, "scan_interval"):
                    f.write(f"<tr><td>Scan Interval</td><td>{sensor.scan_interval}s</td></tr>\n")
                if sensor.unit:
                    f.write(f"<tr><td>Unit of Measurement</td><td>{sensor.unit}</td></tr>\n")
                if sensor._gain:
                    f.write(f"<tr><td>Gain</td><td>{sensor.gain}</td></tr>\n")
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
                f.write("</details>\n")

    def subscribed_topics(device):
        for key in [key for key, value in sorted(mqtt_sensors.items(), key=lambda x: x[1]["name"]) if "command_topic" in value]:
            sensor = mqtt_sensors[key]
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device:
                f.write("<details>\n")
                f.write("<summary>\n")
                f.write(f"{sensor['name']}")
                if sensor["name"] == "Power":
                    f.write(" On/Off")
                f.write("\n")
                f.write("</summary>\n")
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
                f.write("</details>\n")

    readme = Path("sigenergy2mqtt/sensors/README.md")
    assert readme.exists(), f"README.md file not found at {readme}"
    hass_sensors = await get_sensor_instances(hass=True)
    mqtt_sensors = await get_sensor_instances(hass=False)
    with readme.open("w") as f:
        f.write("# MQTT Topics\n")
        f.write("\nTopics prefixed with `homeassistant/` are used when the `home-assistant` configuration `enabled` option in the configuration file,\n")
        f.write("or the `SIGENERGY2MQTT_HASS_ENABLED` environment variable, are set to true, or the `--hass-enabled` command line option is specified\n")
        f.write("Otherwise, the topics prefixed with `sigenergy2mqtt/` are used.\n")
        f.write(
            "\nYou can also enable the `sigenergy2mqtt/` topics when Home Assistant discovery is enabled by setting the `SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS` environment variable to true,\n"
        )
        f.write("or by specifying the `--hass-use-simplified-topics` command line option.\n")
        f.write("\nThe number after the `sigen_` prefix represents the host index from the configuration file, starting from 0. (Home Assistant configuration may change the `sigen` topic prefix.)")
        f.write("\nInverter, AC Charger and DC Charger indexes use the device ID as specified in the configuration file.\n")
        f.write("\nDefault Scan Intervals are shown in seconds, but may be overridden via configuration. Intervals for derived sensors are dependent on the source sensors.\n")
        f.write("\n## Published Topics\n")
        f.write("\n### Plant\n")
        published_topics("PowerPlant")
        f.write("\n#### Grid Sensor\n")
        published_topics("GridSensor")
        f.write("\n#### Smart-Port (Enphase Envoy only)\n")
        published_topics("SmartPort")
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
        logging.info(f"{readme} successfully updated")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sensor_index())
    cancel_sensor_futures()
    loop.close()
