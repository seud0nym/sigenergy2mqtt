import hashlib
import json
import logging
from collections.abc import Mapping
from typing import Any

import paho.mqtt.client as paho_mqtt
import requests
from paho.mqtt import MQTTException
from paho.mqtt.enums import CallbackAPIVersion
from pymodbus.exceptions import ModbusException

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.persistence import Category, state_store
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, ModbusSensorMixin, WriteOnlySensorMixin

from .modbus_helpers import read_registers

logger = logging.getLogger(__name__)


async def _validate_modbus_connections() -> None:
    """Verify that each configured Modbus endpoint accepts a TCP connection.

    Opens a short-lived client for every configured host/port, attempts to
    connect, validates the connected state, logs success, and then closes the
    socket. No register reads or writes are performed.
    """
    for index, modbus in enumerate(active_config.modbus):
        if not modbus.host:
            logger.warning(f"Unable to validate Modbus connection for device #{index}, host is not set")
        else:
            client = ModbusClient(modbus.host, port=modbus.port, timeout=modbus.timeout, retries=modbus.retries)
            try:
                await client.connect()
                if not client.connected:
                    raise ConnectionError(f"Unable to connect to modbus://{modbus.host}:{modbus.port}")
                logger.info(f"Validated Modbus connection to modbus://{modbus.host}:{modbus.port} (device #{index})")
            finally:
                client.close()


def _validate_mqtt_connection(show_credentials: bool) -> None:
    """Validate MQTT broker reachability and authentication only.

    Establishes a temporary MQTT session using the configured transport/TLS and
    optional credentials, waits for a successful CONNACK, then disconnects.

    Args:
        show_credentials: When ``True``, include raw configured credentials in
            log output for troubleshooting.
    """
    client_id = f"{active_config.mqtt.client_id_prefix}_validate"
    client = paho_mqtt.Client(CallbackAPIVersion.VERSION2, client_id=client_id, protocol=paho_mqtt.MQTTv311, transport=active_config.mqtt.transport)

    if active_config.mqtt.tls:
        import ssl

        ssl_context = ssl.create_default_context()
        if active_config.mqtt.tls_insecure:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(ssl_context)

    url = f"mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}"
    try:
        if active_config.mqtt.anonymous:
            logger.info(f"Validating MQTT connection to {url} anonymously")
        else:
            if show_credentials:
                logger.info(f"Validating MQTT connection to {url} with username={active_config.mqtt.username!r} password={active_config.mqtt.password!r}")
            else:
                logger.info(f"Validating MQTT connection to {url} with username={active_config.mqtt.username!r} password='[REDACTED]'")
            client.username_pw_set(active_config.mqtt.username, active_config.mqtt.password)

        client.connect(active_config.mqtt.broker, port=active_config.mqtt.port, keepalive=active_config.mqtt.keepalive)

        connected = False
        for _ in range(10):
            rc = client.loop(timeout=1.0)
            if client.is_connected():
                connected = True
                break
            if rc not in (paho_mqtt.MQTT_ERR_SUCCESS, paho_mqtt.MQTT_ERR_NO_CONN):
                raise ConnectionError(f"MQTT broker connection failed with rc={rc}")

        if not connected:
            raise TimeoutError("Timed out waiting for MQTT CONNACK")

        logger.info(f"Validated MQTT connection/authentication to {url}")
    finally:
        try:
            client.disconnect()
            client.loop(timeout=0.1)
        except (OSError, MQTTException) as exc:
            logger.warning(f"Error during MQTT disconnect: {exc}")


def _validate_influxdb_connection(show_credentials: bool) -> None:
    """Validate InfluxDB connectivity/authentication via read-only HTTP calls.

    For v2 config (token+org), performs a GET against the buckets endpoint.
    For v1 config (username+password), performs a read-only query endpoint
    request. No write endpoint is called.

    Args:
        show_credentials: When ``True``, include raw configured credentials in
            log output for troubleshooting.
    """
    if not active_config.influxdb.enabled:
        return

    base = f"http://{active_config.influxdb.host}:{active_config.influxdb.port}"
    timeout = max(active_config.influxdb.write_timeout, 5.0)

    if active_config.influxdb.token and active_config.influxdb.org:
        headers = {"Authorization": f"Token {active_config.influxdb.token}"}
        if show_credentials:
            logger.info(f"Validating InfluxDB v2 credentials for {base}: token={active_config.influxdb.token!r} org={active_config.influxdb.org!r}")
        else:
            logger.info(f"Validating InfluxDB v2 credentials for {base}: token='[REDACTED]' org={active_config.influxdb.org!r}")
        response = requests.get(f"{base}/api/v2/buckets", params={"org": active_config.influxdb.org, "limit": 1}, headers=headers, timeout=timeout)
    else:
        auth = (active_config.influxdb.username, active_config.influxdb.password)
        if show_credentials:
            logger.info(f"Validating InfluxDB v1 credentials for {base}: username={active_config.influxdb.username!r} password={active_config.influxdb.password!r}")
        else:
            logger.info(f"Validating InfluxDB v1 credentials for {base}: username={active_config.influxdb.username!r} password='[REDACTED]'")
        response = requests.get(f"{base}/query", params={"q": "SHOW DATABASES"}, auth=auth, timeout=timeout)

    response.raise_for_status()
    logger.info(f"Validated InfluxDB connection/authentication to {base}")


