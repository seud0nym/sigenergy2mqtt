import logging
from datetime import UTC, timedelta, timezone
from typing import cast

from pymodbus.exceptions import ModbusException

from sigenergy2mqtt.common import ConsumptionMethod, FirmwareVersion, HybridInverter, ProtocolApplies, ProtocolVersion, PVInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import PID, PSS, ACCharger, DCCharger, Inverter, PowerPlant
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.base import SanityCheckException
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PACKBCUCount
from sigenergy2mqtt.sensors.pid_read_only import PIDSerialNumber
from sigenergy2mqtt.sensors.plant_ess_preheating_read_write import ESSPreHeatingEnable
from sigenergy2mqtt.sensors.plant_read_only import SystemTimeZone
from sigenergy2mqtt.sensors.plant_read_write import GridCodeLVRT, IndependentPhasePowerControl
from sigenergy2mqtt.sensors.pss_read_only import PSSSerialNumber

from .modbus_helpers import get_modbus_url, get_state
from .protocol_probe import probe_optional_interface, probe_protocol

logger = logging.getLogger(__name__)


async def make_ac_charger(plant_index: int, device_address: int, modbus_client: ModbusClient, plant: PowerPlant, sequence_number: int | None = None, total_count: int | None = None) -> ACCharger:
    """Create an AC charger device and link it to the parent plant.

    Side effects: performs async device initialisation reads and sets
    ``via_device`` to the plant unique ID for topology/discovery metadata.
    """
    charger = await ACCharger.create(
        plant_index=plant_index,
        device_address=device_address,
        protocol_version=plant.protocol_version,
        modbus_client=modbus_client,
        sequence_number=sequence_number,
        total_count=total_count,
    )
    charger.via_device = plant.unique_id
    return charger


async def make_dc_charger(
    plant_index: int, device_address: int, modbus_client: ModbusClient, plant: PowerPlant, inverter_unique_id: str, sequence_number: int | None = None, total_count: int | None = None
) -> DCCharger:
    """Create a DC charger device and associate it with its inverter.

    Side effects: performs async device initialisation and sets ``via_device``
    to the owning inverter unique ID.
    """
    charger = await DCCharger.create(
        plant_index=plant_index,
        device_address=device_address,
        protocol_version=plant.protocol_version,
        modbus_client=modbus_client,
        sequence_number=sequence_number,
        total_count=total_count,
    )
    charger.via_device = inverter_unique_id
    return charger


async def make_pid(
    plant_index: int, device_address: int, modbus_client: ModbusClient, plant: PowerPlant, seen_serial_numbers: set[str], sequence_number: int | None = None, total_count: int | None = None
) -> PID | None:
    """Create a PID device and link it to the parent plant.

    ``seen_serial_numbers`` is updated in-place to guard
    against duplicate serial numbers.

    Side effects: performs async device initialisation reads and sets
    ``via_device`` to the plant unique ID for topology/discovery metadata.
    """
    pid = await PID.create(
        plant_index=plant_index,
        device_address=device_address,
        protocol_version=plant.protocol_version,
        modbus_client=modbus_client,
    )
    pid.via_device = plant.unique_id

    sn = await get_state(pid.get_sensor(PIDSerialNumber), modbus_client, "PID")
    if sn in seen_serial_numbers:
        logger.info(f"PID {sn} has already been detected - ignoring (idx={plant_index} id={device_address})")
        return None
    seen_serial_numbers.add(str(sn))

    return pid


