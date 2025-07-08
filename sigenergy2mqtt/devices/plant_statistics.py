from .device import ModbusDevice, DeviceType
import sigenergy2mqtt.sensors.plant_read_only as ro


class PlantStatistics(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
    ):
        name = "Sigenergy Plant Statistics" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1} Statistics"
        super().__init__(device_type, name, plant_index, 247, "EMS Statistics")

        self._add_read_sensor(ro.SITotalChargedEnergy(plant_index))
        self._add_read_sensor(ro.SITotalCommonLoadConsumption(plant_index))
        self._add_read_sensor(ro.SITotalDischargedEnergy(plant_index))
        self._add_read_sensor(ro.SITotalEVACChargedEnergy(plant_index))
        self._add_read_sensor(ro.SITotalEVDCChargedEnergy(plant_index))
        self._add_read_sensor(ro.SITotalEVDCDischargedEnergy(plant_index))
        self._add_read_sensor(ro.SITotalExportedEnergy(plant_index))
        self._add_read_sensor(ro.SITotalGeneratorOutputEnergy(plant_index))
        self._add_read_sensor(ro.SITotalImportedEnergy(plant_index))
        self._add_read_sensor(ro.SITotalSelfPVGeneration(plant_index))
        self._add_read_sensor(ro.SITotalThirdPartyPVGeneration(plant_index))
