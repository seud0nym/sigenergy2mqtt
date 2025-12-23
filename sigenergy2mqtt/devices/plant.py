from .device import ModbusDevice
from .grid_code import GridCode
from .grid_sensor import GridSensor
from .plant_statistics import PlantStatistics
from .types import DeviceType, HybridInverter
from sigenergy2mqtt.config import Config, Protocol, ConsumptionMethod
import importlib
import logging
import sigenergy2mqtt.sensors.plant_derived as derived
import sigenergy2mqtt.sensors.plant_read_only as ro
import sigenergy2mqtt.sensors.plant_read_write as rw


class PowerPlant(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
        output_type: int,
        power_phases: int,
        rcp_value: float,
        rdp_value: float,
        rf_value: float,
        rated_charging_power: ro.PlantRatedChargingPower,
        rated_discharging_power: ro.PlantRatedDischargingPower,
        rated_frequency: ro.GridCodeRatedFrequency,
    ):
        name = "Sigenergy Plant" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1}"
        super().__init__(
            device_type,
            name,
            plant_index,
            247,
            "Energy Management System",
            protocol_version,
            sw=f"Modbus Protocol V{protocol_version.value}",
        )

        self.has_battery = isinstance(device_type, HybridInverter) and rcp_value > 0.0

        consumption_source = ConsumptionMethod.CALCULATED if protocol_version < Protocol.V2_8 else Config.consumption
        consumption_group = "Consumption" if consumption_source == ConsumptionMethod.CALCULATED else None

        grid_sensor_active_power = ro.GridSensorActivePower(plant_index)
        plant_pv_power = ro.PlantPVPower(plant_index)

        self._add_read_sensor(ro.SystemTime(plant_index))
        self._add_read_sensor(ro.SystemTimeZone(plant_index))
        self._add_read_sensor(ro.EMSWorkMode(plant_index))
        self._add_read_sensor(ro.MaxActivePower(plant_index))
        self._add_read_sensor(ro.MaxApparentPower(plant_index))
        self._add_read_sensor(ro.PlantPhaseActivePower(plant_index, power_phases, "A"))
        self._add_read_sensor(ro.PlantPhaseReactivePower(plant_index, power_phases, "A"))
        if power_phases > 1:
            self._add_read_sensor(ro.PlantPhaseActivePower(plant_index, power_phases, "B"))
            self._add_read_sensor(ro.PlantPhaseReactivePower(plant_index, power_phases, "B"))
        if power_phases > 2:
            self._add_read_sensor(ro.PlantPhaseActivePower(plant_index, power_phases, "C"))
            self._add_read_sensor(ro.PlantPhaseReactivePower(plant_index, power_phases, "C"))
        self._add_read_sensor(ro.GeneralPCSAlarm(plant_index, ro.GeneralAlarm1(plant_index), ro.GeneralAlarm2(plant_index)))
        self._add_read_sensor(ro.GeneralAlarm3(plant_index))
        self._add_read_sensor(ro.GeneralAlarm4(plant_index))
        if len(Config.devices[plant_index].dc_chargers) > 0:
            self._add_read_sensor(ro.GeneralAlarm5(plant_index))
        self._add_read_sensor(ro.PlantActivePower(plant_index), "Plant Power")
        self._add_read_sensor(ro.PlantReactivePower(plant_index), "Plant Power")
        self._add_read_sensor(plant_pv_power, consumption_group)

        self._add_read_sensor(ro.AvailableMaxActivePower(plant_index))
        self._add_read_sensor(ro.AvailableMinActivePower(plant_index))
        self._add_read_sensor(ro.AvailableMaxReactivePower(plant_index))
        self._add_read_sensor(ro.AvailableMinReactivePower(plant_index))
        self._add_read_sensor(ro.PlantRunningState(plant_index))
        self._add_read_sensor(ro.PlantRatedEnergyCapacity(plant_index))
        self._add_read_sensor(rw.GridMaxExportLimit(plant_index))
        self._add_read_sensor(rw.GridMaxImportLimit(plant_index))
        self._add_read_sensor(rw.PCSMaxExportLimit(plant_index))
        self._add_read_sensor(rw.PCSMaxImportLimit(plant_index))
        self._add_read_sensor(ro.TotalLoadConsumption(plant_index))
        self._add_read_sensor(ro.TotalLoadDailyConsumption(plant_index))

        remote_ems = rw.RemoteEMS(plant_index)
        remote_ems_mode = rw.RemoteEMSControlMode(plant_index, remote_ems)
        self._add_read_sensor(remote_ems)
        self._add_read_sensor(remote_ems_mode)
        self._add_read_sensor(rw.ActivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.ReactivePowerFixedAdjustmentTargetValue(plant_index))
        self._add_read_sensor(rw.ActivePowerPercentageAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.QSAdjustmentTargetValue(plant_index))
        self._add_read_sensor(rw.PowerFactorAdjustmentTargetValue(plant_index))
        if device_type.has_independent_phase_power_control_interface and output_type == 2:  # L1/L2/L3/N
            independent_phase_power_control = rw.IndependentPhasePowerControl(plant_index, output_type)
            self._add_read_sensor(independent_phase_power_control)
            self._add_read_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseQSAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "A"))
            self._add_read_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseQSAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "B"))
            self._add_read_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "C"))
            self._add_read_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "C"))
            self._add_read_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "C"))
            self._add_read_sensor(rw.PhaseQSAdjustmentTargetValue(plant_index, independent_phase_power_control, output_type, "C"))
        self._add_read_sensor(rw.PVMaxPowerLimit(plant_index, remote_ems, remote_ems_mode))

        address = 30098
        for n in range(1, 25):
            self._add_read_sensor(ro.SmartLoadTotalConsumption(plant_index, address, n))
            self._add_read_sensor(ro.SmartLoadPower(plant_index, address + 48, n))
            address += 2

        if self.has_battery:
            battery_power = ro.BatteryPower(plant_index)
            total_charge_energy = ro.ESSTotalChargedEnergy(plant_index)
            total_discharge_energy = ro.ESSTotalDischargedEnergy(plant_index)
            self._add_read_sensor(ro.PlantBatterySoC(plant_index))
            self._add_read_sensor(battery_power, consumption_group)
            self._add_read_sensor(ro.AvailableMaxChargingPower(plant_index))
            self._add_read_sensor(ro.AvailableMaxDischargingPower(plant_index))
            self._add_read_sensor(ro.AvailableMaxChargingCapacity(plant_index))
            self._add_read_sensor(ro.AvailableMaxDischargingCapacity(plant_index))
            self._add_read_sensor(rated_charging_power)
            self._add_read_sensor(rated_discharging_power)
            self._add_read_sensor(ro.ChargeCutOffSoC(plant_index))
            self._add_read_sensor(ro.DischargeCutOffSoC(plant_index))
            self._add_read_sensor(ro.PlantBatterySoH(plant_index))
            self._add_read_sensor(rw.ESSBackupSOC(plant_index))
            self._add_read_sensor(rw.ESSChargeCutOffSOC(plant_index))
            self._add_read_sensor(rw.ESSDischargeCutOffSOC(plant_index))
            self._add_read_sensor(rw.MaxChargingLimit(plant_index, remote_ems, remote_ems_mode, rcp_value))
            self._add_read_sensor(rw.MaxDischargingLimit(plant_index, remote_ems, remote_ems_mode, rdp_value))
            self._add_read_sensor(total_charge_energy)
            self._add_read_sensor(total_discharge_energy)
            self._add_derived_sensor(derived.BatteryChargingPower(plant_index, battery_power), battery_power)
            self._add_derived_sensor(derived.BatteryDischargingPower(plant_index, battery_power), battery_power)
            self._add_derived_sensor(derived.PlantDailyChargeEnergy(plant_index, total_charge_energy), total_charge_energy, search_children=False)
            self._add_derived_sensor(derived.PlantDailyDischargeEnergy(plant_index, total_discharge_energy), total_discharge_energy, search_children=False)
        else:
            battery_power = None

        self._add_read_sensor(ro.EVDCTotalChargedEnergy(plant_index))
        self._add_read_sensor(ro.EVDCTotalDischargedEnergy(plant_index))
        self._add_read_sensor(ro.PlantTotalGeneratorOutputEnergy(plant_index))

        self._add_writeonly_sensor(rw.PlantStatus(plant_index))

        self._add_child_device(GridSensor(plant_index, device_type, protocol_version, power_phases, grid_sensor_active_power))
        self._add_child_device(PlantStatistics(plant_index, device_type, protocol_version))
        if device_type.has_grid_code_interface and protocol_version >= Protocol.V2_8:
            self._add_child_device(GridCode(plant_index, device_type, protocol_version, rf_value, rated_frequency))

        plant_3rd_party_pv_power = ro.ThirdPartyPVPower(plant_index)
        total_pv_power = derived.TotalPVPower(plant_index, plant_pv_power)
        self._add_derived_sensor(total_pv_power, plant_pv_power, search_children=False)
        smartport = None
        if Config.devices[plant_index].smartport.enabled:
            smartport_config = Config.devices[plant_index].smartport
            if smartport_config.module.name:
                module_config = smartport_config.module
                module = importlib.import_module(f"sigenergy2mqtt.devices.smartport.{module_config.name}")
                try:
                    SmartPort = getattr(module, "SmartPort")
                    smartport = SmartPort(plant_index, module_config)
                    smartport.via_device = self.unique_id
                    self._add_child_device(smartport)
                    if module_config.pv_power and not module_config.pv_power.isspace():
                        for sensor in smartport.sensors.values():
                            if sensor.__class__.__name__ == module_config.pv_power:
                                total_pv_power.register_source_sensors(sensor, type=derived.TotalPVPower.SourceType.SMARTPORT, enabled=True)
                                self._add_derived_sensor(total_pv_power, sensor, search_children=True)
                                break
                    self._add_read_sensor(plant_3rd_party_pv_power)
                    total_pv_power.register_source_sensors(plant_3rd_party_pv_power, type=derived.TotalPVPower.SourceType.FAILOVER, enabled=False)
                except Exception as e:
                    logging.error(f"{self.__class__.__name__} Failed to create SmartPort instance - {e}")
                    smartport = None
        if smartport is None:
            self._add_read_sensor(plant_3rd_party_pv_power, consumption_group)
            total_pv_power.register_source_sensors(plant_3rd_party_pv_power, type=derived.TotalPVPower.SourceType.MANDATORY, enabled=True)

        self._add_derived_sensor(total_pv_power, plant_3rd_party_pv_power)

        general_load_power = ro.GeneralLoadPower(plant_index)
        total_load_power = ro.TotalLoadPower(plant_index)
        self._add_read_sensor(general_load_power)
        self._add_read_sensor(total_load_power)
        self._add_read_sensor(rw.ActivePowerRegulationGradient(plant_index))

        self._add_read_sensor(ro.CurrentControlCommandValue(plant_index))
        self._add_read_sensor(ro.PlantAlarms(plant_index))

        plant_consumed_power = derived.PlantConsumedPower(plant_index, method=consumption_source)
        match plant_consumed_power.method:
            case ConsumptionMethod.CALCULATED:
                grid_status = self.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_30009", True)
                assert grid_status is not None, "Grid Status sensor not found for Plant Consumed Power calculation"
                self._add_derived_sensor(plant_consumed_power, total_pv_power, battery_power, grid_sensor_active_power, grid_status, search_children=True)
            case ConsumptionMethod.GENERAL:
                self._add_derived_sensor(plant_consumed_power, general_load_power)
            case ConsumptionMethod.TOTAL:
                self._add_derived_sensor(plant_consumed_power, total_load_power)

        plant_lifetime_pv_energy = ro.PlantPVTotalGeneration(plant_index)
        plant_3rd_party_lifetime_pv_energy = ro.ThirdPartyLifetimePVEnergy(plant_index)
        total_lifetime_pv_energy = derived.TotalLifetimePVEnergy(plant_index)
        self._add_read_sensor(plant_lifetime_pv_energy, "Lifetime Production")
        self._add_read_sensor(plant_3rd_party_lifetime_pv_energy, "Lifetime Production")
        self._add_derived_sensor(total_lifetime_pv_energy, plant_lifetime_pv_energy, plant_3rd_party_lifetime_pv_energy)
        self._add_derived_sensor(derived.PlantDailyPVEnergy(plant_index, plant_lifetime_pv_energy), plant_lifetime_pv_energy)
        self._add_derived_sensor(derived.TotalDailyPVEnergy(plant_index, total_lifetime_pv_energy), total_lifetime_pv_energy)

        # region reserved registers
        self._add_read_sensor(ro.Reserved30073(plant_index))
        self._add_read_sensor(ro.ReservedPVTotalGenerationToday(plant_index))
        self._add_read_sensor(ro.ReservedPVTotalGenerationYesterday(plant_index))
        self._add_read_sensor(rw.Reserved40026(plant_index))
        # endregion
