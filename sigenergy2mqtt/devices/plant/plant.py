import asyncio
import logging
from datetime import timezone
from typing import cast

import sigenergy2mqtt.sensors.plant_derived as derived
import sigenergy2mqtt.sensors.plant_read_only as ro
import sigenergy2mqtt.sensors.plant_read_write as rw
from sigenergy2mqtt.common import ConsumptionMethod, DeviceType, FirmwareVersion, HybridInverter, Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.devices.plant.ess_preheating import ESSPreHeating
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.inverter_read_only import OutputType
from sigenergy2mqtt.sensors.plant_read_only import GridSensorActivePower, GridStatus
from sigenergy2mqtt.sensors.plant_read_write import RemoteEMS

from .grid_code import GridCode
from .grid_sensor import GridSensor
from .statistics import PlantStatistics


class PowerPlant(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
    ):
        name = "Sigenergy Plant"
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        super().__init__(
            device_type,
            name,
            plant_index,
            247,
            "Energy Management System",
            protocol_version,
            sw=f"Modbus Protocol V{protocol_version.value}",
            plant_suffix=plant_suffix,
        )
        self._consumption_source = ConsumptionMethod.CALCULATED if self.protocol_version < Protocol.V2_8 else active_config.consumption
        self._consumption_group = "Consumption" if self._consumption_source == ConsumptionMethod.CALCULATED else None  # No need to group sensors for scanning if not calculating consumption
        self._grid_sensor = None

    @classmethod
    async def create(
        cls, plant_index: int, device_type: DeviceType, firmware: FirmwareVersion, protocol_version: Protocol, tz: timezone, output_type: int, pre_heating: bool, modbus_client: ModbusClient
    ) -> "PowerPlant":
        power_phases = OutputType.to_phases(output_type)
        plant = cls(plant_index, device_type, protocol_version)
        await plant._register_sensors(firmware, tz, output_type, power_phases, modbus_client)
        availability_control_sensor = plant.sensors.get(f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_247_{RemoteEMS.ADDRESS}")
        if availability_control_sensor is None:
            raise RuntimeError(f"{plant.__class__.__name__} Failed to find RemoteEMS sensor — cannot continue setup")
        await plant._register_child_devices(power_phases, pre_heating, tz, modbus_client)
        return plant

    async def _register_child_devices(self, power_phases: int, pre_heating: bool, tz: timezone, modbus_client: ModbusClient) -> None:
        self._grid_sensor = await GridSensor.create(self.plant_index, self._device_type, self.protocol_version, power_phases, self._consumption_group, modbus_client)
        self._add_child_device(self._grid_sensor)

        self._add_child_device(await PlantStatistics.create(self.plant_index, self._device_type, self.protocol_version))

        if self.protocol_version >= Protocol.V2_8:
            if self._device_type.has_grid_code_interface:
                self._add_child_device(await GridCode.create(self.plant_index, self._device_type, self.protocol_version, modbus_client))
            else:
                logging.info(f"{self.log_identity} GridCode child device not registered because this device type ({self._device_type}) does not support grid code interface")

        if self.protocol_version >= Protocol.V2_9:
            if pre_heating:
                rated_charging_power = self.sensors.get(f"{active_config.home_assistant.unique_id_prefix}_{self.plant_index}_247_{ro.PlantRatedChargingPower.ADDRESS}")
                rated_discharging_power = self.sensors.get(f"{active_config.home_assistant.unique_id_prefix}_{self.plant_index}_247_{ro.PlantRatedDischargingPower.ADDRESS}")
                if rated_charging_power is None or rated_discharging_power is None:
                    logging.warning(f"{self.log_identity} ESS Pre-Heating child device not registered because PlantRatedChargingPower and/or PlantRatedDischargingPower sensors not found")
                else:
                    self._add_child_device(
                        await ESSPreHeating.create(
                            self.plant_index, self._device_type, tz, cast(float, rated_charging_power.latest_raw_state), cast(float, rated_discharging_power.latest_raw_state), self.protocol_version
                        )
                    )
            else:
                logging.info(f"{self.log_identity} ESS Pre-Heating device not registered because pre-heating sensors not found")

    async def _register_sensors(self, fw: FirmwareVersion, tz: timezone, output_type: int, power_phases: int, modbus_client: ModbusClient) -> None:
        rated_charging_power = ro.PlantRatedChargingPower(self.plant_index)
        rated_discharging_power = ro.PlantRatedDischargingPower(self.plant_index)
        # Fetch async values in parallel
        rcp_value, rdp_value = await asyncio.gather(
            rated_charging_power.get_state(modbus_client=modbus_client),
            rated_discharging_power.get_state(modbus_client=modbus_client),
        )

        self.has_battery = isinstance(self._device_type, HybridInverter) and cast(float, rcp_value) > 0.0

        self._add_sensor(ro.SystemTime(self.plant_index, tz))
        self._add_sensor(ro.SystemTimeZone(self.plant_index))
        self._add_sensor(ro.EMSWorkMode(self.plant_index))
        self._add_sensor(ro.MaxActivePower(self.plant_index))
        self._add_sensor(ro.MaxApparentPower(self.plant_index))

        self._add_sensor(ro.PlantPhaseActivePower(self.plant_index, power_phases, "A"))
        self._add_sensor(ro.PlantPhaseReactivePower(self.plant_index, power_phases, "A"))
        if power_phases > 1:
            self._add_sensor(ro.PlantPhaseActivePower(self.plant_index, power_phases, "B"))
            self._add_sensor(ro.PlantPhaseReactivePower(self.plant_index, power_phases, "B"))
        if power_phases > 2:
            self._add_sensor(ro.PlantPhaseActivePower(self.plant_index, power_phases, "C"))
            self._add_sensor(ro.PlantPhaseReactivePower(self.plant_index, power_phases, "C"))

        self._add_sensor(ro.GeneralPCSAlarm(self.plant_index, ro.GeneralAlarm1(self.plant_index), ro.GeneralAlarm2(self.plant_index)))
        self._add_sensor(ro.GeneralAlarm3(self.plant_index))
        self._add_sensor(ro.GeneralAlarm4(self.plant_index))
        if len(active_config.modbus[self.plant_index].dc_chargers) > 0:
            self._add_sensor(ro.GeneralAlarm5(self.plant_index))

        plant_pv_power = ro.PlantPVPower(self.plant_index)
        self._add_sensor(ro.PlantActivePower(self.plant_index), "Plant Power")
        self._add_sensor(ro.PlantReactivePower(self.plant_index), "Plant Power")
        self._add_sensor(plant_pv_power, group=self._consumption_group)

        self._add_sensor(ro.AvailableMaxActivePower(self.plant_index))
        self._add_sensor(ro.AvailableMinActivePower(self.plant_index))
        self._add_sensor(ro.AvailableMaxReactivePower(self.plant_index))
        self._add_sensor(ro.AvailableMinReactivePower(self.plant_index))
        self._add_sensor(ro.PlantRunningState(self.plant_index))
        self._add_sensor(ro.PlantRatedEnergyCapacity(self.plant_index))
        self._add_sensor(rw.GridMaxExportLimit(self.plant_index))
        self._add_sensor(rw.GridMaxImportLimit(self.plant_index))
        self._add_sensor(rw.PCSMaxExportLimit(self.plant_index))
        self._add_sensor(rw.PCSMaxImportLimit(self.plant_index))
        self._add_sensor(ro.TotalLoadConsumption(self.plant_index))
        self._add_sensor(ro.TotalLoadDailyConsumption(self.plant_index))

        remote_ems = rw.RemoteEMS(self.plant_index)
        remote_ems_mode = rw.RemoteEMSControlMode(self.plant_index, remote_ems)

        self._add_sensor(remote_ems)
        self._add_sensor(remote_ems_mode)
        self._add_sensor(rw.ActivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems, remote_ems_mode))
        self._add_sensor(rw.ReactivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems, remote_ems_mode))
        self._add_sensor(rw.ActivePowerPercentageAdjustmentTargetValue(self.plant_index, remote_ems, remote_ems_mode))

        self._add_sensor(rw.PVMaxPowerLimit(self.plant_index, remote_ems if fw.service_pack < 113 else None, remote_ems_mode if fw.service_pack < 113 else None))

        self._add_sensor(rw.QSAdjustmentTargetValue(self.plant_index, remote_ems, remote_ems_mode))
        self._add_sensor(rw.PowerFactorAdjustmentTargetValue(self.plant_index, remote_ems, remote_ems_mode))

        if self._device_type.has_independent_phase_power_control_interface and output_type == 2:  # L1/L2/L3/N
            independent_phase_power_control = rw.IndependentPhasePowerControl(self.plant_index, output_type)
            self._add_sensor(independent_phase_power_control)
            self._add_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "A"))
            self._add_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "A"))
            self._add_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "A"))
            self._add_sensor(rw.PhaseQSAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "A"))
            self._add_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "B"))
            self._add_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "B"))
            self._add_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "B"))
            self._add_sensor(rw.PhaseQSAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "B"))
            self._add_sensor(rw.PhaseActivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "C"))
            self._add_sensor(rw.PhaseReactivePowerFixedAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "C"))
            self._add_sensor(rw.PhaseActivePowerPercentageAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "C"))
            self._add_sensor(rw.PhaseQSAdjustmentTargetValue(self.plant_index, remote_ems_mode, independent_phase_power_control, output_type, "C"))

        address = 30098  # Starting register for Smart Load 1 Total Consumption
        for n in range(1, 25):  # Smart Loads 1 to 24
            self._add_sensor(ro.SmartLoadTotalConsumption(self.plant_index, address, n))
            self._add_sensor(ro.SmartLoadPower(self.plant_index, address + 48, n))  # Each Smart Load Total Consumption has a count of 2 registers, 24 * 2 = 48
            address += 2  # registers

        battery_power = None
        if self.has_battery:
            battery_power = ro.BatteryPower(self.plant_index)
            total_charge_energy = ro.ESSTotalChargedEnergy(self.plant_index)
            total_discharge_energy = ro.ESSTotalDischargedEnergy(self.plant_index)
            self._add_sensor(ro.PlantBatterySoC(self.plant_index))
            self._add_sensor(ro.ESSAverageCellTemperature(self.plant_index))
            self._add_sensor(battery_power, group=self._consumption_group)
            self._add_sensor(ro.AvailableMaxChargingPower(self.plant_index))
            self._add_sensor(ro.AvailableMaxDischargingPower(self.plant_index))
            self._add_sensor(ro.AvailableMaxChargingCapacity(self.plant_index))
            self._add_sensor(ro.AvailableMaxDischargingCapacity(self.plant_index))
            self._add_sensor(rated_charging_power)
            self._add_sensor(rated_discharging_power)
            self._add_sensor(ro.ChargeCutOffSoC(self.plant_index))
            self._add_sensor(ro.DischargeCutOffSoC(self.plant_index))
            self._add_sensor(ro.PlantBatterySoH(self.plant_index))
            self._add_sensor(rw.ESSBackupSOC(self.plant_index))
            self._add_sensor(rw.ESSChargeCutOffSOC(self.plant_index))
            self._add_sensor(rw.ESSDischargeCutOffSOC(self.plant_index))
            self._add_sensor(rw.MaxChargingLimit(self.plant_index, remote_ems if fw.service_pack < 113 else None, remote_ems_mode if fw.service_pack < 113 else None, cast(float, rcp_value)))
            self._add_sensor(rw.MaxDischargingLimit(self.plant_index, remote_ems if fw.service_pack < 113 else None, remote_ems_mode if fw.service_pack < 113 else None, cast(float, rdp_value)))
            self._add_sensor(total_charge_energy)
            self._add_sensor(total_discharge_energy)
            self._add_sensor(derived.BatteryChargingPower(self.plant_index, battery_power))
            self._add_sensor(derived.BatteryDischargingPower(self.plant_index, battery_power))
            self._add_sensor(derived.PlantDailyChargeEnergy(self.plant_index, total_charge_energy), search_children=False)
            self._add_sensor(derived.PlantDailyDischargeEnergy(self.plant_index, total_discharge_energy), search_children=False)

            self_consumed_power = derived.PlantSelfConsumedPower(self.plant_index)
            self._add_sensor(self_consumed_power)
            self._add_sensor(derived.PlantDailySelfConsumedEnergy(self.plant_index, self_consumed_power))

        self._add_sensor(ro.EVDCTotalChargedEnergy(self.plant_index))
        self._add_sensor(ro.EVDCTotalDischargedEnergy(self.plant_index))
        self._add_sensor(ro.PlantTotalGeneratorOutputEnergy(self.plant_index))

        self._add_sensor(rw.PlantStatus(self.plant_index))

        general_load_power = ro.GeneralLoadPower(self.plant_index)
        total_load_power = ro.TotalLoadPower(self.plant_index)
        self._add_sensor(general_load_power)
        self._add_sensor(total_load_power)
        self._add_sensor(rw.ActivePowerRegulationGradient(self.plant_index))

        self._add_sensor(ro.CurrentControlCommandValue(self.plant_index))
        self._add_sensor(ro.PlantAlarms(self.plant_index, ro.Alarm6(self.plant_index), ro.Alarm7(self.plant_index)))

        plant_3rd_party_pv_power = ro.ThirdPartyPVPower(self.plant_index) if self.protocol_version >= Protocol.V2_7 else None
        if plant_3rd_party_pv_power is None:
            total_pv_power = derived.TotalPVPower(self.plant_index, plant_pv_power)
        else:
            self._add_sensor(plant_3rd_party_pv_power, group=self._consumption_group)
            total_pv_power = derived.TotalPVPower(self.plant_index, plant_pv_power, plant_3rd_party_pv_power)
        self._add_sensor(total_pv_power, search_children=False)

        match self._consumption_source:
            case ConsumptionMethod.CALCULATED:
                if not self._grid_sensor:  # Should not be possible: unconditional registration in _register_child_devices
                    raise RuntimeError(f"{self.log_identity} GridSensor device not registered???")
                active_power = self._grid_sensor.get_sensor(GridSensorActivePower)
                if not active_power:
                    raise RuntimeError(f"{self.log_identity} GridSensorActivePower not registered in GridSensor device???")
                grid_status = self._grid_sensor.get_sensor(GridStatus)
                if not grid_status:
                    raise RuntimeError(f"{self.log_identity} GridStatus not registered in GridSensor device???")
                if battery_power is not None:
                    self._add_sensor(derived.PlantConsumedPower(self.plant_index, total_pv_power, battery_power, active_power, grid_status, method=self._consumption_source), search_children=True)
                else:
                    self._add_sensor(derived.PlantConsumedPower(self.plant_index, total_pv_power, active_power, grid_status, method=self._consumption_source), search_children=True)
            case ConsumptionMethod.GENERAL:
                self._add_sensor(derived.PlantConsumedPower(self.plant_index, general_load_power, method=self._consumption_source))
            case ConsumptionMethod.TOTAL:
                self._add_sensor(derived.PlantConsumedPower(self.plant_index, total_load_power, method=self._consumption_source))

        plant_lifetime_pv_energy = ro.PlantPVTotalGeneration(self.plant_index)
        plant_3rd_party_lifetime_pv_energy = ro.ThirdPartyLifetimePVEnergy(self.plant_index)
        total_lifetime_pv_energy = derived.TotalLifetimePVEnergy(self.plant_index, plant_lifetime_pv_energy, plant_3rd_party_lifetime_pv_energy)
        self._add_sensor(plant_lifetime_pv_energy, group="Lifetime Production")
        self._add_sensor(plant_3rd_party_lifetime_pv_energy, group="Lifetime Production")
        self._add_sensor(total_lifetime_pv_energy)
        self._add_sensor(derived.PlantDailyPVEnergy(self.plant_index, plant_lifetime_pv_energy))
        self._add_sensor(derived.TotalDailyPVEnergy(self.plant_index, total_lifetime_pv_energy))
        self._add_sensor(ro.PlantPVTotalGenerationToday(self.plant_index))
        self._add_sensor(ro.PlantPVTotalGenerationYesterday(self.plant_index))

        # Add the reserved registers to optimise sensor scanning
        self._add_sensor(ro.Reserved30073(self.plant_index))
        self._add_sensor(rw.Reserved40026(self.plant_index))
        self._add_sensor(rw.Reserved40069(self.plant_index))
