import asyncio
import logging
import os
import sys
import threading


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import datetime
from paho.mqtt.client import Client as MqttClient
from paho.mqtt.client import CallbackAPIVersion
from pymodbus import __version__ as pymodbus_version
from pymodbus import FramerType, ModbusDeviceIdentification
from pymodbus.client.base import ModbusClientMixin
from pymodbus.constants import ExcCodes
from pymodbus.datastore import ModbusServerContext, ModbusSparseDataBlock
from pymodbus.server import StartAsyncTcpServer
from random import randint
from ruamel.yaml import YAML
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.const import MAX_MODBUS_REGISTERS_PER_REQUEST, DeviceClass
from test import get_sensor_instances, cancel_sensor_futures

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

_logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)


class CustomMqttHandler:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.connected = False
        self._topics = {}
        self._loop = loop
        self._reconnect_lock = threading.Lock()

    def on_reconnect(self, client: MqttClient) -> None:
        if not self.connected:
            with self._reconnect_lock:
                if not self.connected:
                    self.connected = True
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
        self.device_address = device_address
        self._topics: dict = {}
        if mqtt_client:
            self._mqtt_client = mqtt_client
        self._total_sleep_time: int = 0
        self._read_count: int = 0
        self._written_addresses: list[int] = []

    @classmethod
    def create(cls, device_address: int, mqtt_client: MqttClient) -> "CustomDataBlock":
        return cls(device_address, mqtt_client)

    def add_sensor(self, sensor) -> None:
        if not sensor.publishable:
            return
        source = None
        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            source = "string"
            value = "string value" if not sensor.latest_raw_state else sensor.latest_raw_state
        else:
            if sensor.address == 31004:  # OutputType
                source = "output_type"
                value = 2
            elif sensor.address == 31025:  # PVStringCount
                source = "pv_string_count"
                value = 16
            elif sensor.address == 31026:  # MPTTCount
                source = "mptt_count"
                value = 4
            elif sensor.address == 32007:  # ACChargerRatedCurrent
                source = "rated_current"
                value = 63
            elif sensor.address == 32010:  # ACChargerInputBreaker
                source = "input_breaker"
                value = 64
            elif hasattr(sensor, "decode_alarm_bit"):  # AlarmSensor
                source = "alarm_sensor"
                value = 0
            elif sensor.latest_raw_state is not None:
                source = "latest_raw_state"
                value = sensor.latest_raw_state / sensor.gain
            elif sensor.device_class == DeviceClass.TIMESTAMP:
                source = "timestamp"
                value = datetime.now().isoformat()
            elif hasattr(sensor, "state_off") and hasattr(sensor, "state_on"):  # SwitchSensor
                source = "switch_sensor"
                value = 0
            elif hasattr(sensor, "min") and hasattr(sensor, "max"):
                source = "min_max"
                value = randint(sensor["min"][0] if not isinstance(sensor["min"], (tuple, list)) else sensor["min"], sensor["min"][1] if not isinstance(sensor["min"], (tuple, list)) else sensor["max"])
            elif hasattr(sensor, "options"):
                value = 0
            elif sensor._sanity.min_value is not None and sensor._sanity.max_value is not None:
                source = "sanity_check"
                if sensor._sanity.delta:
                    value = sensor._sanity.min_value + randint(0, int(sensor._sanity.max_value - sensor._sanity.min_value) // sensor._sanity.delta) * sensor._sanity.delta
                else:
                    value = randint(int(sensor._sanity.min_value), int(sensor._sanity.max_value))
                value /= sensor.gain
            else:
                source = "data_type_default"
                match sensor.data_type:
                    case ModbusClientMixin.DATATYPE.INT16:
                        value = randint(-32768 if sensor._sanity.min_value is None else int(sensor._sanity.min_value), 32767 if sensor._sanity.max_value is None else int(sensor._sanity.max_value))
                    case ModbusClientMixin.DATATYPE.UINT16:
                        value = randint(0, 65535 if sensor._sanity.max_value is None else int(sensor._sanity.max_value))
                    case ModbusClientMixin.DATATYPE.INT32:
                        value = randint(-2147483648 if sensor._sanity.min_value is None else int(sensor._sanity.min_value), 2147483647 if sensor._sanity.max_value is None else int(sensor._sanity.max_value))
                    case ModbusClientMixin.DATATYPE.UINT32:
                        value = randint(0, 4294967295 if sensor._sanity.max_value is None else int(sensor._sanity.max_value))
                    case ModbusClientMixin.DATATYPE.INT64:
                        value = randint(
                            -9223372036854775808 if sensor._sanity.min_value is None else int(sensor._sanity.min_value),
                            9223372036854775807 if sensor._sanity.max_value is None else int(sensor._sanity.max_value),
                        )
                    case ModbusClientMixin.DATATYPE.UINT64:
                        value = randint(0, 18446744073709551615 if sensor._sanity.max_value is None else int(sensor._sanity.max_value))
                    case _:
                        value = randint(0, 255)
                value /= sensor.gain
        _logger.debug(f"Setting initial value for sensor {sensor['name']} (address={sensor.address}, device_address={self.device_address}, source={source}): {value}")
        self._set_value(sensor, value)
        if self._mqtt_client and sensor.address and not hasattr(sensor, "decode_alarm_bit"):
            if "state_topic" in sensor:
                self._topics[sensor.state_topic] = sensor
                self._mqtt_client.user_data_get().register(self._mqtt_client, sensor.state_topic, self._handle_mqtt_message)
            else:
                _logger.warning(f"Sensor {sensor['name']} does not have a state_topic and cannot be updated via MQTT.")

    def _handle_mqtt_message(self, topic: str, value: str) -> None:
        sensor = self._topics.get(topic)
        self._set_value(sensor, value)

    def _set_value(self, sensor, value: float | int | str) -> None:
        address = sensor.address
        if address in self._written_addresses:
            return  # Ignore messages for addresses that were just written to
        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            registers = ModbusClientMixin.convert_to_registers(value, sensor.data_type)
            if len(registers) < sensor.count:
                registers.extend([0] * (sensor.count - len(registers)))  # Pad with zeros
            elif len(registers) > sensor.count:
                registers = registers[: sensor.count]  # Truncate to the required length
        else:
            raw = sensor.state2raw(value)
            registers = ModbusClientMixin.convert_to_registers(raw, sensor.data_type)
        super().setValues(address, registers)
        if address == 31011:
            super().setValues(31013, registers)
            super().setValues(31015, registers)
        elif address == 31017:
            super().setValues(31019, registers)
            super().setValues(31021, registers)

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
        if address in (30279, 30281, 30286, 30288, 30290, 30292, 30294, 30296, 30622, 30623, 40049):
            # Return ILLEGAL ADDRESS for request for specific address, but not if part of larger chunk
            return ExcCodes.ILLEGAL_ADDRESS
        return super().getValues(address, count)

    async def async_setValues(self, fc_as_hex: int, address: int, values: list[int] | list[bool]):
        self._written_addresses.append(address)
        return super().setValues(address, values)


async def run_async_server(mqtt_client: MqttClient, modbus_client: ModbusClient, use_simplified_topics: bool) -> None:
    context: dict[int, CustomDataBlock] = {}
    groups: dict[int, list] = {}
    group_index: int = None
    address: int = None
    count: int = None
    device_address: int = None
    input_type = None

    _logger.info("Getting sensor instances...")
    sensors: dict = await get_sensor_instances(hass=not use_simplified_topics, pv_inverter_device_address=3)
    for sensor in sorted([s for s in sensors.values() if hasattr(s, "address") and s["platform"] != "button" and not hasattr(s, "alarms")], key=lambda x: (x.device_address, x.address)):
        if (
            device_address != sensor.device_address
            or (address is None or count is None or sensor.address != address + count)
            or input_type != sensor.input_type
            or (group_index is not None and (sum(s.count for s in groups[group_index]) + sensor.count) > MAX_MODBUS_REGISTERS_PER_REQUEST)
        ):
            group_index = group_index + 1 if group_index is not None else 0
            groups[group_index] = []
        groups[group_index].append(sensor)
        address = sensor.address
        count = sensor.count
        device_address = sensor.device_address
        input_type = sensor.input_type

    if modbus_client:
        _logger.info("Pre-populating sensor values...")
        skip_devices: list[int] = []
        async with modbus_client:
            await modbus_client.connect()
            for group_sensors in groups.values():
                if len(group_sensors) == 1 and (group_sensors[0].device_address in skip_devices or group_sensors[0].__class__.__name__.startswith("Reserved")):
                    continue
                first_address: int = min([s.address for s in group_sensors if hasattr(s, "address") and not s.__class__.__name__.startswith("Reserved")])
                last_address: int = max([s.address + s.count - 1 for s in group_sensors if hasattr(s, "address") and not s.__class__.__name__.startswith("Reserved")])
                count: int = sum([s.count for s in group_sensors if hasattr(s, "count") and first_address <= getattr(s, "address") <= last_address])
                assert first_address and last_address and (last_address - first_address + 1) == count
                device_address = group_sensors[0].device_address
                try:
                    if await modbus_client.read_ahead_registers(first_address, count, device_id=device_address, input_type=group_sensors[0].input_type) == 0:
                        for sensor in group_sensors:
                            if sensor.publishable:
                                await sensor.get_state(modbus=modbus_client)
                except Exception:
                    if device_address not in skip_devices:
                        skip_devices.append(device_address)
                    if not modbus_client.connected:
                        await modbus_client.connect()

    _logger.info("Creating data blocks...")
    for sensor in sensors.values():
        if hasattr(sensor, "device_address"):
            if sensor.device_address not in context:
                context[sensor.device_address] = CustomDataBlock.create(sensor.device_address, mqtt_client)
            context[sensor.device_address].add_sensor(sensor)
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
    with open("test/.modbus_test_server.yaml", "r") as f:
        config = _yaml.load(f)
        mqtt_client = MqttClient(CallbackAPIVersion.VERSION2, client_id="modbus_test_server", userdata=CustomMqttHandler(asyncio.get_running_loop()))
        mqtt_client.username_pw_set(config.get("mqtt", {}).get("username"), config.get("mqtt", {}).get("password"))
        mqtt_client.connect(config.get("mqtt", {}).get("broker", "localhost"), config.get("mqtt", {}).get("port", 1883), 60)
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.loop_start()
        modbus_client = ModbusClient(config.get("modbus")[0].get("host"), port=config.get("modbus")[0].get("port", 502), timeout=1, retries=0)

    await run_async_server(mqtt_client, modbus_client, bool(config.get("home-assistant", {}).get("use-simplified-topics")))

    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(async_helper(), debug=True)
