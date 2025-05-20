if __name__ == "__main__":
    import os
    import sys

    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
    sys.path.insert(0, parent_dir)

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.config.smart_port_config import ModuleConfig
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.sensors.base import DerivedSensor, EnergyDailyAccumulationSensor, PVPowerSensor, ReadableSensorMixin, Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency, UnitOfPower, UnitOfReactivePower
import asyncio
import json
import logging
import os
import requests
import xml.etree.ElementTree as xml


# disable warnings of self signed certificate https
import urllib3

urllib3.disable_warnings()


class EnphasePVPower(Sensor, PVPowerSensor, ReadableSensorMixin):
    def __init__(self, plant_index: int, serial_number: str, host: str, username: str, password: str):
        Sensor.__init__(
            self,
            name="PV Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_active_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_active_power",
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,
            precision=2,
        )
        ReadableSensorMixin.__init__(self, 5)
        self["enabled_by_default"] = True

        if Config.log_level == logging.DEBUG and not self._debug_logging:
            requests_log = logging.getLogger("urllib3")
            requests_log.setLevel(logging.INFO)
            requests_log.propagate = True

        self._serial_number = serial_number
        self._host = host
        self._username = username
        self._password = password
        self._token = ""

    async def _update_internal_state(self, **kwargs) -> bool:
        """Retrieves the current state of this sensor and updates the internal state history.

        Args:
            **kwargs    Implementation specific arguments.

        Returns:
            True if the internal state was updated, False if it was not.
        """
        reauthenticate = False if "reauthenticate" not in kwargs else kwargs["reauthenticate"]
        token = self.get_token(reauthenticate)
        try:
            url = f"https://{self._host}/ivp/meters/readings"
            headers = {"Authorization": f"Bearer {token}"}
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} - Fetching data for Envoy device {self._serial_number} from {url}")
            with requests.get(url, timeout=self.scan_interval, verify=False, headers=headers) as response:
                if response.status_code == 401:
                    logging.error(f"{self.__class__.__name__} - Authentication failed: Generating new token")
                    return await self._update_internal_state(reauthenticate=True)
                elif response.status_code != 200:
                    logging.error(f"{self.__class__.__name__} - Failed to connect to {url}: Response={response}")
                    raise Exception(f"{self.__class__.__name__} - Failed to connect to {url}: Response={response}")
                else:
                    elapsed_time = response.elapsed.total_seconds()
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Response from {url} took {elapsed_time:.2f} seconds")
                    try:
                        reading = response.json()
                        if self._debug_logging:
                            logging.debug(f"{self.__class__.__name__} - Response from {url}: JSON={json.dumps(reading)}")
                        solar = reading[0]
                        state_is = float(solar["activePower"])
                        if state_is < 0:
                            state_is = 0.0
                        if self.gain != 1:
                            state_is = state_is / self.gain
                        self.set_state(state_is)
                        self._states[-1] = (self._states[-1][0], self._states[-1][1], solar)
                        for sensor in self._derived_sensors.values():
                            sensor.set_source_values(self, self._states)
                        return True
                    except ValueError as e:
                        logging.error(f"{self.__class__.__name__} - Invalid JSON response from {url}: {e}")
                        raise
                    except Exception as e:
                        logging.error(f"{self.__class__.__name__} - Unhandled error from {url}: {e}")
                        raise
        except requests.exceptions.RequestException as e:
            logging.error(f"{self.__class__.__name__} - Unhandled exception fetching data from {url} : {e}")
            raise
        return False

    def get_token(self, reauthenticate: bool = False) -> str:
        """Return an Enphase authentication token for the specified device.

        Args:
            new:        True if a new token is to be generated, or False to use
                        a previously generated token. Ignored and defaults to
                        True if the token does not exist or is no longer valid.

        Returns:
            The authentication token.
        """

        token_file = os.path.join(Config.persistent_state_path, f"{self.unique_id}.token")

        def load_token() -> str:
            """Loads an Enphase authentication token from persistent storage.

            Returns:
                The authentication token if found, or an empty string.
            """
            if os.path.exists(token_file):
                with open(token_file, "r") as f:
                    try:
                        token = f.read()
                        if token:
                            if self._debug_logging:
                                logging.debug(f"Loaded authentication token from {token_file}: {token}")
                        else:
                            if self._debug_logging:
                                logging.debug(f"No authentication token found in {token_file}!")
                            token = ""
                    except Exception as e:
                        logging.error(f"Failed to load authentication token from {token_file}: {e}")
                        token = ""
                return token
            else:
                return ""

        def save_token(token) -> None:
            """Saves an Enphase authentication token to persistent storage.

            Args:
                token:  The authentication token
            """
            with open(token_file, "w") as f:
                if self._debug_logging:
                    logging.debug(f"Saving authentication token to {token_file}: {token}")
                try:
                    f.write(token)
                except Exception as e:
                    logging.error(f"Failed to save authentication token to {token_file}: {e}")

        if not reauthenticate:
            if self._token and not self._token.isspace():
                token = self._token
                if self._debug_logging:
                    logging.debug(f"Using cached authentication token: {token}")
            else:
                token = load_token()

        if reauthenticate or not token or token == "":
            logging.info("Generating new Enphase authentication token")
            payload = {"user[email]": self._username, "user[password]": self._password}
            if self._debug_logging:
                logging.debug(f"Step 1: Authentication request payload: {payload}")
            with requests.post("https://enlighten.enphaseenergy.com/login/login.json?", data=payload) as response:
                assert response.status_code == 200, f"Failed connect to https://enlighten.enphaseenergy.com/login/login.json? to authenticate: Response={response} Payload={payload}"
                if self._debug_logging:
                    logging.debug(f"Step 1: Authentication response: {response.text}")
                response_data = json.loads(response.text)
                payload = {"session_id": response_data["session_id"], "serial_num": self._serial_number, "username": self._username}
                if self._debug_logging:
                    logging.debug(f"Step 2: Token request payload: {payload}")
                with requests.post("https://entrez.enphaseenergy.com/tokens", json=payload) as response:
                    assert response.status_code == 200, f"Failed connect to https://entrez.enphaseenergy.com/tokens to generate token: Response={response} Payload={payload}"
                    token = response.text
                    save_token(token)

        if self._debug_logging:
            logging.debug(f"Caching authentication token: {token}")
        self._token = token
        return token


