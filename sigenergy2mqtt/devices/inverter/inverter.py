import asyncio
import logging
import re
from typing import cast

import sigenergy2mqtt.sensors.inverter_read_only as ro
import sigenergy2mqtt.sensors.inverter_read_write as rw
from sigenergy2mqtt.common import DeviceType, FirmwareVersion, HybridInverter, Protocol, PVInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient

from .ess import ESS
from .pv_string import PVString


class Inverter(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        device_type: DeviceType,
        protocol_version: Protocol,
        model_id: str,
        serial: str,
        firmware: str,
    ):
        match = re.match(r"^[^\d]*", model_id)
        words = (match.group(0).rstrip() if match else model_id).replace("EC", "Energy Controller", 1).split()
        words.insert(1, serial)
        name = " ".join(words)

        super().__init__(
            type=device_type,
            name=name,
            plant_index=plant_index,
            device_address=device_address,
            model=device_type.__str__(),
            protocol_version=protocol_version,
            translate=False,
            # HA device registry attributes
            sn=serial,
            hw=firmware,  # MUST use hw abbreviation - see InverterFirmwareVersion
            model_id=model_id,
            serial=serial,
        )

    @classmethod
    async def create(cls, plant_index: int, device_address: int, device_type: DeviceType, protocol_version: Protocol, modbus_client: ModbusClient) -> "Inverter":
        model = ro.InverterModel(plant_index, device_address)
        pv_string_count = ro.PVStringCount(plant_index, device_address)
        firmware_version = ro.InverterFirmwareVersion(plant_index, device_address)
        serial_number = ro.InverterSerialNumber(plant_index, device_address)
        pack_bcu_count = ro.PACKBCUCount(plant_index, device_address)
        # Fetch async values in parallel
        firmware, model_id, battery_count, strings, serial = await asyncio.gather(
            firmware_version.get_state(modbus_client=modbus_client),
            model.get_state(modbus_client=modbus_client),
            pack_bcu_count.get_state(modbus_client=modbus_client),
            pv_string_count.get_state(modbus_client=modbus_client),
            serial_number.get_state(modbus_client=modbus_client),
        )

        try:
            parsed_firmware = FirmwareVersion(cast(str, firmware))
            if active_config.ems_mode_check and parsed_firmware.service_pack >= 113:
                logging.info(f"Disabling Remote EMS Mode check because PV Max Power and ESS Charge/Discharge limits are globally available in firmware {firmware}")
                active_config.ems_mode_check = False
        except ValueError:
            logging.debug(f"Unable to parse firmware version '{firmware}' for ems_mode_check enforcement")

        inverter = cls(plant_index, device_address, device_type, protocol_version, cast(str, model_id), cast(str, serial), cast(str, firmware))
        await inverter._register_child_devices(plant_index, device_address, device_type, protocol_version, cast(str, model_id), cast(str, serial), cast(int, strings), cast(int, battery_count))
        await inverter._register_sensors(plant_index, device_address, pv_string_count, firmware_version, model, serial_number, pack_bcu_count, modbus_client)
        return inverter

    async def _register_child_devices(
        self,
        plant_index: int,
        device_address: int,
        device_type: DeviceType,
        protocol_version: Protocol,
        model_id: str,
        serial: str,
        strings: int,
        battery_count: int,
    ) -> None:
        address = 31027
        for n in range(1, min(4, strings) + 1):
            self._add_child_device(PVString(plant_index, device_address, device_type, model_id, serial, n, address, address + 1, Protocol.V1_8))
            address += 2
        if protocol_version >= Protocol.V2_4:
            address = 31042
            for n in range(5, min(16, strings) + 1):
                self._add_child_device(PVString(plant_index, device_address, device_type, model_id, serial, n, address, address + 1, Protocol.V2_4))
                address += 2
        if protocol_version >= Protocol.V2_8 and isinstance(device_type, PVInverter):
            address = 31066
            for n in range(17, min(36, strings) + 1):
                self._add_child_device(PVString(plant_index, device_address, device_type, model_id, serial, n, address, address + 1, Protocol.V2_8))
                address += 2

        if isinstance(device_type, HybridInverter):
            if battery_count > 0:
                self._add_child_device(ESS(plant_index, device_address, device_type, protocol_version, model_id, serial))
            else:
                logging.debug(f"{self.__class__.__name__} Skipped creating ESS device: {battery_count=}")

    async def _register_sensors(
        self,
        plant_index: int,
        device_address: int,
        pv_string_count: ro.PVStringCount,
        firmware_version: ro.InverterFirmwareVersion,
        model: ro.InverterModel,
        serial_number: ro.InverterSerialNumber,
        pack_bcu_count: ro.PACKBCUCount,
        modbus_client: ModbusClient,
    ) -> None:
        output_type = ro.OutputType(plant_index, device_address)
        power_phases = ro.OutputType.to_phases(await output_type.get_state(modbus_client=modbus_client))

        active_power = ro.ActivePower(plant_index, device_address)
        reactive_power = ro.ReactivePower(plant_index, device_address)

        self._add_read_sensor(model)
        self._add_read_sensor(serial_number)
        self._add_read_sensor(firmware_version)
        self._add_read_sensor(ro.RatedActivePower(plant_index, device_address))
        self._add_read_sensor(ro.MaxRatedApparentPower(plant_index, device_address))
        self._add_read_sensor(ro.InverterMaxActivePower(plant_index, device_address))
        self._add_read_sensor(ro.MaxAbsorptionPower(plant_index, device_address))
        self._add_read_sensor(ro.InverterRunningState(plant_index, device_address))
        self._add_read_sensor(ro.MaxActivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(ro.MinActivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(ro.MaxReactivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(ro.MinReactivePowerAdjustment(plant_index, device_address))
        self._add_read_sensor(active_power)
        self._add_read_sensor(reactive_power)
        self._add_read_sensor(ro.InverterPCSAlarm(plant_index, device_address, ro.InverterAlarm1(plant_index, device_address), ro.InverterAlarm2(plant_index, device_address)))
        self._add_read_sensor(ro.InverterAlarm4(plant_index, device_address))
        self._add_read_sensor(ro.RatedGridVoltage(plant_index, device_address))
        self._add_read_sensor(ro.RatedGridFrequency(plant_index, device_address))
        self._add_read_sensor(ro.GridFrequency(plant_index, device_address))
        self._add_read_sensor(ro.InverterTemperature(plant_index, device_address))
        self._add_read_sensor(output_type)
        self._add_read_sensor(ro.PhaseVoltage(plant_index, device_address, "A", power_phases))
        self._add_read_sensor(ro.PhaseCurrent(plant_index, device_address, "A", power_phases))
        if power_phases > 1:
            self._add_read_sensor(ro.PhaseVoltage(plant_index, device_address, "B", power_phases))
            self._add_read_sensor(ro.PhaseCurrent(plant_index, device_address, "B", power_phases))
        if power_phases > 2:
            self._add_read_sensor(ro.PhaseVoltage(plant_index, device_address, "C", power_phases))
            self._add_read_sensor(ro.PhaseCurrent(plant_index, device_address, "C", power_phases))
            self._add_read_sensor(ro.LineVoltage(plant_index, device_address, "A-B"))
            self._add_read_sensor(ro.LineVoltage(plant_index, device_address, "B-C"))
            self._add_read_sensor(ro.LineVoltage(plant_index, device_address, "C-A"))
        self._add_read_sensor(ro.PowerFactor(plant_index, device_address, active_power, reactive_power))
        self._add_read_sensor(ro.MPPTCount(plant_index, device_address))
        self._add_read_sensor(pack_bcu_count)
        self._add_read_sensor(pv_string_count)
        self._add_read_sensor(ro.InverterPVPower(plant_index, device_address))
        self._add_read_sensor(ro.InsulationResistance(plant_index, device_address))
        self._add_read_sensor(ro.StartupTime(plant_index, device_address))
        self._add_read_sensor(ro.ShutdownTime(plant_index, device_address))

        self._add_read_sensor(rw.InverterActivePowerFixedValueAdjustment(plant_index, device_address))
        self._add_read_sensor(rw.InverterReactivePowerFixedValueAdjustment(plant_index, device_address))
        self._add_read_sensor(rw.InverterActivePowerPercentageAdjustment(plant_index, device_address))
        self._add_read_sensor(rw.InverterReactivePowerQSAdjustment(plant_index, device_address))
        self._add_read_sensor(rw.InverterPowerFactorAdjustment(plant_index, device_address))
        self._add_writeonly_sensor(rw.InverterStatus(plant_index, device_address))

        self._add_read_sensor(ro.InverterPVLifetimeGeneration(plant_index, device_address))
        self._add_read_sensor(ro.InverterPVDailyGeneration(plant_index, device_address))

        self._add_read_sensor(ro.InverterActivePowerFixedValueAdjustmentFeedback(plant_index, device_address))
        self._add_read_sensor(ro.InverterReactivePowerFixedValueAdjustmentFeedback(plant_index, device_address))
        self._add_read_sensor(ro.InverterActivePowerPercentageAdjustmentFeedback(plant_index, device_address))
        self._add_read_sensor(ro.InverterReactivePowerPercentageAdjustmentFeedback(plant_index, device_address))
        self._add_read_sensor(ro.InverterPowerFactorAdjustmentFeedback(plant_index, device_address))

        # Add the reserved registers to optimise sensor scanning
        self._add_read_sensor(ro.ReservedDailyExportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.ReservedAccumulatedExportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.ReservedDailyImportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.ReservedAccumulatedImportEnergy(plant_index, device_address))
        self._add_read_sensor(ro.Reserved30610(plant_index, device_address))
        self._add_read_sensor(rw.ReservedGridCode(plant_index, device_address))
        self._add_read_sensor(rw.ReservedInverterRemoteEMSDispatch(plant_index, device_address))
