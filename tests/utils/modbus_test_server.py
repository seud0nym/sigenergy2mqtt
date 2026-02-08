import asyncio
import bisect
import logging
import os
import sys
import threading
import time
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from datetime import datetime
from random import randint

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode
from pymodbus import FramerType, ModbusDeviceIdentification
from pymodbus import __version__ as pymodbus_version
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.constants import ExcCodes
from pymodbus.datastore import ModbusServerContext, ModbusSparseDataBlock
from pymodbus.server import StartAsyncTcpServer
from ruamel.yaml import YAML

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.const import MAX_MODBUS_REGISTERS_PER_REQUEST, DeviceClass
from tests.utils import cancel_sensor_futures, get_sensor_instances

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

_logger = logging.getLogger(__file__)


class CustomMqttHandler:
    def __init__(self, loop: asyncio.AbstractEventLoop, log_level: int = logging.INFO):
        self.connected = False
        self._topics = {}
        self._loop = loop
        self._reconnect_lock = threading.Lock()
        self._logger = logging.getLogger("CustomMqttHandler")
        self._logger.setLevel(log_level)

    def on_reconnect(self, client: mqtt.Client) -> None:
        if not self.connected:
            with self._reconnect_lock:
                if not self.connected:
                    self.connected = True
                    if len(self._topics) > 0:
                        self._logger.info("Reconnected to mqtt")
                        for topic in self._topics.keys():
                            result = client.unsubscribe(topic)
                            self._logger.debug(f"on_reconnect: unsubscribe('{topic}') -> {result}")
                            result = client.subscribe(topic)
                            self._logger.debug(f"on_reconnect: subscribe('{topic}') -> {result}")

    def on_message(self, topic: str, payload: str) -> None:
        value = str(payload).strip()
        if value and topic in self._topics:
            for method in self._topics[topic]:
                self._logger.debug(f"on_message: {method.__func__.__qualname__}('{topic}', {value})")
                method(topic, value, debug=self._logger.isEnabledFor(logging.DEBUG))

    def register(self, client: mqtt.Client, topic: str, handler) -> tuple[MQTTErrorCode, int | None]:
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(handler)
        return client.subscribe(topic)


