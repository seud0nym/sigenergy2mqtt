from .device import ModbusDevice, DeviceType
from sigenergy2mqtt.config import Config, Protocol
from sigenergy2mqtt.sensors.inverter_derived import PVStringPower, PVStringDailyEnergy, PVStringLifetimeEnergy
from sigenergy2mqtt.sensors.inverter_read_only import PVCurrentSensor, PVVoltageSensor


class PVString(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        device_type: DeviceType,
        model_id: str,
        serial_number: str,
        string_number: int,
        voltage_address: int,
        current_address: int,
        protocol_version: Protocol,
    ):
        name = f"{model_id.split()[0]} {serial_number} PV String {string_number}"
        super().__init__(
            device_type,
            name,
            plant_index,
            device_address,
            "PV String",
            protocol_version,
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{self.__class__.__name__.lower()}{string_number}",
        )

        voltage = PVVoltageSensor(plant_index, device_address, voltage_address, string_number, protocol_version)
        current = PVCurrentSensor(plant_index, device_address, current_address, string_number, protocol_version)
        power = PVStringPower(plant_index, device_address, string_number, protocol_version, voltage, current)
        lifetime_energy = PVStringLifetimeEnergy(plant_index, device_address, string_number, protocol_version, power)
        daily_energy = PVStringDailyEnergy(plant_index, device_address, string_number, protocol_version, lifetime_energy)

        self._add_read_sensor(voltage)
        self._add_read_sensor(current)
        self._add_derived_sensor(power, voltage, current)
        self._add_derived_sensor(lifetime_energy, power)
        self._add_derived_sensor(daily_energy, lifetime_energy)
