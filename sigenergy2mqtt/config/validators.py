"""
Shared field validators and sensor-override validation.
All functions are pure — no I/O, no model coupling.
"""

from __future__ import annotations

import logging
from typing import Any

from sigenergy2mqtt.common import TariffType, TimePeriod
from sigenergy2mqtt.config.validation import check_bool, check_float, check_int, check_string, check_time

# ---------------------------------------------------------------------------
# Log level
# ---------------------------------------------------------------------------


def validate_log_level(v: str | int) -> int:
    """Accept a level name (e.g. "WARNING") or int and return the int level."""
    if isinstance(v, int):
        return v
    level = logging.getLevelNamesMapping().get(v.upper())
    if level is None:
        valid = ", ".join(logging.getLevelNamesMapping().keys())
        raise ValueError(f"invalid log level {v!r}, must be one of: {valid}")
    return level


# ---------------------------------------------------------------------------
# Sensor overrides
# ---------------------------------------------------------------------------

_SENSOR_OVERRIDE_VALIDATORS: dict[str, Any] = {
    "debug-logging": lambda v, ctx: check_bool(v, ctx),
    "gain": lambda v, ctx: check_int(v, ctx, allow_none=True, min=1),
    "icon": lambda v, ctx: check_string(v, ctx, allow_none=False, starts_with="mdi:"),
    "max-failures": lambda v, ctx: check_int(v, ctx, allow_none=True, min=1),
    "max-failures-retry-interval": lambda v, ctx: check_int(v, ctx, allow_none=False, min=0),
    "precision": lambda v, ctx: check_int(v, ctx, allow_none=False, min=0, max=6),
    "publishable": lambda v, ctx: check_bool(v, ctx),
    "publish-raw": lambda v, ctx: check_bool(v, ctx),
    "scan-interval": lambda v, ctx: check_int(v, ctx, allow_none=False, min=1),
    "sanity-check-max-value": lambda v, ctx: check_float(v, ctx, allow_none=False),
    "sanity-check-min-value": lambda v, ctx: check_float(v, ctx, allow_none=False),
    "sanity-check-delta": lambda v, ctx: check_bool(v, ctx),
    "unit-of-measurement": lambda v, ctx: check_string(v, ctx, allow_none=False),
}


def validate_sensor_overrides(raw: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Validate every sensor override entry."""
    result: dict[str, dict[str, Any]] = {}
    for sensor, settings in raw.items():
        validated: dict[str, Any] = {}
        for prop, val in settings.items():
            ctx = f"Error processing configuration sensor-overrides: {sensor}.{prop} = {val} -"
            if prop not in _SENSOR_OVERRIDE_VALIDATORS:
                raise ValueError(f"Error processing configuration sensor-overrides: {sensor}.{prop} = {val} - property is not known or not overridable")
            validated[prop] = _SENSOR_OVERRIDE_VALIDATORS[prop](val, ctx)
        result[sensor] = validated
    return result


# ---------------------------------------------------------------------------
# Time-period parsing (used by PvOutputConfig)
# ---------------------------------------------------------------------------


def parse_time_periods(value: list, tariff_index: int) -> list[TimePeriod]:
    """Parse a raw list of period dicts into list[TimePeriod]."""

    if not isinstance(value, list):
        raise ValueError("pvoutput time-periods.periods configuration element must contain a list of time period definitions")
    periods: list[TimePeriod] = []
    for i, period in enumerate(value):
        if not isinstance(period, dict):
            raise ValueError(f"pvoutput.time-periods[{tariff_index}].periods[{i}] must be a time period definition")
        if not all(k in period for k in ("type", "start", "end")):
            raise ValueError(f"pvoutput.time-periods[{tariff_index}].periods[{i}] must contain 'type', 'start', and 'end' elements")
        ptype = TariffType(
            check_string(
                period["type"],
                f"pvoutput.time-periods[{tariff_index}].periods[{i}].type",
                "off-peak",
                "peak",
                "shoulder",
                "high-shoulder",
                allow_empty=False,
                allow_none=False,
            )
        )
        start = check_time(period["start"], f"pvoutput.time-periods[{tariff_index}].periods[{i}].start")
        end = check_time(period["end"], f"pvoutput.time-periods[{tariff_index}].periods[{i}].end")
        days: list[str] = []
        if "days" in period:
            if not isinstance(period["days"], list):
                raise ValueError(f"pvoutput.time-periods[{tariff_index}].periods[{i}].days must be a list of days")
            for day in period["days"]:
                validated = check_string(
                    day.capitalize(),
                    f"pvoutput.time-periods[{tariff_index}].periods[{i}].days",
                    "Mon",
                    "Tue",
                    "Wed",
                    "Thu",
                    "Fri",
                    "Sat",
                    "Sun",
                    "Weekdays",
                    "Weekends",
                    "All",
                )
                if validated:
                    days.append(validated)
        else:
            days.append("All")
        periods.append(TimePeriod(type=ptype, start=start, end=end, days=days))
    return periods
