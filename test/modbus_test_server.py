import asyncio
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from paho.mqtt.client import Client as MqttClient
from paho.mqtt.client import CallbackAPIVersion
from pymodbus import __version__ as pymodbus_version
from pymodbus import FramerType, ModbusDeviceIdentification
from pymodbus.client.base import ModbusClientMixin
from pymodbus.datastore import ModbusServerContext, ModbusSparseDataBlock
from pymodbus.server import StartAsyncTcpServer
from random import randint
from ruamel.yaml import YAML
from test import get_sensor_instances, cancel_sensor_futures

_logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)


class CustomMqttHandler:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._topics = {}
        self._loop = loop
        self._connected = False
        self._reconnect_lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value) -> None:
        self._connected = value

    def on_reconnect(self, client: MqttClient) -> None:
        if not self._connected:
            with self._reconnect_lock:
                if not self._connected:
                    self._connected = True
                    if len(self._topics) > 0:
                        _logger.info("Reconnected to mqtt")
                        for topic in self._topics.keys():
                            result = client.unsubscribe(topic)
                            _logger.debug(f"on_reconnect: unsubscribe('{topic}') -> {result}")
                            result = client.subscribe(topic)
                            _logger.debug(f"on_reconnect: subscribe('{topic}') -> {result}")

    def on_message(self, topic: str, payload: str) -> None:
        value = str(payload).strip()
        if value and topic in self._topics:
            for method in self._topics[topic]:
                method(topic, value)

    def register(self, client: MqttClient, topic: str, handler) -> tuple[int, int]:
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(handler)
        return client.subscribe(topic)


class CustomDataBlock(ModbusSparseDataBlock):
    def __init__(self, device_address: int, mqtt_client: MqttClient):
        super().__init__(values=None, mutable=True)
        self._device_address = device_address
        self._topics = {}
        if mqtt_client:
            self._mqtt_client = mqtt_client
        self._total_sleep_time: int = 0
        self._read_count: int = 0

    @classmethod
    def create(cls, device_address: int, mqtt_client: MqttClient) -> "CustomDataBlock":
        return cls(device_address, mqtt_client)

    def add_sensor(self, sensor) -> None:
        if sensor._data_type == ModbusClientMixin.DATATYPE.STRING:
            match sensor._address:
                case 30500:
                    value = "SigenStor EC 12.0 TP"
                case 30515:
                    value = "CMU123A45BP678"
                case 30525:
                    value = "V100R001C00SPC108B088F"
                case _:
                    value = "string value"
            registers = ModbusClientMixin.convert_to_registers(value, sensor._data_type)
            if len(registers) < sensor._count:
                registers.extend([0] * (sensor._count - len(registers)))  # Pad with zeros
            elif len(registers) > sensor._count:
                registers = registers[: sensor._count]  # Truncate to the required length
        else:
            match sensor._address:
                case 30027 | 30028 | 30029 | 30030 | 30072 | 30605 | 30606 | 30607 | 30608 | 30609 | 32012 | 32013 | 32014:  # Alarms
                    value = 0
                case 31004:  # OutputType
                    value = 2
                case 31025:  # PVStringCount
                    value = 16
                case 31026:  # MPTTCount
                    value = 4
                case 40029:  # RemoteEMS
                    value = 1
                case _:
                    value = randint(0, 255)
            registers = ModbusClientMixin.convert_to_registers(value, sensor._data_type)
        self.setValues(sensor._address, registers)
        if self._mqtt_client and sensor._address and sensor._address not in (31004, 31025, 31026, 30027, 30028, 30029, 30030, 30072, 30605, 30606, 30607, 30608, 30609, 32012, 32013, 32014, 40029):
            if "state_topic" in sensor:
                self._topics[sensor.state_topic] = sensor
                self._mqtt_client.user_data_get().register(self._mqtt_client, sensor.state_topic, self._handle_mqtt_message)
            else:
                _logger.warning(f"Sensor {sensor['name']} does not have a state_topic and cannot be updated via MQTT.")

    def _handle_mqtt_message(self, topic: str, value: str) -> None:
        sensor = self._topics.get(topic)
        if sensor._data_type == ModbusClientMixin.DATATYPE.STRING:
            registers = ModbusClientMixin.convert_to_registers(value, sensor._data_type)
            if len(registers) < sensor._count:
                registers.extend([0] * (sensor._count - len(registers)))  # Pad with zeros
            elif len(registers) > sensor._count:
                registers = registers[: sensor._count]  # Truncate to the required length
        else:
            registers = ModbusClientMixin.convert_to_registers(sensor.state2raw(value), sensor._data_type)
        super().setValues(sensor._address, registers)

    async def async_getValues(self, fc_as_hex: int, address: int, count=1):
        delay_avg: int = 15
        delay_min: int = 5
        delay_max: int = 50
        self._read_count += count
        if (self._total_sleep_time + delay_min) / self._read_count > delay_avg:
            sleep_time = delay_min
        else:
            sleep_time = randint(delay_min, delay_max)  # Simulate variable response times
        self._total_sleep_time += sleep_time
        await asyncio.sleep(sleep_time / 1000)
        return super().getValues(address, count)

    async def async_setValues(self, fc_as_hex: int, address: int, values: list[int] | list[bool]):
        return super().setValues(address, values)


