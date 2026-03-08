"""
modbus_sensors.py - Testing utility for Sigenergy Modbus sensor instances.

Provides a :class:`DummyModbusClient` that simulates Modbus register reads using
pre-populated in-memory data, and :func:`get_sensor_instances` which instantiates
the full sensor graph (plant, inverters, chargers) against that dummy client.

Intended for use in unit and integration tests to verify sensor register mappings,
detect register gaps/overlaps, and confirm all concrete sensor classes are exercised.

Usage (standalone)::

    with _swap_active_config(Config()):
        asyncio.run(get_sensor_instances())
"""

import asyncio
import logging
import os
import sys
from typing import cast

os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.pdu import ModbusPDU

from sigenergy2mqtt.common import HybridInverter, Protocol, ProtocolApplies, PVInverter
from sigenergy2mqtt.config import Config, _swap_active_config, active_config, initialize
from sigenergy2mqtt.devices import ACCharger, DCCharger, Device, Inverter, PowerPlant
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerInputBreaker, ACChargerRatedCurrent, ACChargerRunningState
from sigenergy2mqtt.sensors.ac_charger_read_write import ACChargerStatus
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor, ModbusSensorMixin, Sensor
from sigenergy2mqtt.sensors.inverter_read_only import DCChargerVehicleBatteryVoltage, InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PACKBCUCount, PVStringCount, RatedGridVoltage
from sigenergy2mqtt.sensors.inverter_read_write import DCChargerStatus, InverterStatus, ReservedInverterRemoteEMSDispatch
from sigenergy2mqtt.sensors.plant_read_only import GridCodeRatedFrequency, PlantRatedChargingPower, PlantRatedDischargingPower
from sigenergy2mqtt.sensors.plant_read_write import PlantStatus

initialize()

FIRMWARE_VERSION: str = "V100R001C00SPC112B107G"
INPUT_BREAKER: float = 16.0
OUTPUT_TYPE: int = 2
PACK_BCU_COUNT: int = 3
PV_STRING_COUNT: int = 36
RATED_CHARGING_POWER: float = 12.6
RATED_CURRENT: float = 32.0
RATED_DISCHARGING_POWER: float = 13.68
RATED_FREQUENCY: float = 50.0


class DummyModbusClient(ModbusClientMixin):
    """A simulated Modbus client that serves pre-populated register data from memory.

    Implements the same async read interface as the real Modbus client, returning
    register values constructed from known test constants. Intended solely for use
    in tests; no network connection is made.

    The ``count`` parameter in read methods is intentionally ignored: register values
    are stored and retrieved by start address, with the correct number of registers
    determined at construction time by ``convert_to_registers`` based on each
    sensor's ``data_type``.

    Args:
        model_id: The inverter model string to serve (e.g. ``"SigenStor EC 12.0 TP"``).
        serial_number: The inverter serial number string to serve (e.g. ``"CMU123A45BP678"``).
    """

    def __init__(self, model_id: str, serial_number: str):
        super().__init__()

        rated_charging_power = PlantRatedChargingPower(0)
        rated_discharging_power = PlantRatedDischargingPower(0)
        rated_frequency = GridCodeRatedFrequency(0)

        model = InverterModel(0, 1)
        serial = InverterSerialNumber(0, 1)
        firmware = InverterFirmwareVersion(0, 1)
        pv_strings = PVStringCount(0, 1)
        output_type = OutputType(0, 1)
        pack_bcu_count = PACKBCUCount(0, 1)

        input_breaker = ACChargerInputBreaker(0, 1)
        rated_current = ACChargerRatedCurrent(0, 1)

        self.data = {  # convert_to_registers will create the correct number of registers based on data_type, so we can ignore the count parameter in the read methods
            rated_charging_power.address: self.convert_to_registers(rated_charging_power.state2raw(RATED_CHARGING_POWER), rated_charging_power.data_type),
            rated_discharging_power.address: self.convert_to_registers(rated_discharging_power.state2raw(RATED_DISCHARGING_POWER), rated_discharging_power.data_type),
            rated_frequency.address: self.convert_to_registers(rated_frequency.state2raw(RATED_FREQUENCY), rated_frequency.data_type),
            model.address: self.convert_to_registers(model_id, model.data_type),
            serial.address: self.convert_to_registers(serial_number, serial.data_type),
            firmware.address: self.convert_to_registers(FIRMWARE_VERSION, firmware.data_type),
            pv_strings.address: self.convert_to_registers(pv_strings.state2raw(PV_STRING_COUNT), pv_strings.data_type),
            output_type.address: self.convert_to_registers(output_type.state2raw(OUTPUT_TYPE), output_type.data_type),  # 2 = 3-phase (L1/L2/L3/N)
            pack_bcu_count.address: self.convert_to_registers(pack_bcu_count.state2raw(PACK_BCU_COUNT), pack_bcu_count.data_type),
            input_breaker.address: self.convert_to_registers(input_breaker.state2raw(INPUT_BREAKER), input_breaker.data_type),
            rated_current.address: self.convert_to_registers(rated_current.state2raw(RATED_CURRENT), rated_current.data_type),
        }

    def get_state(self, address: int, device_id: int) -> ModbusPDU:
        """Return the pre-populated register data for the given address.

        Args:
            address: The Modbus register start address to look up.
            device_id: The Modbus device (slave) ID. Accepted but not used, as all
                devices share the same in-memory data store in this dummy client.

        Returns:
            A :class:`ModbusPDU` containing the registers stored at ``address``.

        Raises:
            ValueError: If ``address`` has no entry in the data store, indicating a
                sensor under test is reading a register not covered by this dummy client.
        """
        result = self.data.get(address, None)
        if result is None:
            raise ValueError(f"Unknown address {address}")
        return ModbusPDU(registers=result)

    async def read_holding_registers(self, address: int, count: int, device_id: int, trace: bool = False) -> ModbusPDU:  # noqa: unused arguments required to match real implementation
        """Simulate a holding register read by returning pre-populated data for ``address``."""
        return self.get_state(address, device_id)

    async def read_input_registers(self, address: int, count: int, device_id: int, trace: bool = False) -> ModbusPDU:  # noqa: unused arguments required to match real implementation
        """Simulate an input register read by returning pre-populated data for ``address``."""
        return self.get_state(address, device_id)


