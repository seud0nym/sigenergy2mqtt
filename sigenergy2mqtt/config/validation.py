import importlib
import logging
import re
import socket
from datetime import date, datetime, time
from typing import Any

PATTERN_24H = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def is_valid_ipv4(ip: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, ip)
        return True
    except socket.error:
        return False


def is_valid_ipv6(ip: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except socket.error:
        return False


def is_valid_hostname(hostname: str) -> bool:
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def check_bool(value: str | bool, source: str) -> bool:
    if isinstance(value, str) and value.lower() in ("true", "1", "yes", "on", "y", "false", "0", "no", "off", "n"):
        return True if value.lower() in ("true", "1", "yes", "on", "y") else False
    if isinstance(value, bool):
        return value
    else:
        raise ValueError(f"{source} must be a either true or false")


def check_date(value: str | date, source: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{source} must be in the format YYYY-MM-DD and not null")


def check_float(value: str | float | int | None, source: str, min: float | None = None, max: float | None = None, allow_none: bool = False) -> float | None:
    if allow_none and value is None:
        return value
    if isinstance(value, (int, str)):
        try:
            result = float(value)
        except ValueError:
            raise ValueError(f"{source} must be a float")
        if min is not None and result < min:
            raise ValueError(f"{source} must be a float greater than or equal to {min}")
        if max is not None and result > max:
            raise ValueError(f"{source} must be a float less than or equal to {max}")
        return result
    elif isinstance(value, float):
        if min is not None and value < min:
            raise ValueError(f"{source} must be a float greater than or equal to {min}")
        if max is not None and value > max:
            raise ValueError(f"{source} must be a float less than or equal to {max}")
        return value
    else:
        raise ValueError(f"{source} must be a float")


def check_host(value: str, source: str) -> str:
    if is_valid_hostname(value) or is_valid_ipv4(value) or is_valid_ipv6(value):
        return value
    else:
        raise ValueError(f"{source} does not appear to be a valid IP address or hostname")


def check_int(value: str | int | None, source: str, min: int | None = None, max: int | None = None, allowed: int | None = None, allow_none: bool = False) -> int | None:
    if value is None:
        if allow_none:
            return value
        else:
            raise ValueError(f"{source} must be an integer and not null")
    try:
        result = value if isinstance(value, int) else int(value)
    except ValueError:
        raise ValueError(f"{source} must be an integer")
    if isinstance(result, int):
        if allowed is not None and value == allowed:
            return result
        if min is not None and result < min:
            raise ValueError(f"{source} must be an integer greater than or equal to {min}")
        if max is not None and result > max:
            raise ValueError(f"{source} must be an integer less than or equal to {max}")
        return result
    else:
        raise ValueError(f"{source} must be an integer")


def check_int_list(value: str | list[int] | None, source: str) -> list[int]:
    int_list: list[int]
    if value is None:
        int_list = []
    elif isinstance(value, str):
        int_list = [int(i) for i in value.split(",")]
    else:
        int_list = value
    if len(int_list) == 0 or all(isinstance(item, int) for item in int_list):
        return int_list
    else:
        raise ValueError(f"{source} must be null, an empty list, or a list integers")


def check_log_level(value: str | int, source: str) -> int:
    if isinstance(value, int) and value in (
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ):
        return value
    elif isinstance(value, str) and value.upper() == "DEBUG":
        return logging.DEBUG
    elif isinstance(value, str) and value.upper() == "INFO":
        return logging.INFO
    elif isinstance(value, str) and value.upper() == "WARNING":
        return logging.WARNING
    elif isinstance(value, str) and value.upper() == "ERROR":
        return logging.ERROR
    elif isinstance(value, str) and value.upper() == "CRITICAL":
        return logging.CRITICAL
    else:
        raise ValueError(f"{source} must be one of DEBUG, INFO, WARNING, ERROR or CRITICAL")


def check_module(value: str, source: str) -> str:
    try:
        module = importlib.import_module(f"sigenergy2mqtt.devices.smartport.{value}")
        if getattr(module, "SmartPort"):
            return value
        else:
            raise ValueError(f"{source} must be a valid module that contains a SmartPort class")
    except ValueError:
        raise ValueError(f"{source} must be a valid module")


def check_port(value: str | int, source: str) -> int:
    port = check_int(value, source, min=1, max=65535)
    if isinstance(port, int):
        return port
    else:
        raise ValueError(f"{source} must be a port number between 1 and 65535")


def check_string(value: Any, source: str, *valid_values: str, allow_none: bool = True, allow_empty: bool = True, hex_chars_only: bool = False, starts_with: str | None = None) -> str | None:
    if value is None:
        if allow_none:
            return value
        else:
            raise ValueError(f"{source} must be a valid string and not null")
    elif isinstance(value, str):
        if not allow_empty and (value == "" or value.isspace()):
            raise ValueError(f"{source} must be a valid string and not empty")
        if hex_chars_only:
            try:
                int(value, 16)
            except ValueError:
                raise ValueError(f"{source} must only contain hexadecimal characters")
        if value is not None and starts_with is not None and not value.startswith(starts_with):
            raise ValueError(f"{source} must start with '{starts_with}")
        if valid_values and value not in valid_values:
            raise ValueError(f"{source} must be one of {', '.join(valid_values)}")
        return value
    else:
        raise ValueError(f"{source} must be a valid string")


def check_time(value: str | time, source: str) -> time:
    if isinstance(value, time):
        return value
    try:
        if value == "24:00" or value == "23:59":
            return time(23, 59, 59, 999999)
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise ValueError(f"{source} must be in the format HH:MM and not null")