class CustomDataBlock(ModbusSparseDataBlock):
    def __init__(self, device_address: int, mqtt_client: mqtt.Client):
        super().__init__(values=None, mutable=True)
        self.device_address = device_address
        self.addresses: dict[int, Any] = {}
        self._reserved: list[int] = []
        self._topics: dict[str, Any] = {}
        self._written_addresses: list[int] = []
        if mqtt_client:
            self._mqtt_client = mqtt_client
        self._total_sleep_time: int = 0
        self._read_count: int = 0

    def _set_value(self, sensor, value: float | int | str, source: str = "", debug: bool = False) -> None:
        if debug or sensor.debug_logging:
            _logger.debug(f"_set_value({sensor['name']}, {value}) [address={sensor.address} device_address={self.device_address} {source=}]")
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
        if address == 31011:  # Use the Phase A Voltage for all three phases
            super().setValues(31013, registers)
            super().setValues(31015, registers)
        elif address == 31017:  # Use the Phase A Current for all three phases
            super().setValues(31019, registers)
            super().setValues(31021, registers)

    def _handle_mqtt_message(self, topic: str, value: str, debug: bool = False) -> None:
        sensor = self._topics.get(topic)
        self._set_value(sensor, value, f"mqtt::{topic}", debug=debug)

    def add_sensor(self, sensor: Any) -> None:
        self.addresses[sensor.address] = sensor
        if sensor.__class__.__name__.startswith("Reserved"):
            self._reserved.append(sensor.address)
        if not sensor.publishable:
            return
        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            source = "string"
            value = "string value" if not sensor.latest_raw_state else sensor.latest_raw_state
        else:
            if sensor.address == 31004:  # OutputType
                source = "output_type"
                value = 2
            elif sensor.address == 31023:  # PowerFactor
                source = "power_factor"
                value = randint(64572, 65534) / sensor.gain  # Force sanity check failure to test handling
            elif sensor.address == 32007:  # ACChargerRatedCurrent
                source = "rated_current"
                value = 63
            elif sensor.address == 32010:  # ACChargerInputBreaker
                source = "input_breaker"
                value = 64
            elif hasattr(sensor, "decode_alarm_bit"):  # AlarmSensor
                source = "alarm_sensor"
                value = 0
            else:
                if sensor.latest_raw_state is not None and isinstance(sensor.latest_raw_state, (int, float)):
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
                    value = randint(sensor["min"][0] if isinstance(sensor["min"], (tuple, list)) else sensor["min"], sensor["max"][1] if isinstance(sensor["max"], (tuple, list)) else sensor["max"])
                elif hasattr(sensor, "options"):
                    source = "options"
                    value = 0
                elif sensor.sanity_check.min_raw is not None and sensor.sanity_check.max_raw is not None:
                    source = "sanity_check"
                    if sensor.sanity_check.delta:
                        value = sensor.sanity_check.min_raw + randint(0, int(sensor.sanity_check.max_raw - sensor.sanity_check.min_raw) // sensor.sanity_check.delta) * sensor.sanity_check.delta
                    else:
                        value = randint(int(sensor.sanity_check.min_raw), int(sensor.sanity_check.max_raw))
                    value /= sensor.gain
                else:
                    source = "data_type_default"
                    match sensor.data_type:
                        case ModbusClientMixin.DATATYPE.INT16:
                            value = randint(
                                -32768 if sensor.sanity_check.min_raw is None else int(sensor.sanity_check.min_raw), 32767 if sensor.sanity_check.max_raw is None else int(sensor.sanity_check.max_raw)
                            )
                        case ModbusClientMixin.DATATYPE.UINT16:
                            value = randint(0, 65535 if sensor.sanity_check.max_raw is None else int(sensor.sanity_check.max_raw))
                        case ModbusClientMixin.DATATYPE.INT32:
                            value = randint(
                                -2147483648 if sensor.sanity_check.min_raw is None else int(sensor.sanity_check.min_raw), 2147483647 if sensor.sanity_check.max_raw is None else int(sensor.sanity_check.max_raw)
                            )
                        case ModbusClientMixin.DATATYPE.UINT32:
                            value = randint(0, 4294967295 if sensor.sanity_check.max_raw is None else int(sensor.sanity_check.max_raw))
                        case ModbusClientMixin.DATATYPE.INT64:
                            value = randint(
                                -9223372036854775808 if sensor.sanity_check.min_raw is None else int(sensor.sanity_check.min_raw),
                                9223372036854775807 if sensor.sanity_check.max_raw is None else int(sensor.sanity_check.max_raw),
                            )
                        case ModbusClientMixin.DATATYPE.UINT64:
                            value = randint(0, 18446744073709551615 if sensor.sanity_check.max_raw is None else int(sensor.sanity_check.max_raw))
                        case _:
                            value = randint(0, 255)
                    value /= sensor.gain
                if self._mqtt_client and sensor.address and source not in ("output_type", "pv_string_count", "mptt_count", "alarm_sensor", "power_factor"):
                    if "state_topic" in sensor:
                        self._topics[sensor.state_topic] = sensor
                        self._mqtt_client.user_data_get().register(self._mqtt_client, sensor.state_topic, self._handle_mqtt_message)
                    else:
                        _logger.warning(f"Sensor {sensor['name']} does not have a state_topic and cannot be updated via MQTT.")
        self._set_value(sensor, value, source)

    async def async_getValues(self, fc_as_hex: int, address: int, count=1) -> ExcCodes | list[int] | list[bool]:  # pyright: ignore[reportIncompatibleMethodOverride] # pyrefly: ignore
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
        result = self.getValues(address, count)
        if address in self.addresses and self.addresses[address].debug_logging:
            _logger.debug(f"async_getValues({fc_as_hex}, {address}, {count}) -> {result}")
        return result

    async def async_setValues(self, fc_as_hex: int, address: int, values: list[int] | list[bool]) -> ExcCodes | None:  # pyright: ignore[reportIncompatibleMethodOverride] # pyrefly: ignore
        if address in self.addresses:
            sensor = self.addresses[address]
            if hasattr(sensor, "_availability_control_sensor") and sensor._availability_control_sensor.__class__.__name__ == "RemoteEMS":
                if sensor._availability_control_sensor.latest_raw_state == 0:
                    return ExcCodes.ILLEGAL_ADDRESS
        else:
            sensor = None
        self._written_addresses.append(address)
        if sensor and sensor.debug_logging:
            _logger.debug(f"async_setValues({fc_as_hex}, {address}, {values})")
        return super().setValues(address, values)

    def getValues(self, address, count=1) -> list[int] | list[bool] | ExcCodes:
        sensor = None if address not in self.addresses else self.addresses[address]
        last_address = address + count - 1
        if address in self._reserved or last_address - count + 1 in self._reserved:
            # Return ILLEGAL ADDRESS for request for specific address, but not if part of larger chunk
            result = ExcCodes.ILLEGAL_ADDRESS
        elif sensor and sensor.count == count:
            result = super().getValues(address, count)
        else:
            pre_read: list[int | bool] = []
            keys = list(self.addresses.keys())
            start = bisect.bisect_left(keys, address)
            end = bisect.bisect_right(keys, last_address)
            for k in keys[start:end]:
                sensor = self.addresses[k]
                state = super().getValues(sensor.address, sensor.count)
                if isinstance(state, list):
                    pre_read.extend(state)
                else:
                    for _ in range(0, sensor.count):
                        pre_read.append(0)
            result = pre_read if len(pre_read) == count else ExcCodes.ILLEGAL_ADDRESS
        if sensor and sensor.debug_logging:
            _logger.debug(f"getValues({address}, {count}) -> {result}")
        return result


async def simulate_grid_outage(data_block: CustomDataBlock, wait_for_seconds: int, duration_seconds: int) -> None:
    while True:
        try:
            _logger.info(f"Waiting for {wait_for_seconds} seconds before simulating grid outage for device address {data_block.device_address}...")
            await asyncio.sleep(wait_for_seconds)
            _logger.info(f"Simulating grid outage for device address {data_block.device_address} for {duration_seconds} seconds...")
            await data_block.async_setValues(0x06, 30009, [1])
            await asyncio.sleep(duration_seconds)
            await data_block.async_setValues(0x06, 30009, [0])
            _logger.info(f"Grid outage simulation ended for device address {data_block.device_address}.")
        except asyncio.CancelledError:
            break


async def prepopulate(modbus_client, groups):
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
                            await sensor.get_state(modbus_client=modbus_client)
            except Exception:
                if device_address not in skip_devices:
                    skip_devices.append(device_address)
                if not modbus_client.connected:
                    await modbus_client.connect()


async def run_async_server(
    mqtt_client: Any,
    modbus_client: ModbusClient | None,
    use_simplified_topics: bool,
    host: str = "0.0.0.0",
    port: int = 502,
    protocol_version: Protocol = list(Protocol)[-1],
    log_level: int = logging.INFO,
    registers_to_debug: list[int] = [],
) -> None:
    context: dict[int, CustomDataBlock] = {}
    groups: dict[int, list] = {}
    group_index: int = -1
    address: int | None = None
    count: int | None = None
    device_address: int | None = None
    input_type = None

    _logger.info("Getting sensor instances...")
    sensors: dict = await get_sensor_instances(hass=not use_simplified_topics, protocol_version=protocol_version, pv_inverter_device_address=3, concrete_sensor_check=False)
    sorted_sensors: list = sorted(
        [s for s in sensors.values() if hasattr(s, "address") and s["platform"] != "button" and not hasattr(s, "alarms")],
        key=lambda x: (x.device_address, x.address),
    )
    for sensor in sorted_sensors:
        if (
            device_address != sensor.device_address
            or (address is None or count is None or sensor.address != address + count)
            or input_type != sensor.input_type
            or (group_index != -1 and (sum(s.count for s in groups[group_index]) + sensor.count) > MAX_MODBUS_REGISTERS_PER_REQUEST)
        ):
            group_index = group_index + 1
            groups[group_index] = []
        groups[group_index].append(sensor)
        if sensor.address in registers_to_debug or 0 in registers_to_debug:
            sensor.debug_logging = True
        address = sensor.address
        count = sensor.count
        device_address = sensor.device_address
        input_type = sensor.input_type

    if modbus_client:
        await prepopulate(modbus_client, groups)

    _logger.setLevel(log_level if not any(registers_to_debug) else logging.DEBUG)

    _logger.info("Creating data blocks...")
    for sensor in sorted_sensors:
        if hasattr(sensor, "device_address"):
            if sensor.device_address not in context:
                context[sensor.device_address] = CustomDataBlock(sensor.device_address, mqtt_client)
            context[sensor.device_address].add_sensor(sensor)
    cancel_sensor_futures()

    _logger.info("Starting ASYNC Modbus TCP Testing Server...")
    if log_level <= logging.INFO:
        logging.getLogger("pymodbus").setLevel(logging.INFO)
    try:
        await asyncio.gather(
            StartAsyncTcpServer(
                context=ModbusServerContext(devices=context, single=False),
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
                address=(host, port),
                framer=FramerType.SOCKET,
            ),
            simulate_grid_outage(context[247], wait_for_seconds=30, duration_seconds=30),
        )
    except asyncio.CancelledError as e:
        _logger.debug(f"Modbus TCP Testing Server cancelled: {e}")


async def wait_for_server_start(host: str, port: int, timeout: float = 10.0) -> bool:
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, ConnectionRefusedError):
            await asyncio.sleep(0.1)
    return False