async def get_sensor_instances(
    home_assistant_enabled: bool = False,
    plant_index: int = 0,
    hybrid_inverter_device_address: int = 1,
    pv_inverter_device_address: int = 1,
    dc_charger_device_address: int = 1,
    ac_charger_device_address: int = 2,
    firmware_version: str = FIRMWARE_VERSION,
    protocol_version: Protocol | None = None,
    output_type: OutputType = OUTPUT_TYPE,
    concrete_sensor_check: bool = False,
) -> dict[str, Sensor]:
    """Instantiate the full sensor graph and return all sensors keyed by unique ID.

    Creates a :class:`PowerPlant`, two :class:`Inverter` instances (hybrid and PV),
    a :class:`DCCharger`, and an :class:`ACCharger` against :class:`DummyModbusClient`
    instances, then collects every sensor (including derived and alarm sensors) into a
    flat dictionary.

    When ``concrete_sensor_check`` is ``True``, additional validation is performed:

    - Warnings are logged for any gaps between consecutive register addresses that are
      not expected range boundaries.
    - Warnings are logged for any overlapping register assignments.
    - Warnings are logged for any concrete :class:`Sensor` subclass that was discovered
      but never instantiated (excluding ``MetricsSensor`` subclasses, which are internal
      to sigenergy2mqtt and not Sigenergy Modbus sensors).

    **Important — config isolation:** This function mutates ``active_config`` directly.
    Callers are responsible for config isolation using the ``_swap_active_config``
    context manager so that mutations do not leak into other tests or the production
    config. The canonical pattern is::

        with _swap_active_config(Config()):
            sensors = await get_sensor_instances(...)

    Args:
        home_assistant_enabled: Whether to enable Home Assistant output in the config.
            Defaults to ``False``.
        plant_index: Index of the plant entry in ``active_config.modbus`` to configure.
            Defaults to ``0``.
        hybrid_inverter_device_address: Modbus device address for the hybrid inverter.
            Defaults to ``1``.
        pv_inverter_device_address: Modbus device address for the PV inverter.
            Defaults to ``1``.
        dc_charger_device_address: Modbus device address for the DC charger.
            Defaults to ``1``.
        ac_charger_device_address: Modbus device address for the AC charger.
            Defaults to ``2``.
        firmware_version: The firmware version to use when creating inverters.
            Defaults to ``FIRMWARE_VERSION``.
        protocol_version: The :class:`Protocol` version to use when creating devices.
            Defaults to ``max(Protocol)`` (the latest known protocol version).
        output_type: The :class:`OutputType` to use when creating devices.
            Defaults to ``OutputType.THREE_PHASE``.
        concrete_sensor_check: When ``True``, performs register gap, overlap, and
            unused-class validation and logs warnings for any issues found.
            Defaults to ``True``.

    Returns:
        A dictionary mapping each sensor's ``unique_id`` to its :class:`Sensor` instance.
    """
    if protocol_version is None:
        protocol_version = max(Protocol)
    logging.info(f"Sigenergy Modbus Protocol V{protocol_version.value} [{ProtocolApplies(protocol_version)}] ({home_assistant_enabled=})")

    active_config.modbus[plant_index].dc_chargers.append(dc_charger_device_address)
    active_config.modbus[plant_index].ac_chargers.append(ac_charger_device_address)

    active_config.modbus[plant_index].smartport.enabled = True
    active_config.modbus[plant_index].smartport.module.name = "enphase"
    active_config.modbus[plant_index].smartport.module.pv_power = "EnphasePVPower"
    active_config.modbus[plant_index].smartport.module.testing = True

    active_config.home_assistant.enabled = home_assistant_enabled
    active_config.influxdb.enabled = True

    hi_device_type = HybridInverter(has_grid_code_interface=True, has_independent_phase_power_control_interface=True)
    hi_modbus_client = DummyModbusClient("SigenStor EC 12.0 TP", "CMU123A45BP678")
    pv_device_type = PVInverter(has_grid_code_interface=True, has_independent_phase_power_control_interface=True)
    pv_modbus_client = DummyModbusClient("Sigen PV Max 5.0 TP", "CMU876A54BP321")

    plant = await PowerPlant.create(plant_index, hi_device_type, firmware_version, protocol_version, output_type, hi_modbus_client)
    hybrid_inverter = await Inverter.create(plant_index, hybrid_inverter_device_address, hi_device_type, protocol_version, hi_modbus_client)
    pv_inverter = await Inverter.create(plant_index, pv_inverter_device_address, pv_device_type, protocol_version, pv_modbus_client)
    dc_charger = await DCCharger.create(plant_index, dc_charger_device_address, protocol_version)
    ac_charger = await ACCharger.create(plant_index, ac_charger_device_address, protocol_version, hi_modbus_client)

    classes: dict[str, int] = {}
    registers: dict[int, Sensor] = {}
    sensors: dict[str, Sensor] = {}

    def find_concrete_classes(superclass):
        for c in superclass.__subclasses__():
            if len(c.__subclasses__()) == 0:
                classes[c.__name__] = 0
            elif c.__name__ != "MetricsSensor":  # MetricsSensor classes are sigenergy2mqtt internal sensors, and we are only searching for Sigenergy sensors
                find_concrete_classes(c)

    def add_sensor_instance(s):
        key = s.unique_id
        if hasattr(s, "address"):
            if (
                s.address in registers
                and s.device_address == getattr(registers[s.address], "device_address", None)
                and s.__class__.__name__ != registers[s.address].__class__.__name__
                and not (isinstance(s, AlarmSensor) and isinstance(registers[s.address], AlarmCombinedSensor))
                and not (isinstance(s, AlarmCombinedSensor) and isinstance(registers[s.address], AlarmSensor))
            ):
                logging.warning(f"Register {s.address} in {s.__class__.__name__} already defined in {registers[s.address].__class__.__name__}")
            else:
                registers[s.address] = s
        if key not in sensors:
            sensors[key] = s
        elif s.__class__.__name__ != sensors[key].__class__.__name__:
            logging.warning(f"Register {key} in {s.__class__.__name__} already defined in {sensors[key].__class__.__name__}")
        try:
            classes[s.__class__.__name__] += 1
        except KeyError:
            logging.critical(f"Class {s.__class__.__name__} not found in classes???")
            raise
        for d in s.derived_sensors.values():
            add_sensor_instance(d)

    find_concrete_classes(Sensor)
    for parent in [plant, hybrid_inverter, dc_charger, ac_charger, pv_inverter]:
        devices: list[Device] = [parent]
        devices.extend(parent.children)
        for device in devices:
            for sensor in device.sensors.values():
                if isinstance(sensor, AlarmCombinedSensor):
                    add_sensor_instance(sensor)
                    for alarm in sensor.alarms:
                        add_sensor_instance(alarm)
                else:
                    add_sensor_instance(sensor)

    if concrete_sensor_check:
        previous: tuple[int, int] | None = None
        for address in sorted(registers.keys()):
            sensor = cast(ModbusSensorMixin, registers[address])
            count = sensor.count
            if previous:
                last_address, last_count = previous
                if (
                    address
                    not in (  # Sensors that start each register range
                        InverterModel.ADDRESS,  # 31000
                        RatedGridVoltage.ADDRESS,  # 31500
                        DCChargerVehicleBatteryVoltage.ADDRESS,  # 32000
                        ACChargerRunningState.ADDRESS,  # 32000
                        PlantStatus.ADDRESS,  # 40000
                        InverterStatus.ADDRESS,  # 40500
                        DCChargerStatus.ADDRESS,  # 41000
                        ReservedInverterRemoteEMSDispatch.ADDRESS,  # 41500
                        ACChargerStatus.ADDRESS,  # 42000
                    )
                    and last_address + last_count < address
                ):
                    logging.warning(
                        f"Gap detected between register {last_address} (count={last_count} class={registers[last_address].__class__.__name__}) and register {address} (class={registers[address].__class__.__name__})"
                    )
            for i in range(address + 1, address + count):
                if i in registers:
                    logging.warning(f"Register {i} in {sensor.__class__.__name__} overlaps {registers[i].__class__.__name__}")
            previous = (address, count)
        for classname, count in classes.items():
            if count == 0:
                logging.warning(f"Class {classname} has not been used?")

    return sensors


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    with _swap_active_config(Config()):
        asyncio.run(get_sensor_instances())
