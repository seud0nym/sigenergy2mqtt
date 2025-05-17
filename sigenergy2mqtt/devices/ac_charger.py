from .device import ModBusDevice
from sigenergy2mqtt.sensors.base import RemoteEMSMixin
import sigenergy2mqtt.sensors.ac_charger_read_only as ro
import sigenergy2mqtt.sensors.ac_charger_read_write as rw


class ACCharger(ModBusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        remote_ems: RemoteEMSMixin,
        ib_value: float,
        rc_value: float,
        input_breaker: ro.ACChargerInputBreaker,
        rated_current: ro.ACChargerRatedCurrent,
    ):
        super().__init__(None, "Sigenergy AC Charger", plant_index, device_address, "AC Charger")

        self._add_read_sensor(ro.ACChargerRunningState(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerTotalEnergyConsumed(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerChargingPower(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerRatedPower(plant_index, device_address))
        self._add_read_sensor(rated_current)
        self._add_read_sensor(ro.ACChargerRatedVoltage(plant_index, device_address))
        self._add_read_sensor(input_breaker)
        self._add_read_sensor(
            ro.ACChargerAlarms(
                plant_index, device_address, ro.ACChargerAlarm1(plant_index, device_address), ro.ACChargerAlarm2(plant_index, device_address), ro.ACChargerAlarm3(plant_index, device_address)
            )
        )
        self._add_read_sensor(rw.ACChargerOutputCurrent(remote_ems, plant_index, device_address, ib_value, rc_value))

        self._add_writeonly_sensor(rw.ACChargerStatus(plant_index, device_address))
