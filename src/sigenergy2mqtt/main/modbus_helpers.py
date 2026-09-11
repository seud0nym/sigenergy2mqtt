import logging
from typing import Any

from paho.mqtt import MQTTException
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ModbusPDU

from sigenergy2mqtt.common import InputType
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.base import SanityCheckException

logger = logging.getLogger(__name__)


def get_modbus_url(modbus_client: ModbusClient) -> str:
    """Return a stable ``modbus://host:port`` identifier for logs.

    Falls back to ``modbus://unknown`` if the client does not expose connection
    parameters yet.
    """
    if modbus_client and hasattr(modbus_client, "comm_params"):
        return f"modbus://{modbus_client.comm_params.host}:{modbus_client.comm_params.port}"
    return "modbus://unknown"


async def get_state(sensor: Any, modbus_client: ModbusClient, device: str, default_value: float | str | None = None, raw: bool = False) -> int | float | str | None:
    """Read a sensor state for bootstrap/probing while tolerating read failures.

    Returns the sensor value when successful, otherwise ``default_value``.

    Side effects:

    - Performs a Modbus network read through ``sensor.get_state``.
    - Emits debug logs for successful reads and caught failures.
    """
    try:
        state = await sensor.get_state(raw=raw, republish=True, modbus_client=modbus_client, skip_failure_logging=True)  # Use republish=True to use last read, if one exists
        logger.debug(
            f"READING {get_modbus_url(modbus_client)} acquired {sensor.__class__.__name__} {'raw ' if raw else ''}{state=} to initialise {device} (idx={sensor.plant_index} id={sensor.device_address} addr={sensor.address})"
        )
    except (ValueError, TypeError, RuntimeError, OSError, ModbusException, MQTTException, SanityCheckException) as e:
        state = default_value
        logger.debug(
            f"FAILURE {get_modbus_url(modbus_client)} acquiring {sensor.__class__.__name__} to initialise {device} (idx={sensor.plant_index} id={sensor.device_address} addr={sensor.address}) -> {e} (returning {default_value=})"
        )
    return state


async def read_registers(modbus_client: ModbusClient, register: int, count: int, device_id: int, input_type: InputType) -> ModbusPDU:
    """Read holding or input registers from a target device.

    ``input_type`` selects the Modbus function code. Raises ``ValueError`` if
    ``modbus_client`` is missing or the input type is unsupported.
    """
    if modbus_client is None:
        raise ValueError("modbus_client cannot be None")
    if input_type == InputType.HOLDING:
        return await modbus_client.read_holding_registers(register, count=count, device_id=device_id)
    if input_type == InputType.INPUT:
        return await modbus_client.read_input_registers(register, count=count, device_id=device_id)
    raise ValueError(f"Unknown input type '{input_type}'")
