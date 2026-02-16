import asyncio
import time
from unittest.mock import Mock

import pytest

from sigenergy2mqtt.sensors import base
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.config.config import Config


@pytest.fixture(autouse=True)
def reset_env(tmp_path):
    Config.persistent_state_path = tmp_path
    base.Sensor._used_object_ids.clear()
    base.Sensor._used_unique_ids.clear()
    yield


@pytest.mark.asyncio
async def test_perform_holding_read(monkeypatch):
    async def fake_read(addr, count, device_id, trace):
        rr = Mock()
        rr.isError.return_value = False
        rr.registers = [7]
        return rr

    modbus = Mock()
    modbus.read_holding_registers = fake_read
    modbus.convert_from_registers = Mock(return_value=7)

    s = base.ReadOnlySensor(name="rh", object_id="sigen_rh", input_type=base.InputType.HOLDING, plant_index=0, device_address=1, address=30120, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)
    ok = await s._perform_modbus_read(modbus)
    assert ok is True
    assert s.latest_raw_state == 7


@pytest.mark.asyncio
async def test_write_registers_lock_and_convert(monkeypatch):
    # provide ModbusLockFactory.get(...).lock
    class DummyLock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Container:
        @staticmethod
        def get(_):
            class F:
                def lock(self, *_):
                    return DummyLock()

            return F()

    monkeypatch.setattr(base, "ModbusLockFactory", Container)

    modbus = Mock()
    async def fake_write_registers(addr, registers, device_id, no_response_expected=False):
        rr = Mock()
        rr.isError.return_value = False
        return rr

    modbus.write_registers = fake_write_registers
    async def fake_write_register(addr, value, device_id=None, no_response_expected=False):
        rr = Mock()
        rr.isError.return_value = False
        return rr

    modbus.write_register = fake_write_register
    w = base.WriteOnlySensor(name="w4", object_id="sigen_w4", plant_index=0, device_address=1, address=30130, protocol_version=base.Protocol.N_A)
    # ensure numeric short-circuit
    w.data_type = ModbusDataType.UINT16
    ok = await w._write_registers(modbus, 10, Mock())
    assert ok is True


def test_convert_value_to_registers_uint16_short():
    rw = base.ReadWriteSensor(None, name="rw2", object_id="sigen_rw2", input_type=base.InputType.HOLDING, plant_index=0, device_address=1, address=30140, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A)
    mock_modbus = Mock()
    out = rw._convert_value_to_registers(mock_modbus, 42)
    assert out == [42]


def test_running_state_sensor_options_mapping():
    rs = base.RunningStateSensor(name="rsn", object_id="sigen_rsn", plant_index=0, device_address=1, address=30150, protocol_version=base.Protocol.N_A)
    rs.set_latest_state(1)
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(rs.get_state(raw=False, republish=True))
    loop.close()
    assert isinstance(val, str) and ("Normal" in val or "Unknown State" in val)
