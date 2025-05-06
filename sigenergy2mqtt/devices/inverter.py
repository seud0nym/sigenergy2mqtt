from .device import ModBusDevice
from sigenergy2mqtt.devices.inverter_ess import ESS
from sigenergy2mqtt.devices.inverter_pv_string import PVString
from sigenergy2mqtt.devices.types import DeviceType
from sigenergy2mqtt.sensors.base import RemoteEMSMixin
import re
import sigenergy2mqtt.sensors.inverter_derived as derived
import sigenergy2mqtt.sensors.inverter_read_only as ro
import sigenergy2mqtt.sensors.inverter_read_write as rw


class Inverter(ModBusDevice):
    def __init__(
        self,
        plant_index: int,
        remote_ems: RemoteEMSMixin,
        device_address: int,
        device_type: DeviceType,
        model_id: str,
        serial: str,
        firmware: str,
        strings: int,
        power_phases: int,
        pv_string_count: ro.PVStringCount,
        output_type: ro.OutputType,
        firmware_version: ro.InverterFirmwareVersion,
    ):
        assert 2 <= strings <= 16, f"Invalid PV String Count ({strings} - must be between 2 and 16)"
        match = re.match(r"^[^\d]*", model_id)
        words = (match.group(0).rstrip() if match else model_id).replace('EC', 'Energy Controller', 1).split()
        words.insert(1, serial)
        name = " ".join(words)

        super().__init__(device_type, name, plant_index, device_address, model=device_type.__str__(), mdl_id=model_id, sn=serial, hw=firmware)

        pv_power = ro.InverterPVPower(plant_index, device_address)

        # region read sensors
        self._add_read_sensor(firmware_version)
        self._add_read_sensor(ro.RatedActivePower(plant_index, device_address))
        self._add_read_sensor(ro.MaxRatedApparentPower(plant_index, device_address))
        self._add_read_sensor(ro.InverterMaxActivePower(plant_index, device_address))
        self._add_read_sensor(ro.MaxAbsorptionPower(plant_index, device_address))
        self._add_read_sensor(ro.DailyExportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.AccumulatedExportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.DailyImportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.AccumulatedImportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.InverterRunningState(plant_index, device_address))
        self._add_read_sensor(ro.MaxActivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(ro.MinActivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(ro.MaxReactivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(ro.MinReactivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(ro.ActivePower(plant_index, device_address))
        self._add_read_sensor(ro.ReactivePower(plant_index, device_address))
        self._add_read_sensor(ro.InverterPCSAlarm(plant_index, device_address, ro.InverterAlarm1(plant_index, device_address), ro.InverterAlarm2(plant_index, device_address)))
        self._add_read_sensor(ro.InverterAlarm4(plant_index, device_address))
        self._add_read_sensor(ro.RatedGridVoltage(plant_index, device_address))
        self._add_read_sensor(ro.RatedGridFrequency(plant_index, device_address))
        self._add_read_sensor(ro.GridFrequency(plant_index, device_address))
        self._add_read_sensor(ro.InverterTemperature(plant_index, device_address))
        self._add_read_sensor(output_type)
        self._add_read_sensor(ro.PhaseAVoltage(plant_index, device_address))
        self._add_read_sensor(ro.PhaseACurrent(plant_index, device_address))
        if power_phases > 1:
            self._add_read_sensor(ro.PhaseBVoltage(plant_index, device_address))
            self._add_read_sensor(ro.PhaseBCurrent(plant_index, device_address))
            self._add_read_sensor(ro.ABLineVoltage(plant_index, device_address))
        if power_phases > 2:
            self._add_read_sensor(ro.PhaseCVoltage(plant_index, device_address))
            self._add_read_sensor(ro.PhaseCCurrent(plant_index, device_address))
            self._add_read_sensor(ro.BCLineVoltage(plant_index, device_address))
            self._add_read_sensor(ro.CALineVoltage(plant_index, device_address))
        self._add_read_sensor(ro.PowerFactor(plant_index, device_address))
        self._add_read_sensor(ro.PACKBCUCount(plant_index, device_address))
        self._add_read_sensor(ro.MPTTCount(plant_index, device_address))
        self._add_read_sensor(pv_string_count)
        self._add_read_sensor(pv_power)
        self._add_read_sensor(ro.InsulationResistance(plant_index, device_address))
        self._add_read_sensor(ro.StartupTime(plant_index, device_address))
        self._add_read_sensor(ro.ShutdownTime(plant_index, device_address))

        address = 31027
        for n in range(1, min(4, strings) + 1):
            self._add_child_device(PVString(plant_index, device_address, device_type, model_id, serial, n, address, address + 1))
            address += 2
        address = 31042
        for n in range(5, strings + 1):
            self._add_child_device(PVString(plant_index, device_address, device_type, model_id, serial, n, address, address + 1))
            address += 2
        # endregion

        self._add_read_sensor(rw.GridCode(plant_index, device_address))
        self._add_read_sensor(rw.InverterRemoteEMSDispatch(remote_ems, plant_index, device_address))
        self._add_read_sensor(rw.InverterActivePowerFixedValueAdjustment(remote_ems, plant_index, device_address))
        self._add_read_sensor(rw.InverterReactivePowerFixedValueAdjustment(remote_ems, plant_index, device_address))
        self._add_read_sensor(rw.InverterActivePowerPercentageAdjustment(remote_ems, plant_index, device_address))
        self._add_read_sensor(rw.InverterReactivePowerQSAdjustment(remote_ems, plant_index, device_address))
        self._add_read_sensor(rw.InverterPowerFactorAdjustment(remote_ems, plant_index, device_address))
        self._add_writeonly_sensor(rw.InverterStatus(plant_index, device_address))

        lifetime_pv_energy = derived.InverterLifetimePVEnergy(plant_index, device_address, pv_power)
        self._add_derived_sensor(lifetime_pv_energy, pv_power)
        self._add_derived_sensor(derived.InverterDailyPVEnergy(plant_index, device_address, lifetime_pv_energy), lifetime_pv_energy)

        self._add_child_device(ESS(plant_index, device_address, device_type, model_id, serial))
