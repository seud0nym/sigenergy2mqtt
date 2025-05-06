from .device import ModBusDevice, DeviceType
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.sensors.base import PVCurrentSensor, PVVoltageSensor
from sigenergy2mqtt.sensors.inverter_derived import PVStringPower, PVStringDailyEnergy, PVStringLifetimeEnergy


class PVString(ModBusDevice):
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
    ):
        name = f"{model_id.split()[0]} {serial_number} PV String {string_number}"
        super().__init__(
            device_type,
            name,
            plant_index,
            device_address,
            "PV String",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{self.__class__.__name__.lower()}{string_number}",
        )

        voltage = PVVoltageSensor(plant_index, device_address, voltage_address, string_number)
        current = PVCurrentSensor(plant_index, device_address, current_address, string_number)
        power = PVStringPower(plant_index, device_address, string_number)
        lifetime_energy = PVStringLifetimeEnergy(plant_index, device_address, string_number, power)
        daily_energy = PVStringDailyEnergy(plant_index, device_address, string_number, lifetime_energy)

        self._add_read_sensor(voltage)
        self._add_read_sensor(current)
        self._add_derived_sensor(power, voltage, current)
        self._add_derived_sensor(lifetime_energy, power)
        self._add_derived_sensor(daily_energy, lifetime_energy)
