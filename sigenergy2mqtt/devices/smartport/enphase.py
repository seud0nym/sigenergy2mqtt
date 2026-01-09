if __name__ == "__main__":
    import os
    import sys

    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
    sys.path.insert(0, parent_dir)

import asyncio
import json
import logging
import os
import xml.etree.ElementTree as xml
from time import sleep
from typing import cast

import requests

# disable warnings of self signed certificate https
import urllib3

from sigenergy2mqtt.config import Config, ConsumptionMethod, Protocol
from sigenergy2mqtt.config.smart_port_config import ModuleConfig
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.base import DerivedSensor, EnergyDailyAccumulationSensor, PVPowerSensor, ReadableSensorMixin, Sensor, SubstituteMixin
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency, UnitOfPower, UnitOfReactivePower

urllib3.disable_warnings()


class EnphasePVPower(ReadableSensorMixin, Sensor, PVPowerSensor):
    def __init__(self, plant_index: int, serial_number: str, host: str, username: str, password: str):
        super().__init__(
            name="PV Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_active_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_active_power",
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,
            precision=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=Config.devices[0].scan_interval.realtime,
        )
        self["enabled_by_default"] = True

        if Config.log_level == logging.DEBUG and not self.debug_logging:
            requests_log = logging.getLogger("urllib3")
            requests_log.setLevel(logging.INFO)
            requests_log.propagate = True

        self._serial_number = serial_number
        self._host = host
        self._username = username
        self._password = password
        self._token = ""
        self._failover_initiated = False
        self._max_failures = 5
        self._max_failures_retry_interval = 30

    async def _update_internal_state(self, **kwargs) -> bool:
        reauthenticate = False if "reauthenticate" not in kwargs else kwargs["reauthenticate"]
        token = self.get_token(reauthenticate)
        url = f"https://{self._host}/ivp/meters/readings"
        headers = {"Authorization": f"Bearer {token}"}
        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Fetching data for Envoy device {self._serial_number} from {url}")
        try:
            with requests.get(url, timeout=self.scan_interval, verify=False, headers=headers) as response:
                if response.status_code == 401:
                    logging.warning(f"{self.__class__.__name__} Authentication failed: Generating new token")
                    return await self._update_internal_state(reauthenticate=True)
                elif response.status_code != 200:
                    logging.error(f"{self.__class__.__name__} Failed to connect to {url}: Response={response}")
                    raise Exception(f"{self.__class__.__name__} Failed to connect to {url}: Response={response}")
                else:
                    elapsed_time = response.elapsed.total_seconds()
                    if self.debug_logging:
                        logging.debug(f"{self.__class__.__name__} Response from {url} took {elapsed_time:.2f} seconds")
                    try:
                        reading = response.json()
                        if self.debug_logging:
                            logging.debug(f"{self.__class__.__name__} Response from {url}: JSON={json.dumps(reading)}")
                        solar = reading[0]
                        state_is = float(solar["activePower"])
                        if state_is < 0:
                            state_is = 0.0
                        self.set_state(state_is)
                        latest = self._states.pop()
                        self._states.append((latest[0], latest[1], solar))  # type: ignore
                        for sensor in self._derived_sensors.values():
                            sensor.set_source_values(self, self._states)
                        self._failover_initiated = False
                        return True
                    except ValueError as e:
                        logging.error(f"{self.__class__.__name__} Invalid JSON response from {url}: {e}")
                        raise
                    except Exception as e:
                        logging.error(f"{self.__class__.__name__} Unhandled error from {url}: {repr(e)}")
                        raise
        except requests.exceptions.RequestException as e:
            logging.error(f"{self.__class__.__name__} Unhandled exception fetching data from {url} : {e}")
            if self._failover_initiated or (self._failures + 1) < self._max_failures:
                raise
            else:
                if "TotalPVPower" in self._derived_sensors:
                    logging.info(f"{self.__class__.__name__} Failed to fetch data from {url} after {self._failures + 1} attempts, failing over to Modbus sensor")
                    self._failover_initiated = cast(SubstituteMixin, self._derived_sensors["TotalPVPower"]).failover(self)
                else:
                    logging.warning(f"{self.__class__.__name__} Failed to fetch data from {url} after {self._failures + 1} attempts, giving up and using last known state")
                    return True
        return False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API"
        return attributes

    def get_token(self, reauthenticate: bool = False) -> str:
        token_file = os.path.join(Config.persistent_state_path, f"{self.unique_id}.token")

        def load_token() -> str:
            if os.path.exists(token_file):
                with open(token_file, "r") as f:
                    try:
                        token = f.read()
                        if token:
                            if self.debug_logging:
                                logging.debug(f"Loaded authentication token from {token_file}: {token}")
                        else:
                            if self.debug_logging:
                                logging.debug(f"No authentication token found in {token_file}!")
                            token = ""
                    except Exception as e:
                        logging.warning(f"Failed to load authentication token from {token_file}: {repr(e)}")
                        token = ""
                return token
            else:
                return ""

        def save_token(token) -> None:
            with open(token_file, "w") as f:
                if self.debug_logging:
                    logging.debug(f"Saving authentication token to {token_file}: {token}")
                try:
                    f.write(token)
                except Exception as e:
                    logging.error(f"Failed to save authentication token to {token_file}: {repr(e)}")

        if reauthenticate:
            token = None
        else:
            if self._token and not self._token.isspace():
                token = self._token
                if self.debug_logging:
                    logging.debug(f"Using cached authentication token: {token}")
            else:
                token = load_token()

        if reauthenticate or not token or token == "":
            logging.info("Generating new Enphase authentication token")
            payload = {"user[email]": self._username, "user[password]": self._password}
            if self.debug_logging:
                logging.debug(f"Step 1: Authentication request payload: {payload}")
            with requests.post("https://enlighten.enphaseenergy.com/login/login.json?", data=payload) as response:
                assert response.status_code == 200, f"Failed connect to https://enlighten.enphaseenergy.com/login/login.json? to authenticate: Response={response} Payload={payload}"
                if self.debug_logging:
                    logging.debug(f"Step 1: Authentication response: {response.text}")
                response_data = json.loads(response.text)
                payload = {"session_id": response_data["session_id"], "serial_num": self._serial_number, "username": self._username}
                if self.debug_logging:
                    logging.debug(f"Step 2: Token request payload: {payload}")
                with requests.post("https://entrez.enphaseenergy.com/tokens", json=payload) as response:
                    assert response.status_code == 200, f"Failed connect to https://entrez.enphaseenergy.com/tokens to generate token: Response={response} Payload={payload}"
                    token = response.text
                    save_token(token)

        if self.debug_logging:
            logging.debug(f"Caching authentication token: {token}")
        self._token = token
        return token