async def run_async_server(mqtt_client: MqttClient, use_simplified_topics: bool) -> None:
    context: dict[int, CustomDataBlock] = {}
    sensors = await get_sensor_instances(hass=not use_simplified_topics)
    for sensor in sensors.values():
        if hasattr(sensor, "_device_address"):
            if sensor._device_address not in context:
                context[sensor._device_address] = CustomDataBlock.create(sensor._device_address, mqtt_client)
            context[sensor._device_address].add_sensor(sensor)
    cancel_sensor_futures()
    _logger.info("Starting ASYNC Modbus TCP Testing Server...")
    await StartAsyncTcpServer(
        context=ModbusServerContext(devices=context, single=False if len(context) > 1 else True),
        identity=ModbusDeviceIdentification(
            info_name={
                "VendorName": "seud0nym",
                "ProductCode": "sigenergy2mqtt",
                "VendorUrl": "https://github.com/seud0nym/sigenergy2mqtt/",
                "ProductName": "sigenergy2mqtt Testing Modbus Server",
                "ModelName": "sigenergy2mqtt Testing Modbus Server",
                "MajorMinorRevision": pymodbus_version,
            }
        ),
        address=("0.0.0.0", 502),
        framer=FramerType.SOCKET,
    )


def on_connect(client: MqttClient, userdata: CustomMqttHandler, flags, reason_code, properties) -> None:
    if reason_code == 0:
        userdata.on_reconnect(client)
    else:
        _logger.critical(f"Connection to mqtt REFUSED - {reason_code}")
        os._exit(2)


def on_disconnect(client: MqttClient, userdata: CustomMqttHandler, flags, reason_code, properties) -> None:
    userdata.connected = False
    if reason_code != 0:
        _logger.error(f"Failed to disconnect from mqtt (Reason Code = {reason_code})")


def on_message(client: MqttClient, userdata: CustomMqttHandler, message) -> None:
    userdata.on_message(message.topic, str(message.payload, "utf-8"))
    userdata.on_reconnect(client)


async def async_helper() -> None:
    _yaml = YAML(typ="safe", pure=True)
    with open(".modbus_test_server.yaml", "r") as f:
        config = _yaml.load(f)
        mqtt_client = MqttClient(CallbackAPIVersion.VERSION2, client_id="modbus_test_server", userdata=CustomMqttHandler(asyncio.get_running_loop()))
        mqtt_client.username_pw_set(config.get("mqtt", {}).get("username"), config.get("mqtt", {}).get("password"))
        mqtt_client.connect(config.get("mqtt", {}).get("broker", "localhost"), config.get("mqtt", {}).get("port", 1883), 60)
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.loop_start()
    await run_async_server(mqtt_client, bool(config.get("home-assistant", {}).get("use-simplified-topics")))
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(async_helper(), debug=True)
