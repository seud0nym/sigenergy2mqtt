"""Values written to Modbus are rounded to the nearest register value, never truncated."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import InputType, ProtocolVersion
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType
from sigenergy2mqtt.sensors.base import NumericSensor, Sensor

# (display value, gain, expected raw register value). Each product is just below
# the integer in binary floating point (e.g. 2.01 * 1000 == 2009.9999999999998).
CASES = [
    (2.01, 1000, 2010),
    (0.29, 100, 29),
    (4.35, 100, 435),
    (4.35, 1000, 4350),
    (0.29, 1000, 290),
    (2.01, 100, 201),
    (-2.01, 1000, -2010),
    (1.0, 1000, 1000),
]


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


def _sensor(gain: float, **kwargs) -> NumericSensor:
    sensor = NumericSensor(None, "Test", "sigen_round", InputType.HOLDING, 0, 1, 30104, 2, ModbusDataType.INT32, 10, "kW", None, "mdi:power", gain, 2, ProtocolVersion.V2_4, **kwargs)
    sensor.configure_mqtt_topics("test_device")
    return sensor


@pytest.mark.parametrize(("value", "gain", "expected"), CASES)
def test_state2raw_rounds(value, gain, expected):
    sensor = _sensor(gain)
    assert sensor.state2raw(value) == expected
    assert sensor.state2raw(str(value)) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(("value", "gain", "expected"), CASES)
async def test_set_value_writes_rounded_registers(value, gain, expected):
    sensor = _sensor(gain)
    modbus = MagicMock(spec=ModbusClient)
    modbus.convert_to_registers = MagicMock(side_effect=lambda v, dt: ModbusClient.convert_to_registers(v, dt))
    response = MagicMock()
    response.isError.return_value = False
    modbus.write_registers = AsyncMock(return_value=response)
    lock = MagicMock()
    lock.lock.return_value.__aenter__ = AsyncMock()
    lock.lock.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("sigenergy2mqtt.sensors.base.mixins.ModbusLockFactory.get", return_value=lock), patch("sigenergy2mqtt.metrics.Metrics.modbus_write", new_callable=AsyncMock):
        assert await sensor.set_value(modbus, MagicMock(), str(value), cast(str, sensor["command_topic"]), MagicMock()) is True

    registers = modbus.write_registers.call_args.args[1]
    assert ModbusClient.convert_from_registers(registers, ModbusDataType.INT32) == expected


@pytest.mark.parametrize(("value", "expected"), [(2009.9999999999998, 2010), (28.999999999999996, 29), ("2009.9999999999998", 2010), (2010, 2010), ("7", 7)])
def test_convert_value_to_registers_rounds(value, expected):
    sensor = _sensor(1000)
    registers = sensor._convert_value_to_registers(cast(ModbusClient, ModbusClient), value)
    assert ModbusClient.convert_from_registers(registers, ModbusDataType.INT32) == expected


def test_min_max_sanity_bounds_are_rounded():
    """0.29 * 100 is 28.999999999999996: the raw bound must be 29, not 28."""
    sensor = _sensor(100, minimum=-0.29, maximum=0.29)
    assert sensor.sanity_check.min_raw == -29
    assert sensor.sanity_check.max_raw == 29