class EnphaseLifetimePVEnergy(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Lifetime Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_lifetime_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_lifetime_pv_energy",
            data_type=ModbusClient.DATATYPE.UINT64,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API when EnphasePVPower derived"
        return attributes

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if not isinstance(sensor, EnphasePVPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(values[-1][2]["actEnergyDlvd"])
        return True


class EnphaseDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, serial_number: str, source: EnphaseLifetimePVEnergy):
        super().__init__(
            name="Daily Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_daily_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_daily_pv_energy",
            source=source,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API when EnphasePVPower derived"
        return attributes


class EnphaseCurrent(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Current",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_current",
            data_type=ModbusClient.DATATYPE.INT32,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-dc",
            gain=1,
            precision=2,
        )
        self["enabled_by_default"] = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API when EnphasePVPower derived"
        return attributes

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if not isinstance(sensor, EnphasePVPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(values[-1][2]["current"])
        return True


class EnphaseFrequency(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Frequency",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_frequency",
            data_type=ModbusClient.DATATYPE.UINT16,
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=1,
            precision=2,
        )
        self["enabled_by_default"] = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API when EnphasePVPower derived"
        return attributes

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if not isinstance(sensor, EnphasePVPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(values[-1][2]["freq"])
        return True


class EnphasePowerFactor(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Power Factor",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_power_factor",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_power_factor",
            data_type=ModbusClient.DATATYPE.UINT16,
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            state_class=None,
            icon="mdi:angle-acute",
            gain=1,
            precision=2,
        )
        self["enabled_by_default"] = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API when EnphasePVPower derived"
        return attributes

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if not isinstance(sensor, EnphasePVPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(values[-1][2]["pwrFactor"])
        return True


class EnphaseReactivePower(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Reactive Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_reactive_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_reactive_power",
            data_type=ModbusClient.DATATYPE.UINT32,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:transmission-tower",
            gain=1000,
            precision=2,
        )
        self["enabled_by_default"] = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API when EnphasePVPower derived"
        return attributes

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if not isinstance(sensor, EnphasePVPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(values[-1][2]["reactivePower"])
        return True


class EnphaseVoltage(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Voltage",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_voltage",
            data_type=ModbusClient.DATATYPE.UINT16,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=1,
            precision=1,
        )
        self["enabled_by_default"] = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Enphase Envoy API when EnphasePVPower derived"
        return attributes

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if not isinstance(sensor, EnphasePVPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(values[-1][2]["voltage"])
        return True


class SmartPort(Device):
    @classmethod
    def _get_text(cls, root: xml.Element, path: str) -> str:
        element = root.find(path)
        return element.text if element is not None and element.text else ""

    def __init__(self, plant_index: int, config: ModuleConfig):
        fw: str = ""
        sn: str = ""
        pn: str = ""
        if config.testing:
            logging.debug(f"SmartPort {plant_index} testing mode enabled")
            fw = "D7.0.0"
            sn = "123456789012"
            pn = "Envoy-S"
        else:
            url = f"http://{config.host}/info"
            for i in range(1, 4, 1):
                with requests.Session() as session:
                    try:
                        with session.get(url, timeout=20, verify=False) as response:
                            if response.status_code == 200:
                                root = xml.fromstring(response.content)
                                sn = self._get_text(root, "./device/sn")
                                pn = self._get_text(root, "./device/pn")
                                fw = self._get_text(root, "./device/software")
                                assert fw.startswith("D7") or fw.startswith("D8"), f"Unsupported Enphase Envoy firmware {fw}"
                                break
                            else:
                                logging.error(f"SmartPort Failed to initialise from {url} (Attempt #{i}) - Response code was {response.status_code}")
                    except requests.exceptions.ConnectionError as e:
                        logging.error(f"SmartPort Failed to initialise from {url} (Attempt #{i}): {e}")
                sleep(10)
            else:
                raise Exception(f"Unable to initialise from {url} after 3 attempts")
        unique_id = f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_envoy_{sn}"
        name = "Sigenergy Plant Smart-Port" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1} Smart-Port"
        super().__init__(name, plant_index, unique_id, "Enphase", "Envoy", Protocol.N_A, mdl_id=pn, sn=sn, hw=fw)

        pv_power = EnphasePVPower(plant_index, sn, config.host, config.username, config.password)
        lifetime_pv_energy = EnphaseLifetimePVEnergy(plant_index, sn)
        self._add_read_sensor(pv_power, "Consumption" if Config.consumption == ConsumptionMethod.CALCULATED else None)
        self._add_derived_sensor(lifetime_pv_energy, pv_power)
        self._add_derived_sensor(EnphaseDailyPVEnergy(plant_index, sn, lifetime_pv_energy), lifetime_pv_energy)
        self._add_derived_sensor(EnphaseCurrent(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphaseFrequency(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphasePowerFactor(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphaseReactivePower(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphaseVoltage(plant_index, sn), pv_power)

    def _init_from_enphase_info(self, config):
        return None, None, None


if __name__ == "__main__":
    logging.getLogger("root").setLevel(logging.DEBUG)
    Config.sensor_debug_logging = True

    async def test():
        smartport = SmartPort(0, Config.devices[0].smartport.module)
        print(smartport)
        pv_power_unique_id = f"{Config.home_assistant.unique_id_prefix}_0_enphase_{smartport['serial_number']}_active_power"
        sensor = smartport.get_sensor(pv_power_unique_id)
        if sensor:
            sensor.debug_logging = True
            print(f"{sensor.name} =  {await sensor.get_state()}")
            for derived in sensor._derived_sensors.values():
                print(f"{derived.name} =  {await derived.get_state()}")
        else:
            print(f"Sensor '{pv_power_unique_id}' not found!!!")

    asyncio.run(test(), debug=True)