class EnphaseLifetimePVEnergy(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Lifetime Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_lifetime_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_lifetime_pv_energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power",
            gain=1000,
            precision=2,
        )

    def set_source_values(self, sensor: EnphasePVPower, values: list) -> bool:
        if not issubclass(type(sensor), EnphasePVPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_state(round(values[-1][2]["actEnergyDlvd"] / self.gain, self._precision))
        return True


class EnphaseDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, serial_number: str, source: EnphaseLifetimePVEnergy):
        super().__init__(
            name="Daily Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_daily_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_daily_pv_energy",
            source=source,
            icon="mdi:solar-power-variant",
        )


class EnphaseCurrent(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Current",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_current",
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-dc",
            gain=1,
            precision=2,
        )
        self["enabled_by_default"] = False

    def set_source_values(self, sensor: EnphasePVPower, values: list) -> bool:
        if not issubclass(type(sensor), EnphasePVPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_state(round(values[-1][2]["current"] / self.gain, self._precision))
        return True


class EnphaseFrequency(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Frequency",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_frequency",
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=1,
            precision=2,
        )
        self["enabled_by_default"] = False

    def set_source_values(self, sensor: EnphasePVPower, values: list) -> bool:
        if not issubclass(type(sensor), EnphasePVPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_state(round(values[-1][2]["freq"] / self.gain, self._precision))
        return True


class EnphasePowerFactor(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Power Factor",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_power_factor",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_power_factor",
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            state_class=None,
            icon="mdi:angle-acute",
            gain=1,
            precision=2,
        )
        self["enabled_by_default"] = False

    def set_source_values(self, sensor: EnphasePVPower, values: list) -> bool:
        if not issubclass(type(sensor), EnphasePVPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_state(round(values[-1][2]["pwrFactor"] / self.gain, self._precision))
        return True


class EnphaseReactivePower(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Reactive Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_reactive_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_reactive_power",
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:transmission-tower",
            gain=1000,
            precision=2,
        )
        self["enabled_by_default"] = False

    def set_source_values(self, sensor: EnphasePVPower, values: list) -> bool:
        if not issubclass(type(sensor), EnphasePVPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_state(round(values[-1][2]["reactivePower"] / self.gain, self._precision))
        return True


class EnphaseVoltage(DerivedSensor):
    def __init__(self, plant_index: int, serial_number: str):
        super().__init__(
            name="Voltage",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_{serial_number}_voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_enphase_{serial_number}_voltage",
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=1,
            precision=1,
        )
        self["enabled_by_default"] = False

    def set_source_values(self, sensor: EnphasePVPower, values: list) -> bool:
        if not issubclass(type(sensor), EnphasePVPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_state(round(values[-1][2]["voltage"] / self.gain, self._precision))
        return True


class SmartPort(Device):
    def __init__(self, plant_index: int, config: ModuleConfig):
        if config.testing:
            logging.debug(f"SmartPort {plant_index} testing mode enabled")
            fw = "D7.0.0"
            sn = "123456789012"
            pn = "Envoy-S"
        else:
            url = f"http://{config.host}/info"
            with requests.Session() as session:
                with session.get(url, timeout=20, verify=False) as response:
                    assert response.status_code == 200, f"Failed to connect to {url} - Response code was {response.status_code}"
                    root = xml.fromstring(response.content)
                    sn = root.find("./device/sn").text
                    pn = root.find("./device/pn").text
                    fw = root.find("./device/software").text
        assert fw.startswith("D7") or fw.startswith("D8"), f"Unsupported Enphase Envoy firmware {fw}"
        unique_id = f"{Config.home_assistant.unique_id_prefix}_{plant_index}_enphase_envoy_{sn}"
        name = "Sigenergy Plant Smart-Port" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1} Smart-Port"
        super().__init__(name, plant_index, unique_id, "Enphase", "Envoy", model_id=pn, serial_number=sn, hw_version=fw)

        pv_power = EnphasePVPower(plant_index, sn, config.host, config.username, config.password)
        lifetime_pv_energy = EnphaseLifetimePVEnergy(plant_index, sn)
        self._add_read_sensor(pv_power, "consumption")
        self._add_derived_sensor(lifetime_pv_energy, pv_power)
        self._add_derived_sensor(EnphaseDailyPVEnergy(plant_index, sn, lifetime_pv_energy), lifetime_pv_energy)
        self._add_derived_sensor(EnphaseCurrent(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphaseFrequency(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphasePowerFactor(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphaseReactivePower(plant_index, sn), pv_power)
        self._add_derived_sensor(EnphaseVoltage(plant_index, sn), pv_power)


if __name__ == "__main__":
    logging.getLogger("root").setLevel(logging.DEBUG)
    Config.sensor_debug_logging = True

    async def test():
        smartport = SmartPort(0, Config.devices[0].smartport)
        print(smartport)
        pv_power_unique_id = f"{Config.home_assistant.unique_id_prefix}_0_enphase_{smartport['serial_number']}_active_power"
        sensor = smartport.get_sensor(pv_power_unique_id)
        sensor._debug_logging = True
        print(f"{sensor.name} =  {await sensor.get_state()}")
        for derived in sensor._derived_sensors.values():
            print(f"{derived.name} =  {await derived.get_state()}")

    asyncio.run(test(), debug=True)