def _validate_pvoutput_connection(show_credentials: bool) -> None:
    """Validate PVOutput endpoint reachability and API authentication.

    Calls PVOutput's system-info API with configured API key/system ID and
    requires a successful HTTP response. No upload API endpoint is used.

    When ``pvoutput.testing`` is enabled, this probe is skipped to match
    runtime behaviour, which intentionally avoids outbound PVOutput requests
    in testing mode.

    Args:
        show_credentials: When ``True``, include raw configured credentials in
            log output for troubleshooting.
    """
    if not active_config.pvoutput.enabled:
        return

    if active_config.pvoutput.testing:
        logger.info("Skipping PVOutput connection/authentication probe because pvoutput.testing is enabled")
        return

    headers = {
        "X-Pvoutput-Apikey": active_config.pvoutput.api_key,
        "X-Pvoutput-SystemId": active_config.pvoutput.system_id,
        "X-Rate-Limit": "1",
    }
    if show_credentials:
        logger.info(f"Validating PVOutput credentials with api_key={active_config.pvoutput.api_key!r} system_id={active_config.pvoutput.system_id!r}")
    else:
        logger.info(f"Validating PVOutput credentials with api_key='[REDACTED]' system_id={active_config.pvoutput.system_id!r}")

    response = requests.get("https://pvoutput.org/service/r2/getsystem.jsp?donations=1", headers=headers, timeout=10)
    response.raise_for_status()
    logger.info("Validated PVOutput connection/authentication")


async def validate_connections(show_credentials: bool = False) -> None:
    """Run all configured connection/authentication checks for ``--validate``.

    Executes Modbus, MQTT, InfluxDB, and PVOutput validation checks in
    sequence. Intended for one-shot startup validation mode, not steady-state
    runtime.

    Args:
        show_credentials: When ``True``, validation logs include raw
            credentials where applicable.
    """
    await _validate_modbus_connections()
    _validate_mqtt_connection(show_credentials)
    _validate_influxdb_connection(show_credentials)
    _validate_pvoutput_connection(show_credentials)


_PUBLISHABLE_SENSOR_VALIDATION_CACHE_VERSION = 1


