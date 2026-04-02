import sigenergy2mqtt.sensors.plant_read_only as ro
from sigenergy2mqtt.common import DeviceType, Protocol
from sigenergy2mqtt.devices import ModbusDevice


class PlantStatistics(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
    ):
        name = "Sigenergy Plant Statistics"
        plant_suffix = "" if plant_index == 0 else f" {plant_index + 1}"
        super().__init__(device_type, name, plant_index, 247, "EMS Statistics", protocol_version, plant_suffix=plant_suffix)

    @classmethod
    async def create(cls, plant_index: int, device_type: DeviceType, protocol_version: Protocol) -> "PlantStatistics":
        plant_statistics = PlantStatistics(plant_index, device_type, protocol_version)
        await plant_statistics._register_sensors()
        return plant_statistics

    async def _register_sensors(self) -> None:
        self._add_read_sensor(ro.SITotalChargedEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalCommonLoadConsumption(self.plant_index))
        self._add_read_sensor(ro.SITotalDischargedEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalEVACChargedEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalEVDCChargedEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalEVDCDischargedEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalExportedEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalGeneratorOutputEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalImportedEnergy(self.plant_index))
        self._add_read_sensor(ro.SITotalSelfPVGeneration(self.plant_index))
        self._add_read_sensor(ro.SITotalThirdPartyPVGeneration(self.plant_index))
