import sigenergy2mqtt.sensors.ac_charger_read_only as ro
import sigenergy2mqtt.sensors.ac_charger_read_write as rw
from sigenergy2mqtt.common import Protocol

from .device import ModbusDevice


class ACCharger(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
        ib_value: float | None,
        rc_value: float | None,
        input_breaker: ro.ACChargerInputBreaker | None,
        rated_current: ro.ACChargerRatedCurrent | None,
    ):
        assert ib_value is not None, "Input Breaker value cannot be None"
        assert rc_value is not None, "Rated Current value cannot be None"
        assert input_breaker is not None, "ACChargerInputBreaker instance cannot be None"
        assert rated_current is not None, "ACChargerRatedCurrent instance cannot be None"
        super().__init__(None, "Sigenergy AC Charger", plant_index, device_address, "AC Charger", protocol_version)

        self._add_read_sensor(ro.ACChargerRunningState(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerTotalEnergyConsumed(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerChargingPower(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerRatedPower(plant_index, device_address))
        self._add_read_sensor(rated_current)
        self._add_read_sensor(ro.ACChargerRatedVoltage(plant_index, device_address))
        self._add_read_sensor(input_breaker)
        self._add_read_sensor(
            ro.ACChargerAlarms(
                plant_index,
                device_address,
                ro.ACChargerAlarm1(plant_index, device_address),
                ro.ACChargerAlarm2(plant_index, device_address),
                ro.ACChargerAlarm3(plant_index, device_address),
            )
        )
        self._add_read_sensor(rw.ACChargerOutputCurrent(plant_index, device_address, ib_value, rc_value))

        self._add_writeonly_sensor(rw.ACChargerStatus(plant_index, device_address))
