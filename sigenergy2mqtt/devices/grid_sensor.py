from .device import ModbusDevice, DeviceType
from sigenergy2mqtt.config import Config, Protocol, ConsumptionMethod
import sigenergy2mqtt.sensors.plant_derived as derived
import sigenergy2mqtt.sensors.plant_read_only as ro


class GridSensor(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
        power_phases: int,
        active_power: ro.GridSensorActivePower,
    ):
        name = "Sigenergy Plant Grid Sensor" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1} Grid Sensor"
        super().__init__(device_type, name, plant_index, 247, "Grid Sensor", protocol_version)

        self._add_read_sensor(ro.GridSensorStatus(plant_index))
        self._add_read_sensor(active_power, "Consumption" if Config.consumption == ConsumptionMethod.CALCULATED else None)
        self._add_read_sensor(ro.GridSensorReactivePower(plant_index))
        self._add_read_sensor(ro.GridPhaseActivePower(plant_index, "A"))
        self._add_read_sensor(ro.GridPhaseReactivePower(plant_index, "A"))
        self._add_read_sensor(ro.ReservedGridPhaseVoltage(plant_index, "A"))
        self._add_read_sensor(ro.ReservedGridPhaseCurrent(plant_index, "A"))
        if power_phases > 1:
            self._add_read_sensor(ro.GridPhaseActivePower(plant_index, "B"))
            self._add_read_sensor(ro.GridPhaseReactivePower(plant_index, "B"))
            self._add_read_sensor(ro.ReservedGridPhaseVoltage(plant_index, "B"))
            self._add_read_sensor(ro.ReservedGridPhaseCurrent(plant_index, "B"))
        if power_phases > 2:
            self._add_read_sensor(ro.GridPhaseActivePower(plant_index, "C"))
            self._add_read_sensor(ro.GridPhaseReactivePower(plant_index, "C"))
            self._add_read_sensor(ro.ReservedGridPhaseVoltage(plant_index, "C"))
            self._add_read_sensor(ro.ReservedGridPhaseCurrent(plant_index, "C"))
        self._add_read_sensor(ro.GridStatus(plant_index))

        export_power = derived.GridSensorExportPower(plant_index, active_power)
        import_power = derived.GridSensorImportPower(plant_index, active_power)
        self._add_derived_sensor(export_power, active_power)
        self._add_derived_sensor(import_power, active_power)
        export_energy = ro.PlantTotalExportedEnergy(plant_index)
        self._add_read_sensor(export_energy)
        self._add_derived_sensor(derived.GridSensorDailyExportEnergy(plant_index, export_energy), export_energy)
        import_energy = ro.PlantTotalImportedEnergy(plant_index)
        self._add_read_sensor(import_energy)
        self._add_derived_sensor(derived.GridSensorDailyImportEnergy(plant_index, import_energy), import_energy)
