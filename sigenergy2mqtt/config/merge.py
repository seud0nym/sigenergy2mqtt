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


def _normalize_device_ids(ids: list[int] | int | None) -> list[int]:
    """Normalize a device ID value to a list of ints."""
    if ids is None:
        return []
    if isinstance(ids, int):
        return [ids]
    return list(ids)


def _union_device_ids(base_ids: list[int] | int | None, overlay_ids: list[int] | int | None) -> list[int]:
    """Merge two device ID lists, preserving order with overlay first, then base additions.

    Returns a list where overlay IDs come first (preserving their order),
    followed by any base IDs not already present.  Duplicates within a type
    are removed.  Accepts scalar ints or ``None`` in addition to lists.
    """
    base = _normalize_device_ids(base_ids)
    overlay = _normalize_device_ids(overlay_ids)
    seen: set[int] = set()
    result: list[int] = []
    # Overlay (YAML/manual config) IDs take ordering priority
    for did in overlay:
        if did not in seen:
            seen.add(did)
            result.append(did)
    # Then add any discovered IDs not already present
    for did in base:
        if did not in seen:
            seen.add(did)
            result.append(did)
    return result


_DEVICE_ID_KEYS = ("inverters", "ac-chargers", "dc-chargers")
_DEVICE_ID_KEYS_SNAKE = ("inverters", "ac_chargers", "dc_chargers")


def _validate_device_id_uniqueness(merged: dict[str, Any]) -> None:
    """Ensure device IDs are unique across all device types within a single host entry.

    Raises ValueError if a device ID appears under more than one type.
    """
    all_ids: dict[int, str] = {}
    for key in sorted(set(_DEVICE_ID_KEYS + _DEVICE_ID_KEYS_SNAKE)):
        ids = _normalize_device_ids(merged.get(key))
        if not ids:
            continue
        # Normalise key name for error messages
        display_key = key.replace("_", "-")
        for did in ids:
            if did in all_ids:
                raise ValueError(
                    f"Device ID {did} appears in both '{all_ids[did]}' and '{display_key}' "
                    f"for host {merged.get('host', '?')}:{merged.get('port', 502)}. "
                    f"Device IDs must be unique across all device types."
                )
            all_ids[did] = display_key


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

    YAML config wins over discovery for all scalar keys.
    Device IDs (inverters, ac-chargers, dc-chargers) are **unioned** — IDs from YAML
    config are included first, followed by any additional IDs from discovery that are
    not already present.  Device IDs must be unique within their type and across all
    device types for a given host.
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
                # Union device IDs
                for dk in _DEVICE_ID_KEYS:
                    sk = dk.replace("-", "_")
                    base_ids = disc.get(dk, disc.get(sk, []))
                    overlay_ids = entry.get(dk, entry.get(sk, []))
                    if base_ids or overlay_ids:
                        merged[dk] = _union_device_ids(base_ids or [], overlay_ids or [])
                        if sk != dk:
                            merged.pop(sk, None)
                _validate_device_id_uniqueness(merged)
                result[f"{merged['host']}:{port}"] = merged
            else:
                result[f":{port}"] = dict(entry)
        else:
            key = f"{host}:{port}"
            if key in disc_map:
                disc = disc_map.pop(key)
                merged = dict(disc)
                # Merge non-device-ID fields from overlay (YAML wins for scalars)
                merged.update(
                    {
                        k: v
                        for k, v in entry.items()
                        if k not in (*_DEVICE_ID_KEYS, *_DEVICE_ID_KEYS_SNAKE)
                        or v
                    }
                )
                # Union device IDs
                for dk in _DEVICE_ID_KEYS:
                    sk = dk.replace("-", "_")
                    base_ids = disc.get(dk, disc.get(sk, []))
                    overlay_ids = entry.get(dk, entry.get(sk, []))
                    if base_ids or overlay_ids:
                        merged[dk] = _union_device_ids(base_ids or [], overlay_ids or [])
                        if sk != dk:
                            merged.pop(sk, None)
                _validate_device_id_uniqueness(merged)
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
