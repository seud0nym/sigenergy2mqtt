import asyncio
import importlib
import logging
import pkgutil
from typing import cast

import sigenergy2mqtt.devices.smartport as smartport_pkg
import sigenergy2mqtt.sensors.plant_derived as derived
import sigenergy2mqtt.sensors.plant_read_only as ro
import sigenergy2mqtt.sensors.plant_read_write as rw
from sigenergy2mqtt.common import ConsumptionMethod, DeviceType, FirmwareVersion, HybridInverter, Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.inverter_read_only import OutputType
from sigenergy2mqtt.sensors.plant_read_only import GridSensorActivePower, GridStatus
from sigenergy2mqtt.sensors.plant_read_write import RemoteEMS

from .grid_code import GridCode
from .grid_sensor import GridSensor
from .statistics import PlantStatistics

_VALID_SMARTPORT_MODULES = frozenset(mod.name for mod in pkgutil.iter_modules(smartport_pkg.__path__))


class PowerPlant(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
    ):
        name = "Sigenergy Plant" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1}"
        super().__init__(device_type, name, plant_index, 247, "Energy Management System", protocol_version, sw=f"Modbus Protocol V{protocol_version.value}")
        self._consumption_source = ConsumptionMethod.CALCULATED if self.protocol_version < Protocol.V2_8 else active_config.consumption
        self._consumption_group = "Consumption" if self._consumption_source == ConsumptionMethod.CALCULATED else None  # No need to group sensors for scanning if not calculating consumption
        self._plant_pv_power = ro.PlantPVPower(plant_index)
        self._plant_3rd_party_pv_power = ro.ThirdPartyPVPower(plant_index) if protocol_version >= Protocol.V2_7 else None
        self._total_pv_power = derived.TotalPVPower(plant_index, self._plant_pv_power)
        self._grid_sensor = None
        self._smartport = None

    @classmethod
    async def create(cls, plant_index: int, device_type: DeviceType, firmware: str, protocol_version: Protocol, output_type: int, modbus_client: ModbusClient) -> "PowerPlant":
        power_phases = OutputType.to_phases(output_type)
        plant = cls(plant_index, device_type, protocol_version)
        await plant._register_child_devices(power_phases, modbus_client)
        await plant._register_sensors(firmware, output_type, power_phases, modbus_client)
        availability_control_sensor = plant.sensors.get(f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_247_{RemoteEMS.ADDRESS}")
        if availability_control_sensor is None:
            raise RuntimeError(f"{plant.__class__.__name__} Failed to find RemoteEMS sensor — cannot continue setup")
        return plant

    async def _register_child_devices(self, power_phases: int, modbus_client: ModbusClient) -> None:
        self._grid_sensor = await GridSensor.create(self.plant_index, self._device_type, self.protocol_version, power_phases, self._consumption_group, modbus_client)
        self._add_child_device(self._grid_sensor)

        self._add_child_device(await PlantStatistics.create(self.plant_index, self._device_type, self.protocol_version))

        if self._device_type.has_grid_code_interface and self.protocol_version >= Protocol.V2_8:
            self._add_child_device(await GridCode.create(self.plant_index, self._device_type, self.protocol_version, modbus_client))

        if active_config.modbus[self.plant_index].smartport.enabled:
            smartport_config = active_config.modbus[self.plant_index].smartport
            if smartport_config.module.name:
                module_config = smartport_config.module
                if module_config.name not in _VALID_SMARTPORT_MODULES:
                    logging.error(f"{self.log_identity} Unknown SmartPort module '{module_config.name}' - ignoring")
                else:
                    module = importlib.import_module(f"sigenergy2mqtt.devices.smartport.{module_config.name}")
                    try:
                        SmartPort = getattr(module, "SmartPort")
                        self._smartport = SmartPort(self.plant_index, module_config)
                        self._smartport.via_device = self.unique_id
                        self._add_child_device(self._smartport)
                    except Exception:
                        logging.exception(f"{self.log_identity} Failed to create SmartPort instance")

    async def _register_sensors(self, firmware: str, output_type: int, power_phases: int, modbus_client: ModbusClient) -> None:
        rated_charging_power = ro.PlantRatedChargingPower(self.plant_index)
        rated_discharging_power = ro.PlantRatedDischargingPower(self.plant_index)
        # Fetch async values in parallel
        rcp_value, rdp_value = await asyncio.gather(
            rated_charging_power.get_state(modbus_client=modbus_client),
            rated_discharging_power.get_state(modbus_client=modbus_client),
        )

        self.has_battery = isinstance(self._device_type, HybridInverter) and cast(float, rcp_value) > 0.0

        self._add_read_sensor(ro.SystemTime(self.plant_index))
        self._add_read_sensor(ro.SystemTimeZone(self.plant_index))
        self._add_read_sensor(ro.EMSWorkMode(self.plant_index))
        self._add_read_sensor(ro.MaxActivePower(self.plant_index))
        self._add_read_sensor(ro.MaxApparentPower(self.plant_index))

        self._add_read_sensor(ro.PlantPhaseActivePower(self.plant_index, power_phases, "A"))
        self._add_read_sensor(ro.PlantPhaseReactivePower(self.plant_index, power_phases, "A"))
        if power_phases > 1:
            self._add_read_sensor(ro.PlantPhaseActivePower(self.plant_index, power_phases, "B"))
            self._add_read_sensor(ro.PlantPhaseReactivePower(self.plant_index, power_phases, "B"))
        if power_phases > 2:
            self._add_read_sensor(ro.PlantPhaseActivePower(self.plant_index, power_phases, "C"))
            self._add_read_sensor(ro.PlantPhaseReactivePower(self.plant_index, power_phases, "C"))

        self._add_read_sensor(ro.GeneralPCSAlarm(self.plant_index, ro.GeneralAlarm1(self.plant_index), ro.GeneralAlarm2(self.plant_index)))
        self._add_read_sensor(ro.GeneralAlarm3(self.plant_index))
        self._add_read_sensor(ro.GeneralAlarm4(self.plant_index))
        if len(active_config.modbus[self.plant_index].dc_chargers) > 0:
            self._add_read_sensor(ro.GeneralAlarm5(self.plant_index))

        self._add_read_sensor(ro.PlantActivePower(self.plant_index), "Plant Power")
        self._add_read_sensor(ro.PlantReactivePower(self.plant_index), "Plant Power")
        self._add_read_sensor(self._plant_pv_power, self._consumption_group)

        self._add_read_sensor(ro.AvailableMaxActivePower(self.plant_index))
        self._add_read_sensor(ro.AvailableMinActivePower(self.plant_index))
        self._add_read_sensor(ro.AvailableMaxReactivePower(self.plant_index))
        self._add_read_sensor(ro.AvailableMinReactivePower(self.plant_index))
        self._add_read_sensor(ro.PlantRunningState(self.plant_index))
        self._add_read_sensor(ro.PlantRatedEnergyCapacity(self.plant_index))
        self._add_read_sensor(rw.GridMaxExportLimit(self.plant_index))
        self._add_read_sensor(rw.GridMaxImportLimit(self.plant_index))
        self._add_read_sensor(rw.PCSMaxExportLimit(self.plant_index))
        self._add_read_sensor(rw.PCSMaxImportLimit(self.plant_index))
        self._add_read_sensor(ro.TotalLoadConsumption(self.plant_index))
        self._add_read_sensor(ro.TotalLoadDailyConsumption(self.plant_index))

        fw = FirmwareVersion(firmware)
        remote_ems = rw.RemoteEMS(self.plant_index)
        remote_ems_mode = rw.RemoteEMSControlMode(self.plant_index, remote_ems)

        self._add_read_sensor(remote_ems)
        self._add_read_sensor(remote_ems_mode)
        self._add_read_sensor(rw.ActivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems))
        self._add_read_sensor(rw.ReactivePowerFixedAdjustmentTargetValue(self.plant_index))
        self._add_read_sensor(rw.ActivePowerPercentageAdjustmentTargetValue(self.plant_index, remote_ems))

        self._add_read_sensor(rw.PVMaxPowerLimit(self.plant_index, remote_ems if fw.service_pack < 113 else None, remote_ems_mode if fw.service_pack < 113 else None))

        self._add_read_sensor(rw.QSAdjustmentTargetValue(self.plant_index))
        self._add_read_sensor(rw.PowerFactorAdjustmentTargetValue(self.plant_index))

        if self._device_type.has_independent_phase_power_control_interface and output_type == 2:  # L1/L2/L3/N
            independent_phase_power_control = rw.IndependentPhasePowerControl(self.plant_index, output_type)
            self._add_read_sensor(independent_phase_power_control)
            self._add_read_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseQSAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseQSAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "C"))
            self._add_read_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "C"))
            self._add_read_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "C"))
            self._add_read_sensor(rw.PhaseQSAdjustmentTargetValue(self.plant_index, independent_phase_power_control, output_type, "C"))

        address = 30098  # Starting register for Smart Load 1 Total Consumption
        for n in range(1, 25):  # Smart Loads 1 to 24
            self._add_read_sensor(ro.SmartLoadTotalConsumption(self.plant_index, address, n))
            self._add_read_sensor(ro.SmartLoadPower(self.plant_index, address + 48, n))  # Each Smart Load Total Consumption has a count of 2 registers, 24 * 2 = 48
            address += 2  # registers

        battery_power = None
        if self.has_battery:
            battery_power = ro.BatteryPower(self.plant_index)
            total_charge_energy = ro.ESSTotalChargedEnergy(self.plant_index)
            total_discharge_energy = ro.ESSTotalDischargedEnergy(self.plant_index)
            self._add_read_sensor(ro.PlantBatterySoC(self.plant_index))
            self._add_read_sensor(battery_power, self._consumption_group)
            self._add_read_sensor(ro.AvailableMaxChargingPower(self.plant_index))
            self._add_read_sensor(ro.AvailableMaxDischargingPower(self.plant_index))
            self._add_read_sensor(ro.AvailableMaxChargingCapacity(self.plant_index))
            self._add_read_sensor(ro.AvailableMaxDischargingCapacity(self.plant_index))
            self._add_read_sensor(rated_charging_power)
            self._add_read_sensor(rated_discharging_power)
            self._add_read_sensor(ro.ChargeCutOffSoC(self.plant_index))
            self._add_read_sensor(ro.DischargeCutOffSoC(self.plant_index))
            self._add_read_sensor(ro.PlantBatterySoH(self.plant_index))
            self._add_read_sensor(rw.ESSBackupSOC(self.plant_index))
            self._add_read_sensor(rw.ESSChargeCutOffSOC(self.plant_index))
            self._add_read_sensor(rw.ESSDischargeCutOffSOC(self.plant_index))
            self._add_read_sensor(rw.MaxChargingLimit(self.plant_index, remote_ems if fw.service_pack < 113 else None, remote_ems_mode if fw.service_pack < 113 else None, cast(float, rcp_value)))
            self._add_read_sensor(rw.MaxDischargingLimit(self.plant_index, remote_ems if fw.service_pack < 113 else None, remote_ems_mode if fw.service_pack < 113 else None, cast(float, rdp_value)))
            self._add_read_sensor(total_charge_energy)
            self._add_read_sensor(total_discharge_energy)
            self._add_derived_sensor(derived.BatteryChargingPower(self.plant_index, battery_power), battery_power)
            self._add_derived_sensor(derived.BatteryDischargingPower(self.plant_index, battery_power), battery_power)
            self._add_derived_sensor(derived.PlantDailyChargeEnergy(self.plant_index, total_charge_energy), total_charge_energy, search_children=False)
            self._add_derived_sensor(derived.PlantDailyDischargeEnergy(self.plant_index, total_discharge_energy), total_discharge_energy, search_children=False)

        self._add_read_sensor(ro.EVDCTotalChargedEnergy(self.plant_index))
        self._add_read_sensor(ro.EVDCTotalDischargedEnergy(self.plant_index))
        self._add_read_sensor(ro.PlantTotalGeneratorOutputEnergy(self.plant_index))

        self._add_writeonly_sensor(rw.PlantStatus(self.plant_index))

        general_load_power = ro.GeneralLoadPower(self.plant_index)
        total_load_power = ro.TotalLoadPower(self.plant_index)
        self._add_read_sensor(general_load_power)
        self._add_read_sensor(total_load_power)
        self._add_read_sensor(rw.ActivePowerRegulationGradient(self.plant_index))

        self._add_read_sensor(ro.CurrentControlCommandValue(self.plant_index))
        self._add_read_sensor(ro.PlantAlarms(self.plant_index, ro.Alarm6(self.plant_index), ro.Alarm7(self.plant_index)))

        self._add_derived_sensor(self._total_pv_power, self._plant_pv_power, search_children=False)
        if self._smartport:
            smartport_pv_power = active_config.modbus[self.plant_index].smartport.module.pv_power
            if smartport_pv_power and not smartport_pv_power.isspace():
                for sensor in self._smartport.sensors.values():
                    if sensor.__class__.__name__ == smartport_pv_power:
                        self._total_pv_power.register_source_sensors(sensor, type=derived.TotalPVPower.SourceType.SMARTPORT, enabled=True)
                        self._add_derived_sensor(self._total_pv_power, sensor, search_children=True)
                        break
            if self._plant_3rd_party_pv_power:
                self._add_read_sensor(self._plant_3rd_party_pv_power)
                self._add_derived_sensor(self._total_pv_power, self._plant_3rd_party_pv_power, search_children=False)
                self._total_pv_power.register_source_sensors(self._plant_3rd_party_pv_power, type=derived.TotalPVPower.SourceType.FAILOVER, enabled=False)
            else:
                logging.warning(f"{self.log_identity} Unable to register ThirdPartyPVPower sensor for SmartPort failover - protocol version {self.protocol_version} does not support it")
        else:
            if self._plant_3rd_party_pv_power:
                self._add_read_sensor(self._plant_3rd_party_pv_power, self._consumption_group)
                self._add_derived_sensor(self._total_pv_power, self._plant_3rd_party_pv_power, search_children=False)
                self._total_pv_power.register_source_sensors(self._plant_3rd_party_pv_power, type=derived.TotalPVPower.SourceType.MANDATORY, enabled=True)
            else:
                logging.warning(f"{self.log_identity} Unable to register ThirdPartyPVPower sensor as TotalPVPower source - protocol version {self.protocol_version} does not support it")

        plant_consumed_power = derived.PlantConsumedPower(self.plant_index, method=self._consumption_source)
        match plant_consumed_power.method:
            case ConsumptionMethod.CALCULATED:
                if not self._grid_sensor:  # Should not be possible: unconditional registration in _register_child_devices
                    raise RuntimeError(f"{self.log_identity} GridSensor device not registered???")
                active_power = self._grid_sensor.get_sensor(GridSensorActivePower)
                if not active_power:
                    raise RuntimeError(f"{self.log_identity} GridSensorActivePower not registered in GridSensor device???")
                grid_status = self._grid_sensor.get_sensor(GridStatus)
                if not grid_status:
                    raise RuntimeError(f"{self.log_identity} GridStatus not registered in GridSensor device???")
                self._add_derived_sensor(plant_consumed_power, self._total_pv_power, battery_power, active_power, grid_status, search_children=True)
            case ConsumptionMethod.GENERAL:
                self._add_derived_sensor(plant_consumed_power, general_load_power)
            case ConsumptionMethod.TOTAL:
                self._add_derived_sensor(plant_consumed_power, total_load_power)

        plant_lifetime_pv_energy = ro.PlantPVTotalGeneration(self.plant_index)
        plant_3rd_party_lifetime_pv_energy = ro.ThirdPartyLifetimePVEnergy(self.plant_index)
        total_lifetime_pv_energy = derived.TotalLifetimePVEnergy(self.plant_index)
        self._add_read_sensor(plant_lifetime_pv_energy, "Lifetime Production")
        self._add_read_sensor(plant_3rd_party_lifetime_pv_energy, "Lifetime Production")
        self._add_derived_sensor(total_lifetime_pv_energy, plant_lifetime_pv_energy, plant_3rd_party_lifetime_pv_energy)
        self._add_derived_sensor(derived.PlantDailyPVEnergy(self.plant_index, plant_lifetime_pv_energy), plant_lifetime_pv_energy)
        self._add_derived_sensor(derived.TotalDailyPVEnergy(self.plant_index, total_lifetime_pv_energy), total_lifetime_pv_energy)

        # Add the reserved registers to optimise sensor scanning
        self._add_read_sensor(ro.Reserved30073(self.plant_index))
        self._add_read_sensor(ro.ReservedPVTotalGenerationToday(self.plant_index))
        self._add_read_sensor(ro.ReservedPVTotalGenerationYesterday(self.plant_index))
        self._add_read_sensor(rw.Reserved40026(self.plant_index))
