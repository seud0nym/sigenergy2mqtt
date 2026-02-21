"""
Validation helpers for configuration values loaded from YAML files and environment variables.

Each ``check_*`` function accepts a raw value (which may be a string when sourced from an
environment variable, or a native Python type when sourced from YAML), validates it, coerces
it to the appropriate type, and returns the result.  On failure every function raises
``ValueError`` with a human-readable message that includes ``source`` — the name of the
configuration key being validated — so that error messages can be surfaced directly to the
user without additional wrapping.

The ``is_valid_*`` helpers are lower-level predicates used internally by :func:`check_host`
but exposed publicly for callers that only need a boolean test.
"""

import importlib
import logging
import re
import socket
from datetime import date, datetime, time
from typing import Any, Literal, overload

PATTERN_24H = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def is_valid_ipv4(ip: str) -> bool:
    """Return ``True`` if *ip* is a syntactically valid IPv4 address."""
    try:
        socket.inet_pton(socket.AF_INET, ip)
        return True
    except socket.error:
        return False


def is_valid_ipv6(ip: str) -> bool:
    """Return ``True`` if *ip* is a syntactically valid IPv6 address."""
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except socket.error:
        return False


def is_valid_hostname(hostname: str) -> bool:
    """Return ``True`` if *hostname* is a syntactically valid DNS hostname.

    Validation follows RFC 1123: each label must be 1–63 characters, consist only of
    ASCII letters, digits, and hyphens, and must not start or end with a hyphen.  The
    overall hostname must not exceed 255 characters.  A single trailing dot (indicating
    an absolute name) is accepted and stripped before validation.
    """
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def check_bool(value: str | bool, source: str) -> bool:
    """Validate and coerce *value* to a ``bool``.

    Accepted truthy strings (case-insensitive): ``true``, ``1``, ``yes``, ``on``, ``y``.
    Accepted falsy strings (case-insensitive): ``false``, ``0``, ``no``, ``off``, ``n``.
    Native ``bool`` values are returned as-is.

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If *value* is not a recognised boolean string or native bool.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "1", "yes", "on", "y", "false", "0", "no", "off", "n"):
        return value.lower() in ("true", "1", "yes", "on", "y")
    raise ValueError(f"{source} must be either true or false")


def check_date(value: str | date, source: str) -> date:
    """Validate and coerce *value* to a ``datetime.date``.

    Native ``date`` instances are returned as-is.  Strings must be in ``YYYY-MM-DD``
    format.

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If *value* is a string that does not match ``YYYY-MM-DD``.
    """
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{source} must be in the format YYYY-MM-DD and not null")


@overload
def check_float(value: str | float | int | None, source: str, min: float | None = None, max: float | None = None, *, allow_none: Literal[False]) -> float: ...
@overload
def check_float(value: str | float | int | None, source: str, min: float | None = None, max: float | None = None, *, allow_none: Literal[True]) -> float | None: ...
@overload
def check_float(value: str | float | int | None, source: str, min: float | None = None, max: float | None = None, allow_none: bool = ...) -> float | None: ...
def check_float(value: str | float | int | None, source: str, min: float | None = None, max: float | None = None, allow_none: bool = False) -> float | None:
    """Validate and coerce *value* to a ``float``.

    Accepts native ``float``, ``int``, or a string that can be parsed by ``float()``.

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.
        min: If given, the value must be greater than or equal to this bound.
        max: If given, the value must be less than or equal to this bound.
        allow_none: If ``True``, a ``None`` *value* is accepted and returned as ``None``.
            When ``False`` (default) a ``None`` value raises ``ValueError``.

    Returns:
        The validated ``float``, or ``None`` if *value* is ``None`` and *allow_none* is
        ``True``.

    Raises:
        ValueError: If *value* cannot be coerced to a float, is ``None`` when
            *allow_none* is ``False``, or falls outside the specified bounds.
    """
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{source} must be a float and not null")
    if isinstance(value, (int, float, str)):
        try:
            result = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"{source} must be a float")
        if min is not None and result < min:
            raise ValueError(f"{source} must be a float greater than or equal to {min}")
        if max is not None and result > max:
            raise ValueError(f"{source} must be a float less than or equal to {max}")
        return result
    raise ValueError(f"{source} must be a float")


def check_host(value: str, source: str) -> str:
    """Validate that *value* is a valid hostname or IP address.

    Accepts IPv4 addresses, IPv6 addresses, and DNS hostnames as validated by
    :func:`is_valid_ipv4`, :func:`is_valid_ipv6`, and :func:`is_valid_hostname`
    respectively.  The value is returned unchanged if valid.

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If *value* does not appear to be a valid host.
    """
    if is_valid_hostname(value) or is_valid_ipv4(value) or is_valid_ipv6(value):
        return value
    raise ValueError(f"{source} does not appear to be a valid IP address or hostname")


@overload
def check_int(value: str | int | None, source: str, min: int | None = None, max: int | None = None, allowed: int | None = None, *, allow_none: Literal[False]) -> int: ...
@overload
def check_int(value: str | int | None, source: str, min: int | None = None, max: int | None = None, allowed: int | None = None, *, allow_none: Literal[True]) -> int | None: ...
@overload
def check_int(value: str | int | None, source: str, min: int | None = None, max: int | None = None, allowed: int | None = None, allow_none: bool = ...) -> int | None: ...
def check_int(value: str | int | None, source: str, min: int | None = None, max: int | None = None, allowed: int | None = None, allow_none: bool = False) -> int | None:
    """Validate and coerce *value* to an ``int``.

    Accepts a native ``int`` or a string that can be parsed by ``int()``.

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.
        min: If given, the value must be greater than or equal to this bound, unless
            *allowed* is set and matches.
        max: If given, the value must be less than or equal to this bound, unless
            *allowed* is set and matches.
        allowed: A single integer that is unconditionally accepted regardless of *min*
            and *max*.  Useful for sentinel values such as ``-1``.
        allow_none: If ``True``, a ``None`` *value* is accepted and returned as ``None``.
            When ``False`` (default) a ``None`` value raises ``ValueError``.

    Returns:
        The validated ``int``, or ``None`` if *value* is ``None`` and *allow_none* is
        ``True``.

    Raises:
        ValueError: If *value* cannot be coerced to an integer, is ``None`` when
            *allow_none* is ``False``, or falls outside the specified bounds.
    """
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{source} must be an integer and not null")
    try:
        result = value if isinstance(value, int) else int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{source} must be an integer")
    if allowed is not None and result == allowed:
        return result
    if min is not None and result < min:
        raise ValueError(f"{source} must be an integer greater than or equal to {min}")
    if max is not None and result > max:
        raise ValueError(f"{source} must be an integer less than or equal to {max}")
    return result


def check_int_list(value: str | list[int] | None, source: str) -> list[int]:
    """Validate and coerce *value* to a list of integers.

    Accepts ``None`` (returns an empty list), a native ``list[int]``, or a
    comma-separated string of integers (whitespace around each item is stripped).

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If a comma-separated string contains non-integer tokens, or if a
            list is provided whose items are not all integers.
    """
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return [int(i.strip()) for i in value.split(",")]
        except ValueError:
            raise ValueError(f"{source} must be null, an empty list, or a list of integers separated by commas")
    if isinstance(value, list):
        if all(isinstance(item, int) for item in value):
            return value
    raise ValueError(f"{source} must be null, an empty list, or a list of integers separated by commas")


def check_log_level(value: str | int, source: str) -> int:
    """Validate *value* as a Python logging level and return its integer form.

    Accepts the standard level names (case-insensitive) ``DEBUG``, ``INFO``,
    ``WARNING``, ``ERROR``, and ``CRITICAL``, as well as their corresponding integer
    constants from the ``logging`` module.

    Args:
        value: The raw value to validate — either a level name string or an integer.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If *value* is not a recognised logging level name or integer.
    """
    _names = logging.getLevelNamesMapping()
    if isinstance(value, str):
        level = _names.get(value.upper())
        if level is not None:
            return level
    elif isinstance(value, int) and value in _names.values():
        return value
    raise ValueError(f"{source} must be one of DEBUG, INFO, WARNING, ERROR or CRITICAL")


def check_module(value: str, source: str) -> str:
    """Validate that *value* names an importable SmartPort module.

    Attempts to import ``sigenergy2mqtt.devices.smartport.<value>`` and verifies that
    it exposes a ``SmartPort`` class.  The module name is returned unchanged if valid.

    Args:
        value: The module name to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If the module cannot be imported or does not contain a
            ``SmartPort`` class.
    """
    try:
        module = importlib.import_module(f"sigenergy2mqtt.devices.smartport.{value}")
        if hasattr(module, "SmartPort"):
            return value
        raise ValueError(f"{source} must be a valid module that contains a SmartPort class")
    except (AttributeError, ImportError):
        raise ValueError(f"{source} must be a valid module")


def check_port(value: str | int, source: str) -> int:
    """Validate and coerce *value* to a valid TCP/UDP port number (1–65535).

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If *value* is not an integer in the range 1–65535.
    """
    return check_int(value, source, min=1, max=65535, allow_none=False)


@overload
def check_string(value: Any, source: str, *valid_values: str, allow_none: Literal[False], allow_empty: bool = ..., hex_chars_only: bool = ..., starts_with: str | None = ...) -> str: ...
@overload
def check_string(value: Any, source: str, *valid_values: str, allow_none: Literal[True], allow_empty: bool = ..., hex_chars_only: bool = ..., starts_with: str | None = ...) -> str | None: ...
@overload
def check_string(value: Any, source: str, *valid_values: str, allow_none: bool = ..., allow_empty: bool = ..., hex_chars_only: bool = ..., starts_with: str | None = ...) -> str | None: ...
def check_string(value: Any, source: str, *valid_values: str, allow_none: bool = True, allow_empty: bool = True, hex_chars_only: bool = False, starts_with: str | None = None) -> str | None:
    """Validate *value* as a string, with optional constraints.

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.
        *valid_values: If provided, the string must be one of these values.
        allow_none: If ``True`` (default), ``None`` is accepted and returned as ``None``.
            When ``False``, a ``None`` value raises ``ValueError``.
        allow_empty: If ``True`` (default), empty and whitespace-only strings are
            accepted.  When ``False``, they raise ``ValueError``.
        hex_chars_only: If ``True``, the string must be a valid hexadecimal value
            (i.e. parseable by ``int(value, 16)``).
        starts_with: If given, the string must begin with this prefix.

    Returns:
        The validated string, or ``None`` if *value* is ``None`` and *allow_none* is
        ``True``.

    Raises:
        ValueError: If any constraint is violated.
    """
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{source} must be a valid string and not null")
    if not isinstance(value, str):
        raise ValueError(f"{source} must be a valid string")
    if not allow_empty and (value == "" or value.isspace()):
        raise ValueError(f"{source} must be a valid string and not empty")
    if hex_chars_only:
        try:
            int(value, 16)
        except ValueError:
            raise ValueError(f"{source} must only contain hexadecimal characters")
    if starts_with is not None and not value.startswith(starts_with):
        raise ValueError(f"{source} must start with '{starts_with}'")
    if valid_values and value not in valid_values:
        raise ValueError(f"{source} must be one of {', '.join(valid_values)}")
    return value


def check_string_list(value: str | list[str] | None, source: str) -> list[str]:
    """Validate and coerce *value* to a list of strings.

    Accepts ``None`` (returns an empty list), a native ``list[str]``, or a
    comma-separated string (whitespace around each item is stripped).

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If a list is provided whose items are not all strings.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [i.strip() for i in value.split(",")]
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return value
    raise ValueError(f"{source} must be null, an empty list, or a list of strings separated by commas")


def check_time(value: str | time, source: str) -> time:
    """Validate and coerce *value* to a ``datetime.time``.

    Native ``time`` instances are returned as-is.  Strings must be in ``HH:MM``
    24-hour format.  The special string ``"24:00"`` is accepted as a convenience
    end-of-day sentinel and is mapped to ``time(23, 59, 59, 999999)``.

    Args:
        value: The raw value to validate.
        source: The configuration key name, used in error messages.

    Raises:
        ValueError: If *value* is a string that does not match ``HH:MM``.
    """
    if isinstance(value, time):
        return value
    try:
        if value == "24:00":
            return time(23, 59, 59, 999999)
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise ValueError(f"{source} must be in the format HH:MM and not null")
