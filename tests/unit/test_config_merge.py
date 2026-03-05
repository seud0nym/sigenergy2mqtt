import pytest
from typing import Any

from pydantic import ValidationError

from sigenergy2mqtt.config.merge import (
    _flatten_modbus,
    apply_modbus_env_override,
    merge_modbus_by_host_port,
    propagate_to_all_devices,
)
from sigenergy2mqtt.config.models.modbus import ModbusConfig


def test_merge_modbus_by_host_port_blank_host_wildcard() -> None:
    base = [{"inverters": 1, "host": "192.168.1.100", "port": 502}]
    overlay = [{"host": "", "port": 502, "read_only": True}]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 1
    assert result[0] == {
        "inverters": 1,
        "host": "192.168.1.100",
        "port": 502,
        "read_only": True,
    }


def test_merge_modbus_by_host_port_named_host_exact() -> None:
    base = [
        {"inverters": 1, "host": "192.168.1.100", "port": 502},
        {"inverters": 1, "host": "192.168.1.101", "port": 502},
    ]
    overlay = [{"host": "192.168.1.101", "port": 502, "read_only": True}]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 2
    # Base entry kept
    assert {"inverters": 1, "host": "192.168.1.100", "port": 502} in result
    # Exact match merged
    assert {
        "inverters": 1,
        "host": "192.168.1.101",
        "port": 502,
        "read_only": True,
    } in result


def test_merge_modbus_by_host_port_no_match() -> None:
    base = [{"inverters": 1, "host": "192.168.1.100", "port": 502}]
    overlay = [{"host": "192.168.1.102", "port": 502, "read_only": True}]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 2
    assert {"inverters": 1, "host": "192.168.1.100", "port": 502} in result
    assert {"host": "192.168.1.102", "port": 502, "read_only": True} in result


def test_merge_modbus_by_host_port_priority() -> None:
    base = [{"inverters": 1, "host": "192.168.1.100", "port": 502}]
    overlay = [{"host": "192.168.1.100", "port": 502, "inverters": 2}]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 1
    assert result[0] == {"inverters": 2, "host": "192.168.1.100", "port": 502}


def test_merge_modbus_by_host_port_blank_host_no_match() -> None:
    base: list[dict[str, Any]] = []
    overlay = [{"host": "", "port": 502, "read_only": True}]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 1
    assert result[0] == {"host": "", "port": 502, "read_only": True}


def test_merge_modbus_by_host_port_named_host_ignores_empty_device_lists() -> None:
    base = [
        {
            "host": "192.168.1.100",
            "port": 502,
            "inverters": [1],
            "ac-chargers": [7],
            "dc_chargers": [9],
        }
    ]
    overlay = [
        {
            "host": "192.168.1.100",
            "port": 502,
            "inverters": [],
            "ac-chargers": [],
            "dc_chargers": [],
        }
    ]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 1
    assert result[0]["inverters"] == [1]
    assert result[0]["ac-chargers"] == [7]
    assert result[0]["dc_chargers"] == [9]


def test_merge_modbus_by_host_port_named_host_overrides_non_empty_device_lists() -> None:
    base = [{"host": "192.168.1.100", "port": 502, "inverters": [1], "ac_chargers": [2]}]
    overlay = [{"host": "192.168.1.100", "port": 502, "inverters": [3], "ac_chargers": [4]}]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 1
    assert result[0]["inverters"] == [3]
    assert result[0]["ac_chargers"] == [4]


def test_flatten_modbus() -> None:
    config = ModbusConfig(
        host="192.168.1.100",
        port=502,
        registers={"no_remote_ems": True},
        scan_interval={"low": 10},
    )

    flattened = _flatten_modbus(config)

    assert flattened["host"] == "192.168.1.100"
    assert flattened["port"] == 502
    assert flattened["no_remote_ems"] is True
    assert flattened["scan_interval_low"] == 10


def test_apply_modbus_env_override_empty() -> None:
    base = [ModbusConfig(host="192.168.1.100")]
    result = apply_modbus_env_override(base, {})
    assert result == base


