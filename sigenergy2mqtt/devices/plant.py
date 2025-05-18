from .device import ModBusDevice
from .grid_sensor import GridSensor
from .types import DeviceType
from sigenergy2mqtt.config import Config, SIGENERGY_MODBUS_PROTOCOL
from sigenergy2mqtt.devices.inverter import Inverter
from sigenergy2mqtt.sensors.base import Sensor
import importlib
import logging
import sigenergy2mqtt.sensors.plant_derived as derived
import sigenergy2mqtt.sensors.plant_read_only as ro
import sigenergy2mqtt.sensors.plant_read_write as rw


class PowerPlant(ModBusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        power_phases: int,
        rcp_value: float,
        rdp_value: float,
        rated_charging_power: ro.PlantRatedChargingPower,
        rated_discharging_power: ro.PlantRatedDischargingPower,
    ):
        name = "Sigenergy Plant" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1}"
        super().__init__(device_type, name, plant_index, 247, "Energy Management System", sw=f"Modbus Protocol {SIGENERGY_MODBUS_PROTOCOL}")
        grid_sensor_active_power = ro.GridSensorActivePower(plant_index)
        plant_pv_power = ro.PlantPVPower(plant_index)
        battery_power = ro.BatteryPower(plant_index)

        self._add_read_sensor(ro.SystemTime(plant_index))
        self._add_read_sensor(ro.SystemTimeZone(plant_index))
        self._add_read_sensor(ro.EMSWorkMode(plant_index))
        self._add_read_sensor(ro.MaxActivePower(plant_index))
        self._add_read_sensor(ro.MaxApparentPower(plant_index))
        self._add_read_sensor(ro.PlantBatterySoC(plant_index))
        self._add_read_sensor(ro.PlantPhaseAActivePower(plant_index))
        self._add_read_sensor(ro.PlantPhaseAReactivePower(plant_index))
        if power_phases > 1:
            self._add_read_sensor(ro.PlantPhaseBActivePower(plant_index))
            self._add_read_sensor(ro.PlantPhaseBReactivePower(plant_index))
        if power_phases > 2:
            self._add_read_sensor(ro.PlantPhaseCActivePower(plant_index))
            self._add_read_sensor(ro.PlantPhaseCReactivePower(plant_index))
        self._add_read_sensor(ro.GeneralPCSAlarm(plant_index, ro.GeneralAlarm1(plant_index), ro.GeneralAlarm2(plant_index)))
        self._add_read_sensor(ro.GeneralAlarm3(plant_index))
        self._add_read_sensor(ro.GeneralAlarm4(plant_index))
        if len(Config.devices[plant_index].dc_chargers) > 0:
            self._add_read_sensor(ro.GeneralAlarm5(plant_index))
        self._add_read_sensor(ro.PlantActivePower(plant_index))
        self._add_read_sensor(ro.PlantReactivePower(plant_index))
        self._add_read_sensor(plant_pv_power, "consumption")
        self._add_read_sensor(battery_power, "consumption")
        self._add_read_sensor(ro.AvailableMaxActivePower(plant_index))
        self._add_read_sensor(ro.AvailableMinActivePower(plant_index))
        self._add_read_sensor(ro.AvailableMaxReactivePower(plant_index))
        self._add_read_sensor(ro.AvailableMinReactivePower(plant_index))
        self._add_read_sensor(ro.AvailableMaxChargingPower(plant_index))
        self._add_read_sensor(ro.AvailableMaxDischargingPower(plant_index))
        self._add_read_sensor(ro.PlantRunningState(plant_index))
        self._add_read_sensor(ro.AvailableMaxChargingCapacity(plant_index))
        self._add_read_sensor(ro.AvailableMaxDischargingCapacity(plant_index))
        self._add_read_sensor(rated_charging_power)
        self._add_read_sensor(rated_discharging_power)
        self._add_read_sensor(ro.PlantRatedEnergyCapacity(plant_index))
        self._add_read_sensor(ro.ChargeCutOffSoC(plant_index))
        self._add_read_sensor(ro.DischargeCutOffSoC(plant_index))
        self._add_read_sensor(ro.PlantBatterySoH(plant_index))

        remote_ems = rw.RemoteEMS(plant_index)
        control_mode = rw.RemoteEMSControlMode(plant_index, remote_ems)
        self._add_read_sensor(remote_ems)
        self._add_read_sensor(control_mode)
        self._add_read_sensor(rw.ActivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.ReactivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.ActivePowerPercentageAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.QSAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.PowerFactorAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.PhaseAActivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.PhaseAReactivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.PhaseAActivePowerPercentageAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.PhaseAQSAdjustmentTargetValue(plant_index, remote_ems))
        if power_phases > 1:
            self._add_read_sensor(rw.PhaseBActivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
            self._add_read_sensor(rw.PhaseBReactivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
            self._add_read_sensor(rw.PhaseBActivePowerPercentageAdjustmentTargetValue(plant_index, remote_ems))
            self._add_read_sensor(rw.PhaseBQSAdjustmentTargetValue(plant_index, remote_ems))
            self._add_read_sensor(rw.IndependentPhasePowerControl(plant_index, remote_ems))
            self._add_read_sensor(rw.PhaseCActivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
            self._add_read_sensor(rw.PhaseCReactivePowerFixedAdjustmentTargetValue(plant_index, remote_ems))
            self._add_read_sensor(rw.PhaseCActivePowerPercentageAdjustmentTargetValue(plant_index, remote_ems))
            self._add_read_sensor(rw.PhaseCQSAdjustmentTargetValue(plant_index, remote_ems))
        self._add_read_sensor(rw.MaxChargingLimit(plant_index, remote_ems, rcp_value, control_mode))
        self._add_read_sensor(rw.MaxDischargingLimit(plant_index, remote_ems, rdp_value, control_mode))
        self._add_read_sensor(rw.PVMaxPowerLimit(plant_index, remote_ems, control_mode))
        self._add_read_sensor(rw.GridMaxExportLimit(plant_index, remote_ems))
        self._add_read_sensor(rw.GridMaxImportLimit(plant_index, remote_ems))
        self._add_read_sensor(rw.PCSMaxExportLimit(plant_index, remote_ems))
        self._add_read_sensor(rw.PCSMaxImportLimit(plant_index, remote_ems))

        self._add_writeonly_sensor(rw.PlantStatus(plant_index))

        self._add_child_device(GridSensor(plant_index, device_type, power_phases, grid_sensor_active_power))

        total_pv_power = None
        if Config.devices[plant_index].smartport.enabled:
            total_pv_power = derived.TotalPVPower(plant_index, plant_pv_power)
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
                                total_pv_power.register_source_sensors(sensor)
                                self._add_derived_sensor(total_pv_power, plant_pv_power, sensor, search_children=True)
                                plant_pv_power["enabled_by_default"] = False
                                break
                except Exception as exc:
                    logging.error(f"{self.__class__.__name__} Failed to create SmartPort instance - {exc}")
                    raise

        plant_consumed_power = derived.PlantConsumedPower(plant_index)
        if total_pv_power is None:
            self._add_derived_sensor(plant_consumed_power, plant_pv_power, battery_power, grid_sensor_active_power, search_children=True)
            plant_lifetime_pv_energy = derived.PlantLifetimePVEnergy(plant_index, plant_pv_power)
            self._add_derived_sensor(plant_lifetime_pv_energy, plant_pv_power)
        else:
            self._add_derived_sensor(plant_consumed_power, total_pv_power, battery_power, grid_sensor_active_power, search_children=True)
            plant_lifetime_pv_energy = derived.PlantLifetimePVEnergy(plant_index, total_pv_power)
            self._add_derived_sensor(plant_lifetime_pv_energy, total_pv_power)
        self._add_derived_sensor(derived.PlantDailyPVEnergy(plant_index, plant_lifetime_pv_energy), plant_lifetime_pv_energy)

        plant_lifetime_consumed_energy = derived.PlantLifetimeConsumedEnergy(plant_index, plant_consumed_power)
        self._add_derived_sensor(plant_lifetime_consumed_energy, plant_consumed_power)
        self._add_derived_sensor(derived.PlantDailyConsumedEnergy(plant_index, plant_lifetime_consumed_energy), plant_lifetime_consumed_energy)

        self._add_derived_sensor(derived.BatteryChargingPower(plant_index, battery_power), battery_power)
        self._add_derived_sensor(derived.BatteryDischargingPower(plant_index, battery_power), battery_power)

    def add_ess_accumulation_sensors(self, plant_index, *inverters: Inverter):
        sensors: dict[str, list[Sensor]] = {}
        for inverter in inverters:
            for address in (30566, 30568, 30572, 30574):
                sensor = inverter.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{inverter.device_address:03d}_{address}", search_children=True)
                classname = sensor.__class__.__name__
                if classname not in sensors:
                    sensors[classname] = []
                sensors[classname].append(sensor)
        self._add_read_sensor(derived.PlantDailyChargeEnergy(plant_index, *sensors["DailyChargeEnergy"]))
        self._add_read_sensor(derived.PlantDailyDischargeEnergy(plant_index, *sensors["DailyDischargeEnergy"]))
        self._add_read_sensor(derived.PlantAccumulatedChargeEnergy(plant_index, *sensors["AccumulatedChargeEnergy"]))
        self._add_read_sensor(derived.PlantAccumulatedDischargeEnergy(plant_index, *sensors["AccumulatedDischargeEnergy"]))
