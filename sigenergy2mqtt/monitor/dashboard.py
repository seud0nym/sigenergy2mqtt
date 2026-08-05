"""Extract a compact, dashboard-ready payload from the sigenergy2mqtt
MonitoredSensor state dict.

Design notes
------------
- Device *type* and *id* are read from `sensor.device_name` (e.g.
  "Inverter[plant=0,dev=1]"), not parsed out of the MQTT topic string —
  the topic's own field-name segment is unpredictable per device type,
  but device_name's shape is fixed and reliable.
- Devices are *discovered*, not assumed. A plant with one inverter and no
  chargers produces empty ac_chargers/dc_chargers dicts and a single-entry
  inverters dict; a plant with two inverters and both charger types
  produces exactly that. No config flags needed.
- Only a curated subset of fields is pulled per device type — the ones
  worth a gauge/bar on a dashboard, not all ~80-290 raw sensors per
  device. Add to the *_FIELDS dicts to pull more.
- Fields are split into "live" (changes constantly: power, SoC, temp) and
  "static" (model/serial/firmware) so static values can be nested under a
  "config" key — matching the diagnostics dashboard's existing convention
  where "config" renders dimmed/italic and separated from live metrics.
- Missing sensors are silently skipped (not KeyError'd), since not every
  firmware/hardware combination exposes every field.
"""

from __future__ import annotations

import re
from typing import Any

from sigenergy2mqtt.config import active_config

DEVICE_RE = re.compile(r"^(?P<type>\w+)\[plant=(?P<plant>\d+),dev=(?P<dev>\d+)\]$")

# Maps the device_name "type" token -> the MQTT topic segment used for that
# device type's sensors, e.g. sigen_0_inverter_1_..., sigen_0_dc_charger_1_...
TOPIC_SEGMENT = {
    "Inverter": "inverter",
    "DCCharger": "dc_charger",
    "ACCharger": "ac_charger",
}

# --- Plant-level (single instance, keys have no per-device numeric suffix) ---
PLANT_LIVE_FIELDS = {
    "grid_status": "plant_grid_status",
    "grid_activity": "grid_activity",
    "running_state": "plant_running_state",
    "ems_work_mode": "plant_ems_work_mode",
    "battery_soc": "plant_battery_soc",
    "battery_soh": "plant_battery_soh",
    "battery_power": "plant_battery_power",
    "battery_status": "battery_status",
    "lifetime_charged_energy": "accumulated_charge_energy",
    "lifetime_discharged_energy": "accumulated_discharge_energy",
    "pv_power": "total_pv_power",
    "load_power": "total_load_power",
    "grid_import_power": "grid_sensor_import_power",
    "grid_export_power": "grid_sensor_export_power",
    "daily_pv_energy": "total_daily_pv_energy",
    "daily_charge_energy": "daily_charge_energy",
    "daily_discharge_energy": "daily_discharge_energy",
    "daily_consumed_energy": "daily_consumed_energy",
    "grid_daily_import_energy": "grid_sensor_daily_import_energy",
    "grid_daily_export_energy": "grid_sensor_daily_export_energy",
    "self_consumed_power": "self_consumed_power",
    "daily_self_consumed_energy": "daily_self_consumed_energy",
    "average_cell_temperature": "ess_average_cell_temperature",
    "available_max_charging_capacity": "plant_available_max_charging_capacity",
    "available_max_discharging_capacity": "plant_available_max_discharging_capacity",
    # Alarms are aggregated at plant level rather than per-device — e.g.
    # "general_alarm_5" is the DC-charger-alarm rollup covering every DC
    # charger on the plant (a per-charger sensor doesn't scale/exist), and
    # inverter-level PCS alarms are likewise redundant with general_pcs_alarm
    # here. See INVERTER_LIVE_FIELDS/DC_CHARGER_LIVE_FIELDS notes below.
    "pcs_alarms": "general_pcs_alarm",
    "ess_alarms": "general_alarm_3",
    "gateway_alarms": "general_alarm_4",
    "dc_charger_alarms": "general_alarm_5",
    "alarms": "plant_alarms",
}
PLANT_CONFIG_FIELDS = {
    "rated_energy_capacity": "plant_rated_energy_capacity",
    "max_active_power": "plant_max_active_power",
    "rated_charging_power": "plant_rated_charging_power",
    "rated_discharging_power": "plant_rated_discharging_power",
    "grid_max_export_limit": "plant_grid_max_export_limit",
}

# --- Per-inverter (0..N instances) ---
INVERTER_LIVE_FIELDS = {
    "running_state": "running_state",
    "active_power": "active_power",
    "pv_power": "pv_power",
    "battery_soc": "battery_soc",
    "battery_soh": "battery_soh",
    "temperature": "temperature",
    "min_battery_temperature": "min_battery_temperature",
    "max_battery_temperature": "max_battery_temperature",
    "daily_pv_energy": "daily_pv_energy",
    # pcs_alarm deliberately omitted — it's the same alarm rolled up at
    # plant level as "pcs_alarms" (general_pcs_alarm); showing both would
    # duplicate the same information per-inverter instead of once for the
    # whole plant.
}
INVERTER_CONFIG_FIELDS = {
    "model": "model",
    "serial_number": "serial_number",
    "firmware_version": "firmware_version",
    "rated_active_power": "rated_active_power",
    "rated_battery_capacity": "rated_battery_capacity",
}

