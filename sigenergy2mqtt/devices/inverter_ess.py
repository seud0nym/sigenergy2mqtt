from .device import ModBusDevice, DeviceType
from sigenergy2mqtt.config import Config
import sigenergy2mqtt.sensors.inverter_derived as derived
import sigenergy2mqtt.sensors.inverter_read_only as ro


class ESS(ModBusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        device_type: DeviceType,
        model_id: str,
        serial_number: str,
    ):
        name = f"{model_id.split()[0]} {serial_number} ESS"
        super().__init__(
            device_type,
            name,
            plant_index,
            device_address,
            "Energy Storage System",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{self.__class__.__name__.lower()}",
        )

        self._add_read_sensor(ro.RatedChargingPower(plant_index, device_address))
        self._add_read_sensor(ro.RatedDischargingPower(plant_index, device_address))
        self._add_read_sensor(ro.MaxBatteryChargePower(plant_index, device_address))
        self._add_read_sensor(ro.MaxBatteryDischargePower(plant_index, device_address))
        self._add_read_sensor(ro.AvailableBatteryChargeEnergy(plant_index, device_address))
        self._add_read_sensor(ro.AvailableBatteryDischargeEnergy(plant_index, device_address))
        self._add_read_sensor(ro.InverterBatterySoC(plant_index, device_address))
        self._add_read_sensor(ro.InverterBatterySoH(plant_index, device_address))
        self._add_read_sensor(ro.AverageCellTemperature(plant_index, device_address))
        self._add_read_sensor(ro.AverageCellVoltage(plant_index, device_address))
        self._add_read_sensor(ro.InverterAlarm3(plant_index, device_address))
        self._add_read_sensor(ro.InverterMaxBatteryTemperature(plant_index, device_address))
        self._add_read_sensor(ro.InverterMinBatteryTemperature(plant_index, device_address))
        self._add_read_sensor(ro.InverterMaxCellVoltage(plant_index, device_address))
        self._add_read_sensor(ro.InverterMinCellVoltage(plant_index, device_address))
        self._add_read_sensor(ro.DailyChargeEnergy(plant_index, device_address))
        self._add_read_sensor(ro.AccumulatedChargeEnergy(plant_index, device_address))
        self._add_read_sensor(ro.DailyDischargeEnergy(plant_index, device_address))
        self._add_read_sensor(ro.AccumulatedDischargeEnergy(plant_index, device_address))
        self._add_read_sensor(ro.RatedBatteryCapacity(plant_index, device_address))

        battery_power = ro.ChargeDischargePower(plant_index, device_address)
        self._add_read_sensor(battery_power)

        self._add_derived_sensor(derived.InverterBatteryChargingPower(plant_index, device_address, battery_power), battery_power)
        self._add_derived_sensor(derived.InverterBatteryDischargingPower(plant_index, device_address, battery_power), battery_power)
