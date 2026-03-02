import asyncio
import logging
from asyncio import sleep

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient

from .client import MqttClient
from .handler import MqttHandler

__all__ = ["MqttHandler", "mqtt_setup"]

_MAX_CONNECT_ATTEMPTS: int = 3


def _build_broker_url() -> str:
    """Construct the broker URL string from active config for use in log messages."""
    return f"mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}"


async def _connect_with_retry(mqtt_client: MqttClient, client_id: str) -> None:
    """Attempt to connect the given MQTT client to the broker, retrying up to
    ``_MAX_CONNECT_ATTEMPTS`` times on failure.

    Args:
        mqtt_client: The :class:`MqttClient` instance to connect.
        client_id:   The MQTT client ID, used only for log messages.

    Raises:
        Exception: Re-raises the last connection exception once
            ``_MAX_CONNECT_ATTEMPTS`` is exhausted.
    """
    broker_url = _build_broker_url()

    for attempt in range(1, _MAX_CONNECT_ATTEMPTS + 1):
        try:
            mqtt_client.connect(
                active_config.mqtt.broker,
                port=active_config.mqtt.port,
                keepalive=active_config.mqtt.keepalive,
            )
            mqtt_client.loop_start()
            logging.info(f"Connected to {broker_url} as Client ID '{client_id}' (keepalive={active_config.mqtt.keepalive}s)")
            return
        except Exception as e:
            if attempt < _MAX_CONNECT_ATTEMPTS:
                logging.warning(f"Error connecting to {broker_url}: {repr(e)} (attempt {attempt}/{_MAX_CONNECT_ATTEMPTS}) - Retrying in {active_config.mqtt.retry_delay}s")
                await sleep(active_config.mqtt.retry_delay)
            else:
                logging.critical(f"Failed to connect to {broker_url} after {_MAX_CONNECT_ATTEMPTS} attempts: {repr(e)}")
                raise


async def mqtt_setup(
    mqtt_client_id: str,
    modbus_client: ModbusClient | None,
    loop: asyncio.AbstractEventLoop,
) -> tuple[MqttClient, MqttHandler]:
    """Create, configure, and connect an MQTT client/handler pair.

    Instantiates an :class:`MqttHandler` and :class:`MqttClient`, applies
    authentication from active config, and establishes a broker connection
    (with retries).  The caller is responsible for managing the returned
    :class:`MqttClient` lifecycle after this point.

    Args:
        mqtt_client_id: A non-empty string used as the MQTT client identifier.
            Must be unique per broker session.
        modbus_client:  An optional :class:`ModbusClient` passed through to
            the :class:`MqttHandler` for Modbus read/write operations.
        loop:           The asyncio event loop the handler will schedule
            callbacks on.  Must not be ``None``.

    Returns:
        A ``(MqttClient, MqttHandler)`` tuple.  The client is already
        connected and its internal paho loop is running.

    Raises:
        ValueError:  If ``mqtt_client_id`` is empty or whitespace-only.
        ValueError:  If ``loop`` is ``None``.
        Exception:   If the broker is unreachable after all retry attempts.
    """
    if not mqtt_client_id or mqtt_client_id.isspace():
        raise ValueError("mqtt_client_id must not be None or an empty string")
    if loop is None:
        raise ValueError("loop must not be None")

    broker_url = _build_broker_url()

    logging.debug(f"Creating MQTT Client ID {mqtt_client_id} for {broker_url} over {active_config.mqtt.transport}")

    mqtt_handler = MqttHandler(mqtt_client_id, modbus_client, loop)
    mqtt_client = MqttClient(
        client_id=mqtt_client_id,
        userdata=mqtt_handler,
        transport=active_config.mqtt.transport,
        tls=active_config.mqtt.tls,
        tls_insecure=active_config.mqtt.tls_insecure,
    )

    if active_config.mqtt.anonymous:
        logging.debug(f"MQTT Client ID {mqtt_client_id} connecting to {broker_url} anonymously")
    else:
        logging.debug(f"MQTT Client ID {mqtt_client_id} connecting to {broker_url} with username {active_config.mqtt.username}")
        mqtt_client.username_pw_set(active_config.mqtt.username, active_config.mqtt.password)

    await _connect_with_retry(mqtt_client, mqtt_client_id)

    return mqtt_client, mqtt_handler
