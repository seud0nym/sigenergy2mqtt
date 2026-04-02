import sigenergy2mqtt.sensors.plant_derived as derived
import sigenergy2mqtt.sensors.plant_read_only as ro
from sigenergy2mqtt.common import DeviceType, Protocol
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient


class GridSensor(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
    ):
        name = "Sigenergy Plant Grid Sensor"
        plant_suffix = "" if plant_index == 0 else f" {plant_index + 1}"
        super().__init__(device_type, name, plant_index, 247, "Grid Sensor", protocol_version, plant_suffix=plant_suffix)

    @classmethod
    async def create(cls, plant_index: int, device_type: DeviceType, protocol_version: Protocol, power_phases: int, consumption_group: str | None, modbus_client: ModbusClient) -> "GridSensor":
        grid_sensor = GridSensor(plant_index, device_type, protocol_version)
        await grid_sensor._register_sensors(power_phases, consumption_group, modbus_client)
        return grid_sensor

    async def _register_sensors(self, power_phases: int, consumption_group: str | None, modbus_client: ModbusClient) -> None:
        active_power = ro.GridSensorActivePower(self.plant_index)
        grid_status = ro.GridStatus(self.plant_index)

        self._add_read_sensor(grid_status)
        self._add_read_sensor(ro.GridSensorStatus(self.plant_index))
        self._add_read_sensor(active_power, consumption_group)
        self._add_read_sensor(ro.GridSensorReactivePower(self.plant_index))
        self._add_read_sensor(ro.GridPhaseActivePower(self.plant_index, "A"))
        self._add_read_sensor(ro.GridPhaseReactivePower(self.plant_index, "A"))
        self._add_read_sensor(ro.ReservedGridPhaseVoltage(self.plant_index, "A"))
        self._add_read_sensor(ro.ReservedGridPhaseCurrent(self.plant_index, "A"))
        if power_phases > 1:
            self._add_read_sensor(ro.GridPhaseActivePower(self.plant_index, "B"))
            self._add_read_sensor(ro.GridPhaseReactivePower(self.plant_index, "B"))
            self._add_read_sensor(ro.ReservedGridPhaseVoltage(self.plant_index, "B"))
            self._add_read_sensor(ro.ReservedGridPhaseCurrent(self.plant_index, "B"))
        if power_phases > 2:
            self._add_read_sensor(ro.GridPhaseActivePower(self.plant_index, "C"))
            self._add_read_sensor(ro.GridPhaseReactivePower(self.plant_index, "C"))
            self._add_read_sensor(ro.ReservedGridPhaseVoltage(self.plant_index, "C"))
            self._add_read_sensor(ro.ReservedGridPhaseCurrent(self.plant_index, "C"))

        import_energy = ro.PlantTotalImportedEnergy(self.plant_index)
        export_energy = ro.PlantTotalExportedEnergy(self.plant_index)
        self._add_read_sensor(import_energy)
        self._add_read_sensor(export_energy)

        import_power = derived.GridSensorImportPower(self.plant_index, active_power)
        export_power = derived.GridSensorExportPower(self.plant_index, active_power)
        self._add_derived_sensor(import_power, active_power)
        self._add_derived_sensor(export_power, active_power)
        self._add_derived_sensor(derived.GridSensorDailyExportEnergy(self.plant_index, export_energy), export_energy)
        self._add_derived_sensor(derived.GridSensorDailyImportEnergy(self.plant_index, import_energy), import_energy)