def test_apply_modbus_env_override_target_index_0() -> None:
    base = [ModbusConfig(host="192.168.1.100"), ModbusConfig(host="192.168.1.101")]
    override = {"port": 503}

    result = apply_modbus_env_override(base, override)

    assert len(result) == 2
    assert result[0].port == 503
    assert result[1].port == 502


def test_apply_modbus_env_override_target_host() -> None:
    base = [ModbusConfig(host="192.168.1.100"), ModbusConfig(host="192.168.1.101")]
    override = {"host": "192.168.1.101", "port": 503}

    result = apply_modbus_env_override(base, override)

    assert len(result) == 2
    assert result[0].port == 502
    assert result[1].port == 503


def test_apply_modbus_env_override_bootstrap() -> None:
    base: list[ModbusConfig] = []
    override = {"host": "192.168.1.100", "port": 503}

    result = apply_modbus_env_override(base, override)

    assert len(result) == 1
    assert result[0].host == "192.168.1.100"
    assert result[0].port == 503


def test_apply_modbus_env_override_target_host_not_found_uses_first_entry() -> None:
    base = [ModbusConfig(host="192.168.1.100"), ModbusConfig(host="192.168.1.101")]
    override = {"host": "192.168.1.222", "port": 503}

    result = apply_modbus_env_override(base, override)

    assert len(result) == 2
    assert result[0].host == "192.168.1.222"
    assert result[0].port == 503
    assert result[1].host == "192.168.1.101"


def test_propagate_to_all_devices() -> None:
    base = [ModbusConfig(host="192.168.1.100"), ModbusConfig(host="192.168.1.101")]
    override = {"log_level": "DEBUG", "non_propagatable_key": "val"}

    result = propagate_to_all_devices(base, override)

    assert len(result) == 2
    assert result[0].log_level == 10
    assert result[1].log_level == 10


def test_propagate_to_all_devices_empty() -> None:
    base = [ModbusConfig(host="192.168.1.100")]
    override = {"non_propagatable_key": "val"}

    result = propagate_to_all_devices(base, override)

    assert len(result) == 1
    assert result[0].log_level == 30
    # Assuming result is same as base if nothing propagates
    # we don't assert exact equality because it returns the original if not propagatable
    assert result == base


def test_propagate_to_all_devices_updates_registers_and_scan_interval() -> None:
    base = [
        ModbusConfig(host="192.168.1.100", read_only=False, scan_interval_low=5),
        ModbusConfig(host="192.168.1.101", read_only=False, scan_interval_low=6),
    ]
    override = {"read_only": True, "scan_interval_low": 15}

    result = propagate_to_all_devices(base, override)

    assert len(result) == 2
    assert all(device.registers.read_only for device in result)
    assert all(device.scan_interval.low == 15 for device in result)



def test_merge_modbus_by_host_port_blank_host_keeps_zero_values() -> None:
    base = [{"host": "192.168.1.100", "port": 502, "timeout": 1.0}]
    overlay = [{"host": "", "port": 502, "timeout": 0, "retries": 0}]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 1
    assert result[0]["host"] == "192.168.1.100"
    assert result[0]["timeout"] == 0
    assert result[0]["retries"] == 0


def test_merge_modbus_by_host_port_blank_host_multiple_entries_match_distinct_devices() -> None:
    base = [
        {"host": "192.168.1.100", "port": 502, "inverters": [1]},
        {"host": "192.168.1.101", "port": 502, "inverters": [2]},
    ]
    overlay = [
        {"host": "", "port": 502, "read_only": True},
        {"host": "", "port": 502, "read_write": False},
    ]

    result = merge_modbus_by_host_port(base, overlay)

    assert len(result) == 2
    hosts = {entry["host"] for entry in result}
    assert hosts == {"192.168.1.100", "192.168.1.101"}
    assert any(entry.get("read_only") is True for entry in result)
    assert any(entry.get("read_write") is False for entry in result)


def test_apply_modbus_env_override_bootstrap_requires_host() -> None:
    base: list[ModbusConfig] = []

    with pytest.raises(ValidationError, match="modbus entry must have a host"):
        apply_modbus_env_override(base, {"port": 503})


def test_propagate_to_all_devices_empty_list_returns_empty_list() -> None:
    result = propagate_to_all_devices([], {"read_only": True})

    assert result == []