def _validation_hash(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _current_modbus_config_hash() -> str:
    return _validation_hash([device.model_dump(mode="json", by_alias=True) for device in active_config.modbus])


def _inverter_firmware_payload(inverter_firmware_versions: Mapping[int, str] | None) -> dict[str, str]:
    return {str(address): str(firmware) for address, firmware in sorted((inverter_firmware_versions or {}).items())}


def _validation_cache_key(device: Device) -> str:
    return f"publishable-sensor-validation.{_validation_hash(device.unique_id)}.json"


def _validation_sensor_lookup(device: Device) -> dict[str, Any]:
    sensors: dict[str, Any] = {}
    for sensor in device.get_all_sensors(search_children=True).values():
        candidates = sensor.alarms if isinstance(sensor, AlarmCombinedSensor) else [sensor]
        for candidate in candidates:
            if isinstance(candidate, ModbusSensorMixin):
                sensors[candidate.unique_id] = candidate
    return sensors


def _log_illegal_data_address(sensor: Any) -> None:
    logger.debug(f"{sensor.log_identity} not supported on this device/firmware: ILLEGAL DATA ADDRESS {sensor.address} (count={sensor.count} type={sensor.input_type} protocol=V{sensor.protocol_version.value})")


def _is_valid_validation_cache_payload(value: str) -> bool:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return False

    return (
        isinstance(payload, dict)
        and payload.get("cache_version") == _PUBLISHABLE_SENSOR_VALIDATION_CACHE_VERSION
        and isinstance(payload.get("inverter_firmware_versions"), dict)
        and isinstance(payload.get("inverter_firmware_hash"), str)
        and isinstance(payload.get("modbus_config_hash"), str)
        and isinstance(payload.get("illegal_sensor_unique_ids"), list)
        and all(isinstance(sensor_id, str) for sensor_id in payload["illegal_sensor_unique_ids"])
    )


async def validate_publishable_sensors(modbus_client: ModbusClient, device: Device, inverter_firmware_versions: Mapping[int, str] | None = None) -> None:
    """Validate all publishable sensors for illegal data addresses.

    Scans all publishable ModbusSensorMixin sensors that are not WriteOnlySensors and
    have not been previously probed (state_count == 0), then marks those returning
    Modbus 0x02 ILLEGAL_DATA_ADDRESS as unpublishable before scan groups are created.

    Physical scan results are cached per device and reused on later startups while both
    the active Modbus configuration and the full plant inverter firmware set are
    unchanged. The firmware set is supplied by setup_devices from inverter ``hw``
    attributes only; non-inverter device software/hardware attributes are ignored.

    Args:
        modbus_client: Modbus client for reads
        device: Device to validate (and children recursively)
        inverter_firmware_versions: Firmware versions for all created inverters in the
            plant, keyed by inverter Modbus device address.
    """
    if active_config.clean:
        return

    sensors_to_test = [s for s in device.get_all_sensors(search_children=True).values() if isinstance(s, ModbusSensorMixin) and not isinstance(s, WriteOnlySensorMixin) and s.publishable and s.state_count == 0]
    if not sensors_to_test:
        return

    firmware_versions = _inverter_firmware_payload(inverter_firmware_versions)
    firmware_hash = _validation_hash(firmware_versions)
    modbus_config_hash = _current_modbus_config_hash()
    cache_key = _validation_cache_key(device)
    cached = await state_store.load(Category.CONFIG, cache_key, validator=_is_valid_validation_cache_payload)
    if cached is None:
        logger.debug(f"{device.log_identity} ILLEGAL DATA ADDRESS errors cache not found ({cache_key=})")
    else:
        payload = json.loads(cached)
        if payload["inverter_firmware_hash"] == firmware_hash:
            if payload["modbus_config_hash"] == modbus_config_hash:
                cached_illegal_sensor_unique_ids = payload["illegal_sensor_unique_ids"]
                logger.debug(f"{device.log_identity} Applying {len(cached_illegal_sensor_unique_ids)} sensor{'s' if len(cached_illegal_sensor_unique_ids) != 1 else ''} ILLEGAL DATA ADDRESS errors from cache")
                sensor_lookup = _validation_sensor_lookup(device)
                for sensor_unique_id in cached_illegal_sensor_unique_ids:
                    sensor = sensor_lookup.get(sensor_unique_id)
                    if sensor is not None:
                        sensor.publishable = False
                        _log_illegal_data_address(sensor)
                return
            else:
                logger.debug(f"{device.log_identity} ILLEGAL DATA ADDRESS errors cache modbus config hash mismatch (cached={payload['modbus_config_hash']} current={modbus_config_hash})")
        else:
            logger.debug(f"{device.log_identity} ILLEGAL DATA ADDRESS errors cache inverter firmware hash mismatch (cached={payload['inverter_firmware_hash']} current={firmware_hash})")

    logger.debug(f"{device.log_identity} Validating {len(sensors_to_test)} sensor{'s' if len(sensors_to_test) != 1 else ''} addresses")

    illegal_sensor_unique_ids: list[str] = []
    scan_completed = True

    # Test each sensor for illegal address exceptions
    for sensor in sensors_to_test:
        for s in sensor.alarms if isinstance(sensor, AlarmCombinedSensor) else [sensor]:
            try:
                rr = await read_registers(modbus_client, s.address, s.count, s.device_address, s.input_type)
                if rr and rr.isError() and rr.exception_code == 0x02:
                    _log_illegal_data_address(s)
                    s.publishable = False
                    illegal_sensor_unique_ids.append(s.unique_id)
            except (ModbusException, TimeoutError, OSError, ConnectionError) as e:
                scan_completed = False
                # Log but don't suppress sensor on transient errors (only explicit 0x02)
                if "0x02 ILLEGAL DATA ADDRESS" in str(e):
                    logger.debug(f"{s.log_identity}: Validation detected illegal address: {e}")
                else:
                    logger.debug(f"{s.log_identity}: Validation read failed: {e}")

    if not scan_completed:
        logger.debug(f"{device.log_identity} Validation scan not cached because one or more sensor reads failed")
        return

    payload = {
        "cache_version": _PUBLISHABLE_SENSOR_VALIDATION_CACHE_VERSION,
        "inverter_firmware_versions": firmware_versions,
        "inverter_firmware_hash": firmware_hash,
        "modbus_config_hash": modbus_config_hash,
        "illegal_sensor_unique_ids": sorted(set(illegal_sensor_unique_ids)),
    }
    await state_store.save(Category.CONFIG, cache_key, json.dumps(payload, sort_keys=True))