def on_connect(client: mqtt.Client, userdata: CustomMqttHandler, flags, reason_code, properties) -> None:
    if reason_code == 0:
        userdata.on_reconnect(client)
    else:
        _logger.critical(f"Connection to mqtt REFUSED - {reason_code}")
        os._exit(2)


def on_disconnect(client: mqtt.Client, userdata: CustomMqttHandler, flags, reason_code, properties) -> None:
    userdata.connected = False
    if reason_code != 0:
        _logger.error(f"Failed to disconnect from mqtt (Reason Code = {reason_code})")


def on_message(client: mqtt.Client, userdata: CustomMqttHandler, message) -> None:
    userdata.on_message(message.topic, str(message.payload, "utf-8"))
    userdata.on_reconnect(client)


async def async_helper() -> None:
    _yaml = YAML(typ="safe", pure=True)
    modbus_log_level: int = logging.INFO
    with open("tests/utils/.modbus_test_server.yaml", "r") as f:
        config = _yaml.load(f)
        mqtt_log_level = logging.getLevelNamesMapping()[config.get("mqtt", {}).get("log-level", "INFO")]
        mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="modbus_test_server", userdata=CustomMqttHandler(asyncio.get_running_loop(), log_level=mqtt_log_level))
        mqtt_client.username_pw_set(config.get("mqtt", {}).get("username"), config.get("mqtt", {}).get("password"))
        mqtt_client.connect(config.get("mqtt", {}).get("broker", "localhost"), config.get("mqtt", {}).get("port", 1883), 60)
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.loop_start()
        modbus_client = ModbusClient(config.get("modbus")[0].get("host"), port=config.get("modbus")[0].get("port", 502), timeout=1, retries=0)
        modbus_log_level = logging.getLevelNamesMapping()[config.get("modbus")[0].get("log-level", "INFO")]
        protocol_version = config.get("modbus")[0].get("protocol-version", None)
        registers_to_debug = config.get("modbus")[0].get("registers_to_debug", [])
        if protocol_version:
            protocol_version = Protocol(protocol_version)

    await run_async_server(
        mqtt_client, modbus_client, bool(config.get("home-assistant", {}).get("use-simplified-topics")), protocol_version=protocol_version, log_level=modbus_log_level, registers_to_debug=registers_to_debug
    )

    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(async_helper(), debug=True)