# --- Per-DC-charger (0..N instances; absent entirely on most systems) ---
# No per-device alarm field here deliberately — DC charger alarms are only
# available as a single plant-level rollup (general_alarm_5, extracted as
# plant.dc_charger_alarms) covering every DC charger on the plant at once,
# not per-charger. That scales correctly regardless of how many DC chargers
# exist, which a per-device sensor wouldn't.
DC_CHARGER_LIVE_FIELDS = {
    "running_state": "running_state",
    "output_power": "output_power",
    "vehicle_soc": "vehicle_soc",
    "current_charging_capacity": "current_charging_capacity",
}
DC_CHARGER_CONFIG_FIELDS = {
    "rated_charging_power": "rated_charging_power",
    "max_charging_power_limit": "max_charging_power_limit",
}

# --- Per-AC-charger (0..N instances; absent entirely on most systems) ---
AC_CHARGER_LIVE_FIELDS = {
    "running_state": "running_state",
    "charging_power": "charging_power",
    "output_current": "output_current",
    "alarm": "alarm",
}
AC_CHARGER_CONFIG_FIELDS = {
    "rated_power": "rated_power",
    "rated_current": "rated_current",
}


def _extract(state: dict[str, Any], topic_prefix: str, fields: dict[str, str]) -> dict[str, Any]:
    """Pull `fields` (short_name -> topic suffix) off `topic_prefix`, skipping
    any sensor that isn't present in this system's state dict.

    Each field comes back as {"value": ..., "unit": ...} rather than a bare
    scalar — sigenergy2mqtt already knows the correct unit per sensor (from
    the Modbus/HA integration), so carrying it through beats trying to
    re-infer units from field-name suffixes on the dashboard side.
    """
    return {short: {"value": sensor.last_state, "unit": sensor.unit} for short, suffix in fields.items() if (sensor := state.get(f"{topic_prefix}_{suffix}/state")) is not None}


def extract_dashboard_state(state: dict[str, Any]) -> dict[str, Any]:
    """Build a compact, dashboard-ready payload from the raw MonitoredSensor
    state dict. Devices absent from `state` simply produce empty dicts/lists
    rather than errors — safe for single-inverter, no-charger systems and
    multi-inverter, dual-charger systems alike.
    """
    # Discover which plant(s)/inverter(s)/charger(s) actually exist by
    # reading device_name off every sensor, rather than assuming dev=1.
    devices = {(m["type"], m["plant"], m["dev"]) for sensor in state.values() if (m := DEVICE_RE.match(sensor.device_name))}

    plant_ids = sorted({plant for typ, plant, _ in devices if typ == "PowerPlant"})
    plant_id = plant_ids[0] if plant_ids else "0"  # sigenergy2mqtt currently supports a single plant
    plant_prefix = f"sigenergy2mqtt/{active_config.home_assistant.entity_id_prefix}_{plant_id}"

    plant = _extract(state, plant_prefix, PLANT_LIVE_FIELDS)
    plant["config"] = _extract(state, plant_prefix, PLANT_CONFIG_FIELDS)
    # Battery-less systems either never publish these topics at all (so
    # battery_soc is simply absent from `plant`), or in some firmware
    # versions publish the sensor with a literal None value. Either way,
    # this single check gives the dashboard one clear signal to hide the
    # battery gauges/pills rather than rendering an empty/zero gauge.
    plant["has_battery"] = plant.get("battery_soc", {}).get("value") is not None

    inverters = {}
    dc_chargers = {}
    ac_chargers = {}
    for typ, dev_plant_id, dev in sorted(devices, key=lambda d: (d[0], int(d[2]))):
        if typ not in TOPIC_SEGMENT:
            continue  # PowerPlant already handled above
        prefix = f"sigenergy2mqtt/{active_config.home_assistant.entity_id_prefix}_{dev_plant_id}_{TOPIC_SEGMENT[typ]}_{dev}"
        if typ == "Inverter":
            entry = _extract(state, prefix, INVERTER_LIVE_FIELDS)
            entry["config"] = _extract(state, prefix, INVERTER_CONFIG_FIELDS)
            inverters[dev] = entry
        elif typ == "DCCharger":
            entry = _extract(state, prefix, DC_CHARGER_LIVE_FIELDS)
            entry["config"] = _extract(state, prefix, DC_CHARGER_CONFIG_FIELDS)
            dc_chargers[dev] = entry
        elif typ == "ACCharger":
            entry = _extract(state, prefix, AC_CHARGER_LIVE_FIELDS)
            entry["config"] = _extract(state, prefix, AC_CHARGER_CONFIG_FIELDS)
            ac_chargers[dev] = entry

    return {
        "plant": plant,
        "inverters": inverters,
        "dc_chargers": dc_chargers,
        "ac_chargers": ac_chargers,
    }
