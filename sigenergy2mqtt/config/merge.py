"""
Modbus list merge and override helpers.

All functions are pure (no I/O) and operate on plain dicts or ModbusConfig
objects, making them straightforward to unit-test in isolation.
"""

from __future__ import annotations

from typing import Any, Final

from sigenergy2mqtt.config.models.modbus import ModbusConfig

# Env-var keys that are propagated to ALL devices (including auto-discovered ones)
PROPAGATABLE_MODBUS_KEYS: Final = frozenset(
    {
        "log_level",
        "no_remote_ems",
        "read_only",
        "read_write",
        "write_only",
        "scan_interval_low",
        "scan_interval_medium",
        "scan_interval_high",
        "scan_interval_realtime",
    }
)


def merge_modbus_by_host_port(
    base: list[dict[str, Any]],     # discovery devices
    overlay: list[dict[str, Any]],  # YAML-configured devices
) -> list[dict[str, Any]]:
    """
    Merge discovery and YAML-config modbus lists.

    For each YAML entry:
    - Blank host acts as a wildcard matching the first discovery device with the same port.
    - A named host matches an exact discovery device (host + port).
    - No match → kept as a standalone entry.

    YAML config wins over discovery for all keys it provides.
    Discovery contributes device IDs (inverters, ac-chargers, dc-chargers) and host when the
    YAML entry had a blank host wildcard.
    """
    disc_map: dict[str, dict[str, Any]] = {}
    for entry in base:
        key = f"{entry.get('host', '')}:{entry.get('port', 502)}"
        disc_map[key] = dict(entry)

    result: dict[str, dict[str, Any]] = {}

    for entry in overlay:
        host = entry.get("host", "")
        port = entry.get("port", 502)

        if not host:
            matched_key = next(
                (k for k, d in disc_map.items() if d.get("port", 502) == port),
                None,
            )
            if matched_key:
                disc = disc_map.pop(matched_key)
                merged = {**disc, **{k: v for k, v in entry.items() if v or v == 0}}
                merged["host"] = disc["host"]
                result[f"{merged['host']}:{port}"] = merged
            else:
                result[f":{port}"] = dict(entry)
        else:
            key = f"{host}:{port}"
            if key in disc_map:
                disc = disc_map.pop(key)
                merged = dict(disc)
                merged.update(
                    {
                        k: v
                        for k, v in entry.items()
                        if k not in ("inverters", "ac-chargers", "dc-chargers", "ac_chargers", "dc_chargers")
                        or v
                    }
                )
                result[key] = merged
            else:
                result[key] = dict(entry)

    for key, disc in disc_map.items():
        if key not in result:
            result[key] = disc

    return list(result.values())


def _flatten_modbus(device: ModbusConfig) -> dict[str, Any]:
    """Dump a ModbusConfig back to a flat dict suitable for re-construction."""
    base = device.model_dump(by_alias=False)
    regs = base.pop("registers", {})
    si   = base.pop("scan_interval", {})
    base.update({f"no_{k}" if k == "remote_ems" else k: v for k, v in regs.items()})
    base.update({f"scan_interval_{k}": v for k, v in si.items()})
    return base


def apply_modbus_env_override(
    modbus_list: list[ModbusConfig],
    override: dict[str, Any],
) -> list[ModbusConfig]:
    """
    Apply a flat env-var override dict to one modbus entry.

    Targets the entry whose host matches SIGENERGY2MQTT_MODBUS_HOST, or index 0.
    If the list is empty and a host is set, bootstraps a new entry from the override.
    """
    if not override:
        return modbus_list

    target_host = override.get("host")

    if not modbus_list:
        return [ModbusConfig(**override)]

    idx = 0
    if target_host:
        for i, m in enumerate(modbus_list):
            if m.host == target_host:
                idx = i
                break

    base = _flatten_modbus(modbus_list[idx])
    base.update(override)

    result = list(modbus_list)
    result[idx] = ModbusConfig(**base)
    return result


def propagate_to_all_devices(
    modbus_list: list[ModbusConfig],
    override: dict[str, Any],
) -> list[ModbusConfig]:
    """Apply propagatable env-var keys (log level, register access, scan intervals) to every device."""
    propagatable = {k: v for k, v in override.items() if k in PROPAGATABLE_MODBUS_KEYS}
    if not propagatable:
        return modbus_list

    result: list[ModbusConfig] = []
    for device in modbus_list:
        base = _flatten_modbus(device)
        base.update(propagatable)
        result.append(ModbusConfig(**base))
    return result