async def make_plant_and_inverter(plant_index: int, modbus_client: ModbusClient, device_address: int, plant: PowerPlant | None, seen_serial_numbers: set[str]) -> tuple[Inverter | None, PowerPlant | None]:
    """Create an Inverter and, on first call, a PowerPlant.

    ``seen_serial_numbers`` is updated in-place to guard
    against duplicate serial numbers.
    """
    sn = await get_state(InverterSerialNumber(plant_index, device_address), modbus_client, "inverter")
    if sn in seen_serial_numbers:
        logger.info(f"Inverter {sn} has already been detected - ignoring (idx={plant_index} id={device_address})")
        return None, None

    mdl = await get_state(InverterModel(plant_index, device_address), modbus_client, "inverter")
    if mdl is None:
        raise ValueError(f"Inverter {sn} Model ID cannot be None (idx={plant_index} id={device_address})")

    batteries = cast(int, await get_state(PACKBCUCount(plant_index, device_address), modbus_client, "plant", default_value=0))
    if batteries == 0:
        device_type = PVInverter()
        logger.debug(f"Inverter {sn} has no batteries - assuming PVInverter (idx={plant_index} id={device_address})")
    else:
        device_type = HybridInverter()
        logger.debug(f"Inverter {sn} has {batteries} batter{'y' if batteries == 1 else 'ies'} - assuming HybridInverter (idx={plant_index} id={device_address})")

    device_type.has_independent_phase_power_control_interface = await probe_optional_interface(modbus_client, IndependentPhasePowerControl.ADDRESS, "Independent Phase Control Interface")
    device_type.has_grid_code_interface = await probe_optional_interface(modbus_client, GridCodeLVRT.ADDRESS, "Grid Code Interface")

    try:
        sys_tz_offset = await get_state(SystemTimeZone(plant_index), modbus_client, "plant", raw=True)
        if sys_tz_offset is None or not isinstance(sys_tz_offset, int):
            logger.warning(f"Plant {plant_index} System Timezone offset not available - defaulting to UTC")
            sys_tz_offset = 0
        if sys_tz_offset > 1440 or sys_tz_offset < -1440:
            logger.warning(f"Plant {plant_index} System Timezone offset {sys_tz_offset} is out of range - defaulting to UTC")
            sys_tz_offset = 0
        tz = timezone(timedelta(minutes=cast(int, sys_tz_offset)))
    except (ModbusException, TimeoutError, OSError, SanityCheckException) as e:
        logger.error(f"Plant {plant_index} System Timezone offset read failed - defaulting to UTC ({e})")
        tz = UTC

    if plant is None:
        firmware = FirmwareVersion(cast(str, await get_state(InverterFirmwareVersion(plant_index, device_address), modbus_client, "plant/inverter")))
        protocol = await probe_protocol(modbus_client)
        if protocol == ProtocolVersion.V2_8 and firmware.service_pack >= 114:
            logger.debug(f"IGNORED {get_modbus_url(modbus_client)} detection of ProtocolVersion V{protocol.value} because Firmware {firmware} supports V2.9 features")
            protocol = ProtocolVersion.V2_9
        logger.info(f"Interrogated {get_modbus_url(modbus_client)} and found Sigenergy Modbus Protocol V{protocol.value} ({ProtocolApplies(protocol)})")

        if protocol < ProtocolVersion.V2_8 and active_config.consumption != ConsumptionMethod.CALCULATED:
            logger.warning(f"Resetting consumption configuration to {ConsumptionMethod.CALCULATED.name} because {active_config.consumption.name} is not supported on Modbus ProtocolVersion V{protocol.value}")
            active_config.consumption = ConsumptionMethod.CALCULATED

        ot = await get_state(OutputType(plant_index, device_address), modbus_client, "plant/inverter", raw=True)
        if ot is None:
            raise ValueError(f"Inverter {sn} OutputType cannot be None — cannot create PowerPlant (idx={plant_index} id={device_address})")

        pre_heating = await get_state(ESSPreHeatingEnable(plant_index), modbus_client, "plant/inverter")

        plant = await PowerPlant.create(plant_index, device_type, firmware, protocol, tz, cast(int, ot), pre_heating is not None, modbus_client)
    else:
        protocol = plant.protocol_version

    inverter = await Inverter.create(plant_index, device_address, device_type, protocol, tz, modbus_client)
    inverter.via_device = plant.unique_id

    if sn is not None:
        seen_serial_numbers.add(str(sn))

    return inverter, plant


async def make_pss(
    plant_index: int, modbus_client: ModbusClient, device_address: int, plant: PowerPlant, seen_serial_numbers: set[str], sequence_number: int | None = None, total_count: int | None = None
) -> PSS | None:
    """Create a PSS device and link it to the parent plant.

    ``seen_serial_numbers`` is updated in-place to guard
    against duplicate serial numbers.

    Side effects: performs async device initialisation reads and sets
    ``via_device`` to the plant unique ID for topology/discovery metadata.
    """
    pss = await PSS.create(
        plant_index=plant_index,
        device_address=device_address,
        protocol_version=plant.protocol_version,
        modbus_client=modbus_client,
    )
    pss.via_device = plant.unique_id

    sn = await get_state(pss.get_sensor(PSSSerialNumber), modbus_client, "PSS")
    if sn in seen_serial_numbers:
        logger.info(f"PSS {sn} has already been detected - ignoring (idx={plant_index} id={device_address})")
        return None
    seen_serial_numbers.add(str(sn))

    return pss
