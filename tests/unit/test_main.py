import logging
import signal
import sys
import types
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import ConsumptionMethod, Protocol
from sigenergy2mqtt.config import _swap_active_config, active_config
from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerRunningState
from sigenergy2mqtt.sensors.base import DerivedSensor, ModbusSensorMixin, ReadOnlySensor, Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, InputType, StateClass
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion
from sigenergy2mqtt.sensors.plant_read_only import SystemTimeZone

# Use locally aliased function for backward compatibility
configure_logging = main_mod.configure_logging
get_state = main_mod.get_state


@pytest.fixture
def clean_config(monkeypatch):
    """Fixture to ensure Config is clean and mocked appropriately for tests."""
    from sigenergy2mqtt.config import Config, active_config

    cfg = Config()
    cfg.modbus = []
    cfg.pvoutput.enabled = False
    cfg.home_assistant.enabled = False
    cfg.metrics_enabled = False
    cfg.clean = False
    cfg.log_level = logging.INFO
    cfg.persistent_state_path = "/tmp"
    cfg.mqtt.anonymous = True

    with _swap_active_config(cfg):
        # Mock validation and logging config to avoid side effects
        monkeypatch.setattr("sigenergy2mqtt.main.main.configure_logging", lambda: None)
        monkeypatch.setattr("sigenergy2mqtt.main.main.pymodbus_apply_logging_config", lambda *a: None)
        yield cfg


class ConcreteSensor(Sensor):
    """Concrete implementation of Sensor for testing."""

    async def _update_internal_state(self, **kwargs):
        if "value" in kwargs:
            self.set_state(kwargs["value"])
        return True


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_configure_logging_sets_root_level(self):
        """Test that configure_logging sets the root logger level."""
        with (
            patch.object(active_config, "log_level", logging.DEBUG),
            patch.object(active_config, "get_modbus_log_level", return_value=logging.INFO),
            patch.object(active_config.mqtt, "log_level", logging.WARNING),
            patch.object(active_config.pvoutput, "log_level", logging.ERROR),
        ):
            # Reset loggers to known state
            logging.getLogger("root").setLevel(logging.NOTSET)
            logging.getLogger("pymodbus").setLevel(logging.NOTSET)
            logging.getLogger("paho.mqtt").setLevel(logging.NOTSET)
            logging.getLogger("pvoutput").setLevel(logging.NOTSET)

            main_mod.configure_logging()

            assert logging.getLogger("root").level == logging.DEBUG
            assert logging.getLogger("pymodbus").level == logging.INFO
            assert logging.getLogger("paho.mqtt").level == logging.WARNING
            assert logging.getLogger("pvoutput").level == logging.ERROR


