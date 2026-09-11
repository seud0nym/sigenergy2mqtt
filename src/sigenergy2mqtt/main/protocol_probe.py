import logging

from pymodbus.exceptions import ModbusException

from sigenergy2mqtt.common import Constants, InputType, ProtocolVersion
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.plant_read_only import (
    PlantBatterySoH,
    PlantPVTotalGenerationToday,
    ThirdPartyPVPower,
    TotalLoadDailyConsumption,
    TotalLoadPower,
)

from .modbus_helpers import get_modbus_url, read_registers

logger = logging.getLogger(__name__)


async def probe_protocol(modbus_client: ModbusClient) -> ProtocolVersion:
    """Interrogate the plant to determine the highest supported Modbus protocol version.

    Registers are probed in descending version order; the first successful read
    determines the protocol.  Falls back to V1.8 if none respond.
    """
    # Tuples of (register, count, protocol_version) — must be input registers
    # unique to each version, listed from newest to oldest.
    candidates = [
        (PlantPVTotalGenerationToday.ADDRESS, 2, ProtocolVersion.V2_9),
        (TotalLoadPower.ADDRESS, 2, ProtocolVersion.V2_8),
        (ThirdPartyPVPower.ADDRESS, 2, ProtocolVersion.V2_7),
        (TotalLoadDailyConsumption.ADDRESS, 2, ProtocolVersion.V2_6),
        (PlantBatterySoH.ADDRESS, 1, ProtocolVersion.V2_5),
    ]
    for register, count, version in candidates:
        logger.debug(f"READING {get_modbus_url(modbus_client)} to probe V{version.value} register {register} ({count=} device_id={Constants.PLANT_DEVICE_ADDRESS})")
        try:
            rr = await read_registers(modbus_client, register, count=count, device_id=Constants.PLANT_DEVICE_ADDRESS, input_type=InputType.INPUT)
            if rr.isError():
                logger.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} {count=} device_id={Constants.PLANT_DEVICE_ADDRESS} -> {rr.exception_code=}")
            else:
                logger.debug(f"SUCCESS {get_modbus_url(modbus_client)} {register=} {count=} device_id={Constants.PLANT_DEVICE_ADDRESS} -> OK protocol=V{version.value}")
                return version
        except (ModbusException, TimeoutError, OSError, RuntimeError) as e:
            logger.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} {count=} device_id={Constants.PLANT_DEVICE_ADDRESS} -> {e}")

    logger.debug(f"DEFAULT {get_modbus_url(modbus_client)} to Sigenergy Modbus ProtocolVersion V1.8")
    return ProtocolVersion.V1_8


async def probe_optional_interface(modbus_client: ModbusClient, register: int, interface_name: str) -> bool:
    """Return True if the device responds successfully to a holding-register read."""
    try:
        rr = await read_registers(modbus_client, register, count=1, device_id=Constants.PLANT_DEVICE_ADDRESS, input_type=InputType.HOLDING)
        if rr.isError():
            logger.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} count=1 device_id={Constants.PLANT_DEVICE_ADDRESS} -> {rr.exception_code=} : NO {interface_name}")
            return False
        logger.debug(f"SUCCESS {get_modbus_url(modbus_client)} {register=} count=1 device_id={Constants.PLANT_DEVICE_ADDRESS} -> HAS {interface_name}")
        return True
    except (TimeoutError, ModbusException) as e:
        logger.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} count=1 device_id={Constants.PLANT_DEVICE_ADDRESS} -> {e} : NO {interface_name}")
        return False
