import importlib
import logging
import re
import socket


def is_valid_ipv4(ip):
    try:
        socket.inet_pton(socket.AF_INET, ip)
        return True
    except socket.error:
        return False


def is_valid_ipv6(ip):
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except socket.error:
        return False


def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def check_bool(value, source):
    if isinstance(value, str) and value.lower() in ("true", "1", "yes", "on", "y", "false", "0", "no", "off", "n"):
        return True if value.lower() in ("true", "1", "yes", "on", "y") else False
    if isinstance(value, bool):
        return value
    else:
        raise ValueError(f"{source} must be a either true or false")


def check_host(value, source):
    if is_valid_hostname(value) or is_valid_ipv4(value) or is_valid_ipv6(value):
        return value
    else:
        raise ValueError(f"{source} does not appear to be a valid IP address or hostname")


def check_int(value, source, min: int = None, max: int = None, allow_none: bool = False):
    if allow_none and value is None:
        return value
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise ValueError(f"{source} must be a integer")
        if min is not None and value < min:
            raise ValueError(f"{source} must be a integer greater than or equal to {min}")
        if max is not None and value > max:
            raise ValueError(f"{source} must be a integer less than or equal to {max}")
        return value
    elif isinstance(value, int):
        if min is not None and value < min:
            raise ValueError(f"{source} must be a integer greater than or equal to {min}")
        if max is not None and value > max:
            raise ValueError(f"{source} must be a integer less than or equal to {max}")
        return value
    else:
        raise ValueError(f"{source} must be a integer")


def check_int_list(value, source):
    if value is None or (isinstance(value, list) and (len(value) == 0 or all(isinstance(item, int) for item in value))):
        return value
    else:
        raise ValueError(f"{source} must be null, an empty list, or a list integers")


def check_log_level(value, source):
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


def check_module(value, source):
    module = importlib.import_module(f"sigenergy2mqtt.devices.smartport.{value}")
    if getattr(module, "SmartPort"):
        return value


def check_port(value, source):
    return check_int(value, source, min=1, max=65535)


def check_string(value, source, allow_none: bool = True, allow_empty: bool = True, hex_chars_only: bool = False, starts_with: str = None):
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
        return value
    else:
        raise ValueError(f"{source} must be a valid string")