class TestGetState:
    """Tests for the get_state helper function and related sensor behaviors."""

    @pytest.mark.asyncio
    async def test_get_state_success(self):
        """Test successful state retrieval."""
        mock_sensor = MagicMock()
        mock_sensor.get_state = AsyncMock(return_value=42.5)
        mock_sensor.__class__.__name__ = "TestSensor"

        mock_modbus = MagicMock()
        mock_modbus.comm_params.host = "192.168.1.1"
        mock_modbus.comm_params.port = 502

        sensor, state = await main_mod.get_state(mock_sensor, mock_modbus, "test_device")

        assert sensor == mock_sensor
        assert state == 42.5

    @pytest.mark.asyncio
    async def test_get_state_exception_returns_default(self):
        """Test that exceptions return the default value."""
        mock_sensor = MagicMock()
        mock_sensor.get_state = AsyncMock(side_effect=Exception("Connection failed"))
        mock_sensor.__class__.__name__ = "TestSensor"

        mock_modbus = MagicMock()
        mock_modbus.comm_params.host = "192.168.1.1"
        mock_modbus.comm_params.port = 502

        sensor, state = await main_mod.get_state(mock_sensor, mock_modbus, "test_device", default_value=999)
        assert state == 999

    @pytest.mark.asyncio
    async def test_sensor_get_state_republish(self, clean_config):
        """Test get_state with republish=True."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ConcreteSensor(name="Test", unique_id="sigen_u1", object_id="sigen_o1", unit="W", device_class=DeviceClass.POWER, state_class=StateClass.MEASUREMENT, icon="mdi:test", gain=1.0, precision=2)
            await sensor.get_state(value=10.1234)
            assert sensor.latest_raw_state == 10.1234
            assert await sensor.get_state(republish=True) == 10.12
            assert await sensor.get_state(republish=True, raw=True) == 10.1234

    @pytest.mark.asyncio
    async def test_ac_charger_running_state_get_state(self):
        """Test AC charger running state mapping."""
        with (
            patch.dict(Sensor._used_unique_ids, clear=True),
            patch.dict(Sensor._used_object_ids, clear=True),
            patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super,
        ):
            sensor = ACChargerRunningState(plant_index=0, device_address=1)
            mock_super.return_value = 5
            assert await sensor.get_state() == "Charging"
            mock_super.return_value = 1
            assert await sensor.get_state() == "EV not connected"

    @pytest.mark.asyncio
    async def test_system_time_zone_get_state(self):
        """Test system timezone conversion."""
        with (
            patch.dict(Sensor._used_unique_ids, clear=True),
            patch.dict(Sensor._used_object_ids, clear=True),
            patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super,
        ):
            sensor = SystemTimeZone(plant_index=0)
            mock_super.return_value = 600  # 10 hours
            assert await sensor.get_state() == "UTC+10:00"
            mock_super.return_value = -300  # -5 hours
            assert await sensor.get_state() == "UTC-05:00"

    @pytest.mark.asyncio
    async def test_inverter_firmware_version_trigger_rediscovery(self):
        """Test that firmware version change triggers rediscovery."""
        with (
            patch.dict(Sensor._used_unique_ids, clear=True),
            patch.dict(Sensor._used_object_ids, clear=True),
            patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super,
        ):
            sensor = InverterFirmwareVersion(plant_index=0, device_address=1)
            mock_device = MagicMock()
            mock_device.__getitem__.side_effect = lambda key: "v1.0" if key == "hw" else None
            sensor.parent_device = mock_device

            mock_super.return_value = "v1.0"
            await sensor.get_state()
            assert not hasattr(mock_device, "rediscover") or mock_device.rediscover is not True

            mock_super.return_value = "v2.0"
            await sensor.get_state()
            assert mock_device.rediscover is True


@pytest.mark.asyncio
async def test_make_dc_charger_and_ac_charger_with_monkeypatch(monkeypatch):
    class DummyDC:
        def __init__(self, plant_index, device_address, protocol_version):
            self.via_device = None

    monkeypatch.setattr(main_mod, "DCCharger", DummyDC)
    dc = await main_mod.make_dc_charger(1, 5, Protocol.N_A, "inv-id")
    assert dc.via_device == "inv-id"

    class DummyAC:
        def __init__(self, *args, **kwargs):
            self.via_device = None

    monkeypatch.setattr(main_mod, "get_state", AsyncMock(return_value=(MagicMock(), 7.5)))
    monkeypatch.setattr(main_mod, "ACCharger", DummyAC)

    ac = await main_mod.make_ac_charger(2, None, 8, types.SimpleNamespace(unique_id="plant-uid", protocol_version=Protocol.N_A))
    assert ac.via_device == "plant-uid"


@pytest.mark.asyncio
async def test_make_plant_and_inverter_with_existing_plant(monkeypatch):
    async def fake_get_state_sequence(sensor, *args, **kwargs):
        seq = [(sensor, "SN123"), (sensor, "ModelX"), (sensor, 5000.0), (sensor, 5000.0), (sensor, "FW1"), (sensor, 2.0), (sensor, 0), (sensor, 0)]
        i = call_index["i"]
        call_index["i"] += 1
        return seq[i]

    call_index = {"i": 0}
    monkeypatch.setattr(main_mod, "get_state", fake_get_state_sequence)
    monkeypatch.setattr(main_mod, "Inverter", MagicMock(return_value=MagicMock(unique_id="inv-uid")))

    for sym in ("InverterSerialNumber", "InverterModel", "InverterFirmwareVersion", "PVStringCount", "OutputType", "PACKBCUCount"):
        monkeypatch.setattr(main_mod, sym, lambda *a, **k: MagicMock())

    mock_client = MagicMock()
    mock_client.read_holding_registers = AsyncMock(return_value=MagicMock(isError=lambda: False))

    plant = types.SimpleNamespace(protocol_version=Protocol.V2_8, unique_id="plant-uid", device_address=247)
    inv, returned_plant = await main_mod.make_plant_and_inverter(0, mock_client, 1, plant)
    assert returned_plant is plant


@pytest.mark.asyncio
async def test_test_for_0x02_illegal_data_address_marks_unpublishable(monkeypatch):
    device = types.SimpleNamespace(device_address=247, name="Device")

    class SensorObj(dict):
        def __init__(self):
            super().__init__()
            self.publishable = True
            self.input_type = InputType.HOLDING
            self.count = 1
            self.name = "Sensor"
            self.state_topic = "topic"
            self["platform"] = "sensor"
            self["object_id"] = "obj"

    sensor = SensorObj()
    monkeypatch.setattr(main_mod, "ModbusSensorMixin", SensorObj)
    device.get_sensor = lambda *a, **k: sensor

    class RR:
        def isError(self):
            return True

        @property
        def exception_code(self):
            return 0x02

    class FakeModbus:
        async def read_holding_registers(self, *a, **k):
            return RR()

        comm_params = types.SimpleNamespace(host="x", port=1)

    await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(FakeModbus(), 0, device, 40000)
    assert sensor.publishable is False


@pytest.mark.asyncio
async def test_illegal_data_address_unknown_input_type(clean_config, monkeypatch):
    mock_client = MagicMock()
    mock_device = MagicMock()
    mock_device.device_address = 247

    class MockSensor(dict):
        def __init__(self):
            super().__init__()
            self.publishable = True
            self.input_type = "INVALID_TYPE"
            self.count = 1
            self.name = "BadSensor"
            self.state_topic = "topic"
            self["platform"] = "sensor"
            self["object_id"] = "obj"

    mock_sensor = MockSensor()
    monkeypatch.setattr(main_mod, "ModbusSensorMixin", MockSensor)
    mock_device.get_sensor.return_value = mock_sensor

    with patch("sigenergy2mqtt.main.main.logging.info") as mock_log:
        await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(mock_client, 0, mock_device, 12345)

    assert mock_sensor.publishable is False
    assert mock_log.called


@pytest.mark.asyncio
async def test_make_plant_and_inverter_protocol_probe_sets_default(monkeypatch):
    for sym in ("InverterSerialNumber", "InverterModel", "InverterFirmwareVersion", "PVStringCount", "OutputType", "PACKBCUCount", "PlantRatedChargingPower", "PlantRatedDischargingPower"):
        monkeypatch.setattr(main_mod, sym, lambda *a, **k: MagicMock())

    seq = [(None, "SNX"), (None, "ModelY"), (None, "FW1"), (None, 2.0), (None, 0), (None, 0)]
    calls = {"i": 0}

    async def fake_get_state(*a, **k):
        i = calls["i"]
        calls["i"] += 1
        return seq[i] if i < len(seq) else (None, 0)

    monkeypatch.setattr(main_mod, "get_state", fake_get_state)
    monkeypatch.setattr(main_mod, "PowerPlant", lambda *a, **k: types.SimpleNamespace(protocol_version=a[2], unique_id="p", device_address=247))
    monkeypatch.setattr(main_mod, "Inverter", lambda *a, **k: types.SimpleNamespace(unique_id="i", device_address=1))

    class FakeModbus:
        def __init__(self):
            self.comm_params = types.SimpleNamespace(host="h", port=1)

        async def read_holding_registers(self, *a, **k):
            raise Exception("no")

    inv, plant = await main_mod.make_plant_and_inverter(0, FakeModbus(), 1, None)
    assert plant.protocol_version == Protocol.V1_8


@pytest.mark.asyncio
async def test_async_main_with_full_device_flow(clean_config, monkeypatch):
    mock_device = MagicMock()
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    mock_device.timeout = 1
    mock_device.retries = 0
    mock_device.inverters = [1]
    mock_device.dc_chargers = [1]  # Match inverter address to avoid KeyError
    mock_device.ac_chargers = [1]
    mock_device.registers.read_only = True
    mock_device.device_address = 247
    active_config.mqtt.anonymous = True
    active_config.modbus.clear()
    active_config.modbus.extend([mock_device])

    mock_thread_config = MagicMock()
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_config", lambda *a: mock_thread_config)
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **k: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(connected=True))))

    mock_plant = MagicMock(protocol_version=Protocol.V2_8, has_battery=True, unique_id="p_uid", device_address=247)
    mock_plant.name = "Plant"
    mock_plant.sensors = {f"{active_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}

    mock_inverter = MagicMock(unique_id="i_uid", device_address=1)
    mock_inverter.name = "Inverter"
    monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(mock_inverter, mock_plant)))
    monkeypatch.setattr(main_mod, "test_for_0x02_ILLEGAL_DATA_ADDRESS", AsyncMock())
    monkeypatch.setattr(main_mod, "make_dc_charger", AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(main_mod, "make_ac_charger", AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()
    assert mock_thread_config.add_device.called


@pytest.mark.asyncio
async def test_async_main_with_no_battery(clean_config, monkeypatch):
    mock_device = MagicMock()
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    mock_device.timeout = 1
    mock_device.retries = 0
    mock_device.device_address = 247
    mock_device.inverters = [1]
    mock_device.dc_chargers = []
    mock_device.ac_chargers = []
    mock_device.registers.read_only = True
    active_config.mqtt.anonymous = True
    active_config.modbus.clear()
    active_config.modbus.extend([mock_device])

    mock_plant = MagicMock(has_battery=False, protocol_version=Protocol.V1_8, device_address=247)
    mock_plant.name = "Plant"
    mock_plant.sensors = {f"{active_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}
    mock_si_sensor = MagicMock(publishable=True)
    mock_plant.get_sensor.return_value = mock_si_sensor

    mock_thread_config = MagicMock()
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_config", lambda *a: mock_thread_config)

    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **k: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(connected=True))))
    mock_inverter = MagicMock(unique_id="i_uid", device_address=1)
    mock_inverter.name = "Inverter"
    monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(mock_inverter, mock_plant)))
    monkeypatch.setattr(main_mod, "test_for_0x02_ILLEGAL_DATA_ADDRESS", AsyncMock())
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()
    assert mock_si_sensor.publishable is False


@pytest.mark.asyncio
async def test_async_main_registers_signal_handlers(clean_config, monkeypatch):
    """Test that async_main registers expected signal handlers."""
    # Ensure at least one Modbus device is configured to pass validation
    mock_device = MagicMock()
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    mock_device.inverters = [1]
    mock_device.dc_chargers = []
    mock_device.ac_chargers = []
    mock_device.registers.read_only = True
    mock_device.device_address = 247
    active_config.modbus.clear()
    active_config.modbus.extend([mock_device])

    handlers = {}
    monkeypatch.setattr(signal, "signal", lambda sig, h: handlers.update({sig: h}))
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **h: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(connected=True))))

    mock_plant = MagicMock(protocol_version=Protocol.V1_8, device_address=247, name="Plant")
    mock_plant.sensors = {f"{active_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}
    mock_inverter = MagicMock(unique_id="i_uid", device_address=1)
    mock_inverter.name = "Inverter"
    monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(mock_inverter, mock_plant)))

    await main_mod.async_main()
    assert signal.SIGINT in handlers
    assert signal.SIGTERM in handlers
    assert signal.SIGHUP in handlers
    assert signal.SIGUSR1 in handlers


@pytest.mark.asyncio
async def test_async_main_version_upgrade_flow(clean_config, tmp_path, monkeypatch):
    """Test that version upgrade flow writes the new version to file."""
    # Ensure at least one Modbus device is configured to pass validation
    mock_device = MagicMock()
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    mock_device.inverters = [1]
    mock_device.dc_chargers = []
    mock_device.ac_chargers = []
    mock_device.registers.read_only = True
    mock_device.device_address = 247
    active_config.modbus.clear()
    active_config.modbus.extend([mock_device])

    active_config.home_assistant.enabled = True
    active_config.persistent_state_path = str(tmp_path)
    monkeypatch.setattr(active_config, "version", lambda: "2.0.0")

    ver_file = tmp_path / ".current-version"
    ver_file.write_text("1.0.0")

    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **h: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(connected=True))))

    mock_plant = MagicMock(protocol_version=Protocol.V1_8, device_address=247, name="Plant")
    mock_plant.sensors = {f"{active_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}
    mock_inverter = MagicMock(unique_id="i_uid", device_address=1)
    mock_inverter.name = "Inverter"
    monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(mock_inverter, mock_plant)))

    await main_mod.async_main()
    # Path in main.py is constructed from persistent_state_path
    assert ver_file.read_text() == "2.0.0"


@pytest.mark.asyncio
async def test_async_main_version_upgrade_errors(clean_config, monkeypatch):
    """Test error handling when reading/writing version file."""
    # Ensure at least one Modbus device is configured to pass validation
    mock_device = MagicMock()
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    mock_device.inverters = [1]
    mock_device.dc_chargers = []
    mock_device.ac_chargers = []
    mock_device.registers.read_only = True
    mock_device.device_address = 247
    active_config.modbus.clear()
    active_config.modbus.extend([mock_device])

    active_config.home_assistant.enabled = True
    with patch("sigenergy2mqtt.main.main.Path") as mock_path_cls, patch("sigenergy2mqtt.main.main.logging.error") as mock_log_err:
        mock_file = MagicMock(exists=lambda: True)
        mock_file.open.side_effect = Exception("IO Error")
        mock_path_cls.return_value = mock_file
        monkeypatch.setattr(main_mod, "start", AsyncMock())
        monkeypatch.setattr(signal, "signal", lambda *a: None)
        monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **h: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(connected=True))))

        mock_plant = MagicMock(protocol_version=Protocol.V1_8, device_address=247, name="Plant")
        mock_plant.sensors = {f"{active_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}
        mock_inverter = MagicMock(unique_id="i_uid", device_address=1)
        mock_inverter.name = "Inverter"
        monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(mock_inverter, mock_plant)))

        await main_mod.async_main()
        assert mock_log_err.called


@pytest.mark.asyncio
async def test_make_plant_and_inverter_edge_cases(clean_config, monkeypatch):
    mock_client = MagicMock()
    mock_client.read_holding_registers = AsyncMock(return_value=MagicMock(isError=lambda: False))

    # 1. Duplicate Serial
    monkeypatch.setattr(main_mod, "serial_numbers", ["DUPE123"])

    async def fake_get_state_dupe(s, *a, **k):
        return (s, "DUPE123") if "Serial" in s.__class__.__name__ else (s, None)

    monkeypatch.setattr(main_mod, "get_state", fake_get_state_dupe)

    inv, plant = await main_mod.make_plant_and_inverter(0, mock_client, 1, None)
    assert inv is None

    # 2. Consumption Method forced to CALCULATED
    monkeypatch.setattr(main_mod, "serial_numbers", [])
    active_config.modbus.clear()
    monkeypatch.setattr(active_config, "consumption", ConsumptionMethod.TOTAL, raising=False)

    async def fake_get_state(s, *a, **k):
        m = {"InverterSerialNumber": "SN", "InverterModel": "M", "InverterFirmwareVersion": "F", "PVStringCount": 1.0, "OutputType": 0}
        return s, m.get(s.__class__.__name__, k.get("default_value"))

    monkeypatch.setattr(main_mod, "get_state", fake_get_state)
    monkeypatch.setattr(main_mod, "PowerPlant", MagicMock(return_value=MagicMock(unique_id="p", device_address=247)))
    monkeypatch.setattr(main_mod, "Inverter", MagicMock(return_value=MagicMock(unique_id="i", device_address=1)))

    await main_mod.make_plant_and_inverter(0, mock_client, 1, None)
    assert active_config.consumption == ConsumptionMethod.CALCULATED
