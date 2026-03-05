import asyncio
import logging
import os
import signal
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import ConsumptionMethod, DeviceClass, FirmwareVersion, InputType, Protocol, StateClass, UnitOfPower
from sigenergy2mqtt.config import _swap_active_config, active_config
from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.main.thread_config import ThreadConfig
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerRunningState
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion
from sigenergy2mqtt.sensors.plant_read_only import SystemTimeZone


class FmtMock(MagicMock):
    def __format__(self, format_spec):
        return str(self)


class FmtAsyncMock(AsyncMock):
    def __format__(self, format_spec):
        return str(self)


# Use locally aliased function for backward compatibility
configure_logging = main_mod.configure_logging
get_state = main_mod.get_state


@pytest.fixture
def clean_config(monkeypatch):
    """Fixture to ensure Config is clean and mocked appropriately for tests."""
    from sigenergy2mqtt.config import Config

    cfg = Config()
    mock_modbus = MagicMock()
    mock_modbus.scan_interval = MagicMock()
    mock_modbus.scan_interval.__int__ = lambda s: 30
    mock_modbus.scan_interval.low = 600
    mock_modbus.scan_interval.medium = 60
    mock_modbus.scan_interval.high = 10
    mock_modbus.scan_interval.realtime = 5
    cfg.modbus = [mock_modbus]
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


class TestFirmwareVersion:
    def test_parses_full_firmware_version(self):
        parsed = FirmwareVersion("V122R001C00SPC113B717A")

        assert parsed.platform == 122
        assert parsed.release == 1
        assert parsed.variant == 0
        assert parsed.service_pack == 113
        assert parsed.build == 717
        assert parsed.special_id == "A"

    def test_parses_optional_groups_absent(self):
        parsed = FirmwareVersion("V122R001C00SPC112")

        assert parsed.build is None
        assert parsed.special_id is None

    def test_raises_for_invalid_firmware_version(self):
        with pytest.raises(ValueError, match="Invalid firmware format"):
            FirmwareVersion("invalid")


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
            logging.getLogger().setLevel(logging.NOTSET)
            logging.getLogger("pymodbus").setLevel(logging.NOTSET)
            logging.getLogger("paho.mqtt").setLevel(logging.NOTSET)
            logging.getLogger("pvoutput").setLevel(logging.NOTSET)

            main_mod.configure_logging()

            assert logging.getLogger().level == logging.DEBUG
            assert logging.getLogger("pymodbus").level == logging.INFO
            assert logging.getLogger("paho.mqtt").level == logging.WARNING
            assert logging.getLogger("pvoutput").level == logging.ERROR

    def test_configure_logging_tty_format(self, monkeypatch):
        """Test the TTY logging format branch."""
        monkeypatch.setattr(os, "isatty", lambda fd: True)
        monkeypatch.setattr(sys.stdout, "fileno", lambda: 1)

        with patch("logging.basicConfig") as mock_basic:
            main_mod.configure_logging()
            args, kwargs = mock_basic.call_args
            assert "sigenergy2mqtt:" in kwargs["format"]

    def test_configure_logging_docker_format(self, monkeypatch):
        """Test the Docker logging format branch."""
        monkeypatch.setattr(os, "isatty", lambda fd: False)
        monkeypatch.setattr(sys.stdout, "fileno", lambda: 1)
        with patch("sigenergy2mqtt.main.main.Path") as mock_path:
            # Mocking /.dockerenv existance
            mock_path.return_value.is_file.return_value = True
            with patch("logging.basicConfig") as mock_basic:
                main_mod.configure_logging()
                args, kwargs = mock_basic.call_args
                assert "{asctime}" in kwargs["format"]
                assert "sigenergy2mqtt:" not in kwargs["format"]

    def test_configure_logger_level_change_log(self):
        """Test that _configure_logger logs level changes."""
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)
        with patch.object(logger, "log") as mock_log:
            main_mod._configure_logger("test_logger", logging.DEBUG)
            assert mock_log.called


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

        state = await main_mod.get_state(mock_sensor, mock_modbus, "test_device")

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

        state = await main_mod.get_state(mock_sensor, mock_modbus, "test_device", default_value=999)
        assert state == 999

    @pytest.mark.asyncio
    async def test_sensor_get_state_republish(self, clean_config):
        """Test get_state with republish=True."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ConcreteSensor(
                name="Test", unique_id="sigen_u1", object_id="sigen_o1", unit=UnitOfPower.WATT, device_class=DeviceClass.POWER, state_class=StateClass.MEASUREMENT, icon="mdi:test", gain=1.0, precision=2
            )
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


class TestModbusHelpers:
    """Tests for Modbus helper functions."""

    def test_get_modbus_url_unknown(self):
        """Test get_modbus_url with unknown client."""
        assert main_mod.get_modbus_url(None) == "modbus://unknown"
        assert main_mod.get_modbus_url(object()) == "modbus://unknown"

    @pytest.mark.asyncio
    async def test_read_registers_input(self):
        """Test read_registers with INPUT type."""
        mock_client = AsyncMock()
        await main_mod.read_registers(mock_client, 100, 2, 1, InputType.INPUT)
        mock_client.read_input_registers.assert_called_with(100, count=2, device_id=1)

    @pytest.mark.asyncio
    async def test_read_registers_none_client(self):
        """Test read_registers with None client."""
        with pytest.raises(ValueError, match="modbus_client cannot be None"):
            await main_mod.read_registers(None, 0, 1, 1, InputType.HOLDING)

    @pytest.mark.asyncio
    async def test_read_registers_invalid_type(self):
        """Test read_registers with invalid type."""
        mock_client = AsyncMock()
        with pytest.raises(ValueError, match="Unknown input type"):
            await main_mod.read_registers(mock_client, 0, 1, 1, "INVALID")


class TestDiscovery:
    """Tests for discovery and probing functions."""

    @pytest.mark.asyncio
    async def test_probe_protocol_success(self, monkeypatch):
        """Test successful protocol probing."""
        mock_client = AsyncMock()

        class RR:
            def isError(self):
                return False

        monkeypatch.setattr(main_mod, "read_registers", AsyncMock(return_value=RR()))

        version = await main_mod.probe_protocol(mock_client)
        assert version == Protocol.V2_8

    @pytest.mark.asyncio
    async def test_probe_protocol_fallback(self, monkeypatch):
        """Test protocol probing fallback to V1.8."""
        mock_client = AsyncMock()

        class RR:
            def isError(self):
                return True

            exception_code = 0x02

        monkeypatch.setattr(main_mod, "read_registers", AsyncMock(return_value=RR()))

        version = await main_mod.probe_protocol(mock_client)
        assert version == Protocol.V1_8

    @pytest.mark.asyncio
    async def test_probe_optional_interface_error(self, monkeypatch):
        """Test probe_optional_interface with Modbus error."""
        mock_client = AsyncMock()

        class RR:
            def isError(self):
                return True

            exception_code = 0x02

        monkeypatch.setattr(main_mod, "read_registers", AsyncMock(return_value=RR()))

        assert await main_mod.probe_optional_interface(mock_client, 1, "Test") is False

    @pytest.mark.asyncio
    async def test_probe_optional_interface_exception(self, monkeypatch):
        """Test probe_optional_interface with Exception."""
        mock_client = AsyncMock()
        monkeypatch.setattr(main_mod, "read_registers", AsyncMock(side_effect=Exception("BOOM")))

        assert await main_mod.probe_optional_interface(mock_client, 1, "Test") is False


class TestFactories:
    """Tests for device and service factories."""

    @pytest.mark.asyncio
    async def test_make_ac_charger(self):
        """Test make_ac_charger factory."""
        mock_client = AsyncMock()
        mock_plant = MagicMock(unique_id="plant_id", protocol_version=Protocol.V2_8)
        with patch("sigenergy2mqtt.devices.ACCharger.create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock()
            charger = await main_mod.make_ac_charger(0, mock_client, 1, mock_plant)
            assert charger.via_device == "plant_id"

    @pytest.mark.asyncio
    async def test_make_dc_charger(self):
        """Test make_dc_charger factory."""
        with patch("sigenergy2mqtt.devices.DCCharger.create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock()
            charger = await main_mod.make_dc_charger(0, 1, Protocol.V2_8, "inverter_id")
            assert charger.via_device == "inverter_id"

    @pytest.mark.asyncio
    async def test_make_plant_and_inverter_duplicate_sn(self):
        """Test make_plant_and_inverter with duplicate SN."""
        mock_client = AsyncMock()
        seen = {"SN123"}
        with patch("sigenergy2mqtt.main.main.get_state", AsyncMock(return_value="SN123")):
            inv, plant = await main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen)
            assert inv is None
            assert plant is None

    @pytest.mark.asyncio
    async def test_make_plant_and_inverter_missing_model(self):
        """Test make_plant_and_inverter missing model ID error."""
        mock_client = AsyncMock()
        seen = set()
        with patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN123", None]):
            with pytest.raises(ValueError, match="Model ID cannot be None"):
                asyncio.run(main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen))

    @pytest.mark.asyncio
    async def test_make_plant_and_inverter_pv_inverter(self):
        """Test make_plant_and_inverter detection of PVInverter."""
        mock_client = AsyncMock()
        seen = set()
        # SN, Model, RCP, RDP, OutputType
        with (
            patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", None, None, 1, "V122R001C00SPC112B701P"]),
            patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V2_8)),
            patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
            patch("sigenergy2mqtt.devices.PowerPlant.create", AsyncMock(return_value=MagicMock(protocol_version=Protocol.V2_8, unique_id="p1"))),
            patch("sigenergy2mqtt.devices.Inverter.create", AsyncMock(return_value=MagicMock())),
        ):
            inv, plant = await main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen)
            assert inv is not None
            assert plant is not None

    @pytest.mark.asyncio
    async def test_make_plant_and_inverter_spc113_forces_ems_mode_check_false(self, clean_config):
        """Test ems_mode_check forced to False for firmware SPC113+."""
        mock_client = AsyncMock()
        mock_client.comm_params.host = "h"
        mock_client.comm_params.port = 502
        seen = set()
        clean_config.ems_mode_check = True
        with (
            patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", 1000, 1000, 1, "V122R001C00SPC113B717A"]),
            patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V2_8)),
            patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
            patch("sigenergy2mqtt.devices.PowerPlant.create", AsyncMock(return_value=MagicMock(protocol_version=Protocol.V2_8, unique_id="p1"))),
            patch("sigenergy2mqtt.sensors.inverter_read_only.InverterFirmwareVersion.get_state", AsyncMock(return_value="V122R001C00SPC113B717A")),
            patch("sigenergy2mqtt.sensors.inverter_read_only.InverterModel.get_state", AsyncMock(return_value="MDL1")),
            patch("sigenergy2mqtt.sensors.inverter_read_only.PACKBCUCount.get_state", AsyncMock(return_value=1)),
            patch("sigenergy2mqtt.sensors.inverter_read_only.PVStringCount.get_state", AsyncMock(return_value=1)),
            patch("sigenergy2mqtt.sensors.inverter_read_only.InverterSerialNumber.get_state", AsyncMock(return_value="SN1")),
            patch("sigenergy2mqtt.sensors.inverter_read_only.OutputType.get_state", AsyncMock(return_value=1)),
            patch("sigenergy2mqtt.main.main.logging.info") as mock_info,
        ):
            await main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen)
            assert clean_config.ems_mode_check is False
            assert any("Disabling Remote EMS Mode check" in str(call) for call in mock_info.call_args_list)

    @pytest.mark.asyncio
    async def test_make_plant_and_inverter_spc112_keeps_ems_mode_check_config(self, clean_config):
        """Test ems_mode_check remains as configured for firmware below SPC113."""
        mock_client = AsyncMock()
        mock_client.comm_params.host = "h"
        mock_client.comm_params.port = 502
        seen = set()
        clean_config.ems_mode_check = True
        with (
            patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", 1000, 1000, 1, "V122R001C00SPC112B701P"]),
            patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V2_8)),
            patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
            patch("sigenergy2mqtt.devices.PowerPlant.create", AsyncMock(return_value=MagicMock(protocol_version=Protocol.V2_8, unique_id="p1"))),
            patch("sigenergy2mqtt.sensors.inverter_read_only.InverterFirmwareVersion.get_state", AsyncMock(return_value="V122R001C00SPC112B701P")),
            patch("sigenergy2mqtt.sensors.inverter_read_only.InverterModel.get_state", AsyncMock(return_value="MDL1")),
            patch("sigenergy2mqtt.sensors.inverter_read_only.PACKBCUCount.get_state", AsyncMock(return_value=1)),
            patch("sigenergy2mqtt.sensors.inverter_read_only.PVStringCount.get_state", AsyncMock(return_value=1)),
            patch("sigenergy2mqtt.sensors.inverter_read_only.InverterSerialNumber.get_state", AsyncMock(return_value="SN1")),
            patch("sigenergy2mqtt.sensors.inverter_read_only.OutputType.get_state", AsyncMock(return_value=1)),
        ):
            await main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen)
            assert clean_config.ems_mode_check is True

    async def test_make_plant_and_inverter_old_protocol_consumption_reset(self, clean_config):
        """Test consumption reset for old protocols."""
        mock_client = AsyncMock()
        mock_client.comm_params.host = "h"
        mock_client.comm_params.port = 502
        mock_client.__format__ = lambda s, f: "h:502"
        seen = set()
        clean_config.consumption = ConsumptionMethod.CALCULATED
        # SN, Model, RCP, RDP, OutputType
        with (
            patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", 1000, 1000, 1, "V122R001C00SPC112B701P"]),
            patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V1_8)),
            patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
            patch("sigenergy2mqtt.devices.PowerPlant.create", AsyncMock(return_value=MagicMock(protocol_version=Protocol.V1_8, unique_id="p1"))),
            patch("sigenergy2mqtt.devices.Inverter.create", AsyncMock(return_value=MagicMock())),
        ):
            await main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen)
            assert clean_config.consumption == ConsumptionMethod.CALCULATED




    def test_make_plant_and_inverter_passes_firmware_to_powerplant_create(self):
        """Ensure firmware read from inverter is forwarded to PowerPlant.create."""
        mock_client = AsyncMock()
        seen = set()
        mock_plant = MagicMock(protocol_version=Protocol.V2_8, unique_id="p1")

        with (
            patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", 1000, 1000, 1, "V122R001C00SPC113B717A"]),
            patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V2_8)),
            patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
            patch("sigenergy2mqtt.devices.PowerPlant.create", AsyncMock(return_value=mock_plant)) as mock_plant_create,
            patch("sigenergy2mqtt.devices.Inverter.create", AsyncMock(return_value=MagicMock())),
        ):
            asyncio.run(main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen))

            assert mock_plant_create.await_count == 1
            assert mock_plant_create.await_args.args[2] == "V122R001C00SPC113B717A"

    def test_make_plant_and_inverter_existing_plant_skips_output_type_and_firmware_reads(self):
        """When plant already exists, only inverter is created and no plant-only reads occur."""
        mock_client = AsyncMock()
        seen = set()
        existing_plant = MagicMock(protocol_version=Protocol.V2_8, unique_id="p-existing")

        with (
            patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", 1000, 1000]) as mock_get_state,
            patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
            patch("sigenergy2mqtt.devices.Inverter.create", AsyncMock(return_value=MagicMock())),
            patch("sigenergy2mqtt.devices.PowerPlant.create", AsyncMock()) as mock_plant_create,
        ):
            asyncio.run(main_mod.make_plant_and_inverter(0, mock_client, 1, existing_plant, seen))

            assert mock_get_state.await_count == 4
            mock_plant_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_make_plant_and_inverter_missing_output_type(self, clean_config):
        """Test make_plant_and_inverter missing OutputType error."""
        mock_client = AsyncMock()
        mock_client.comm_params.host = "h"
        mock_client.comm_params.port = 502
        mock_client.__format__ = lambda s, f: "h:502"
        seen = set()
        # SN, Model, RCP, RDP, OutputType (returns None)
        with (
            patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", 1000, 1000, None]),
            patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V2_8)),
            patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
        ):
            with pytest.raises(ValueError, match="OutputType cannot be None"):
                await main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen)


@pytest.mark.asyncio
async def test_probe_protocol_candidates_and_error(monkeypatch):
    """Test protocol probing through candidates with errors/exceptions."""
    mock_client = AsyncMock()
    mock_client.comm_params.host = "h"
    mock_client.comm_params.port = 502

    class RR:
        def __init__(self, error):
            self._error = error

        def isError(self):
            return self._error

        def __format__(self, format_spec):
            return "RR"

        def __str__(self):
            return "RR"

        exception_code = 0x02

    # Mocking read_registers to fail first 3, succeed on 4th (V2_5)
    responses = [RR(True), RR(True), Exception("BOOM"), RR(False)]
    monkeypatch.setattr(main_mod, "read_registers", AsyncMock(side_effect=responses))

    # Should hit the exception (V2_6 branch) then succeed on V2_5
    version = await main_mod.probe_protocol(mock_client)
    assert version == Protocol.V2_5

    # Test complete failure fallback to V1_8
    monkeypatch.setattr(main_mod, "read_registers", AsyncMock(return_value=RR(True)))
    version = await main_mod.probe_protocol(mock_client)
    assert version == Protocol.V1_8


@pytest.mark.asyncio
async def test_probe_optional_interface_success(monkeypatch):
    """Test successful probe_optional_interface."""
    mock_client = AsyncMock()
    mock_client.comm_params.host = "h"
    mock_client.comm_params.port = 502

    class RR:
        def isError(self):
            return False

        def __str__(self):
            return "RR"

        def __format__(self, format_spec):
            return "RR"

    monkeypatch.setattr(main_mod, "read_registers", AsyncMock(return_value=RR()))
    assert await main_mod.probe_optional_interface(mock_client, 1, "Test") is True


@pytest.mark.asyncio
async def test_test_for_0x02_illegal_data_address_marks_unpublishable(monkeypatch):
    device = MagicMock()
    device.device_address = 247
    device.name = "Device"
    device.__format__ = lambda s, f: "Device"

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

        def __format__(self, format_spec):
            return "Sensor"

    sensor = SensorObj()
    monkeypatch.setattr(main_mod, "ModbusSensorMixin", SensorObj)
    device.get_sensor = lambda *a, **k: sensor

    class RR:
        def isError(self):
            return True

        def __str__(self):
            return "RR"

        def __format__(self, format_spec):
            return "RR"

        @property
        def exception_code(self):
            return 0x02

    class FakeModbus:
        async def read_holding_registers(self, *a, **k):
            return RR()

        comm_params = types.SimpleNamespace(host="x", port=1)

        def __str__(self):
            return "FakeModbus"

        def __format__(self, format_spec):
            return "FakeModbus"

    await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(FakeModbus(), 0, device, 40000)
    assert sensor.publishable is False


@pytest.mark.asyncio
async def test_illegal_data_address_unknown_input_type(clean_config, monkeypatch):
    mock_client = MagicMock()
    mock_client.comm_params.host = "h"
    mock_client.comm_params.port = 502
    mock_client.__str__ = lambda x: "MockClient"
    mock_client.__format__ = lambda x, f: "MockClient"
    mock_device = MagicMock()
    mock_device.device_address = 247
    mock_device.name = "Device"
    mock_device.__format__ = lambda x, f: "Device"

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

        def __format__(self, format_spec):
            return "BadSensor"

    mock_sensor = MockSensor()
    monkeypatch.setattr(main_mod, "ModbusSensorMixin", MockSensor)
    mock_device.get_sensor.return_value = mock_sensor

    with patch("sigenergy2mqtt.main.main.logging.info") as mock_log:
        await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(mock_client, 0, mock_device, 12345)

    assert mock_sensor.publishable is False
    assert mock_log.called


@pytest.mark.asyncio
async def test_test_for_0x02_illegal_data_address_not_publishable(monkeypatch):
    """Test the continue branch when sensor is not publishable."""
    device = FmtMock()
    device.name = "TestDevice"
    sensor = FmtMock(publishable=False)
    sensor.name = "TestSensor"
    device.get_sensor.return_value = sensor

    mock_client = FmtAsyncMock()
    mock_client.comm_params.host = "h"
    mock_client.comm_params.port = 502

    await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(mock_client, 0, device, 123)
    assert not mock_client.read_holding_registers.called


@pytest.mark.asyncio
async def test_setup_devices_ignored_host(clean_config):
    """Test branch where Modbus host is ignored (no registers enabled)."""
    clean_config.modbus[0].registers.read_only = False
    clean_config.modbus[0].registers.read_write = False
    clean_config.modbus[0].registers.write_only = False
    seen = set()
    configs, proto = await main_mod.setup_devices(seen)
    assert len(configs) == 0


@pytest.mark.asyncio
async def test_setup_devices_connection_failure(clean_config, monkeypatch):
    """Test connection failure in setup_devices."""
    mock_client = FmtAsyncMock(connected=False)
    # Ensure nested attributes used in f-strings are also FmtMocks
    mock_client.comm_params = FmtMock()
    mock_client.comm_params.host = "h"
    mock_client.comm_params.port = 502
    mock_client.__str__ = lambda x: "h:502"
    mock_client.__aenter__.return_value = mock_client
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **k: mock_client)

    # Also need to mock active_config.modbus[plant_index] attributes
    clean_config.modbus[0] = FmtMock(wraps=clean_config.modbus[0])
    clean_config.modbus[0].host = "h"
    clean_config.modbus[0].port = 502

    with pytest.raises(SystemExit):
        await main_mod.setup_devices(set())


@pytest.mark.asyncio
async def test_coverage_gap_closers(clean_config, monkeypatch):
    """Test specific lines and branches identified as missing coverage."""
    # Line 246-247: consumption reset warning
    mock_client = AsyncMock()
    mock_client.comm_params.host = "h"
    mock_client.comm_params.port = 502
    seen = set()
    clean_config.consumption = ConsumptionMethod.TOTAL
    with (
        patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN1", "MDL1", 1000, 1000, 1, "V122R001C00SPC112B701P"]),
        patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V1_8)),
        patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
        patch("sigenergy2mqtt.devices.PowerPlant.create", AsyncMock(return_value=MagicMock(protocol_version=Protocol.V1_8, unique_id="p1"))),
        patch("sigenergy2mqtt.devices.Inverter.create", AsyncMock(return_value=MagicMock())),
        patch("sigenergy2mqtt.main.main.logging.warning") as mock_warn,
    ):
        await main_mod.make_plant_and_inverter(0, mock_client, 1, None, seen)
        assert clean_config.consumption == ConsumptionMethod.CALCULATED
        assert mock_warn.called

    # Line 254: plant already exists branch
    mock_plant = MagicMock(protocol_version=Protocol.V2_8, unique_id="p1")
    with (
        patch("sigenergy2mqtt.main.main.get_state", side_effect=["SN2", "MDL1", 1000, 1000, 1]),
        patch("sigenergy2mqtt.main.main.probe_protocol", AsyncMock(return_value=Protocol.V2_8)),
        patch("sigenergy2mqtt.main.main.probe_optional_interface", AsyncMock(return_value=False)),
        patch("sigenergy2mqtt.devices.Inverter.create", AsyncMock(return_value=MagicMock())),
    ):
        inv, plant = await main_mod.make_plant_and_inverter(0, mock_client, 1, mock_plant, seen)
        assert plant is mock_plant

    # Line 281: sensor and sensor.publishable branch
    device = MagicMock()
    device.device_address = 1
    device.get_sensor.return_value = None
    await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(mock_client, 0, device, 123)
    # Just verifying no crash, as it hits 'continue'


@pytest.mark.asyncio
async def test_setup_services_comprehensive(clean_config):
    """Test setup_services with various enabled/disabled parts."""
    clean_config.metrics_enabled = True
    clean_config.pvoutput.enabled = True
    clean_config.influxdb.enabled = True
    clean_config.log_level = logging.DEBUG
    clean_config.clean = False

    configs = [ThreadConfig("Test", "host", 502)]

    with (
        patch("sigenergy2mqtt.main.main.get_pvoutput_services", return_value=[MagicMock()]),
        patch("sigenergy2mqtt.main.main.get_influxdb_services", return_value=[MagicMock()]),
    ):
        result = main_mod.setup_services(configs, Protocol.V2_8)
        # Should have Services thread at 0 and Monitor thread at end
        assert result[0].name == "Services"
        assert result[-1].name == "Monitor"
        assert len(result) == 3


def test_exit_on_signal(clean_config):
    """Test exit_on_signal logic."""
    mock_config = MagicMock()
    configs = [mock_config]
    main_mod.setup_signals(configs)

    with patch("signal.signal") as mock_sig:
        main_mod.setup_signals(configs)
        # Find SIGINT handler
        handler = [call.args[1] for call in mock_sig.call_args_list if call.args[0] == signal.SIGINT][0]
        handler(signal.SIGINT, None)
        assert mock_config.offline.called


@pytest.mark.asyncio
async def test_setup_dc_chargers_missing_inverter(clean_config):
    """Test DC charger with no associated inverter warning."""
    mock_modbus_cfg = MagicMock(dc_chargers=[2], host="h", port=502)
    mock_plant = MagicMock()
    mock_config = MagicMock()
    with patch("sigenergy2mqtt.main.main.logging.warning") as mock_warn:
        await main_mod._setup_dc_chargers(0, mock_modbus_cfg, mock_plant, {1: "inv1"}, mock_config)
        assert mock_warn.called


@pytest.mark.asyncio
async def test_setup_ac_chargers_older_protocol(clean_config):
    """Test AC Chargers not supported warning."""
    mock_modbus_cfg = MagicMock(ac_chargers=[1], host="h", port=502)
    mock_plant = MagicMock()
    mock_config = MagicMock()
    with patch("sigenergy2mqtt.main.main.logging.warning") as mock_warn:
        await main_mod._setup_ac_chargers(0, mock_modbus_cfg, mock_plant, AsyncMock(), mock_config, Protocol.V1_8)
        assert mock_warn.called


class TestSignals:
    """Tests for signal handlers."""

    def test_configure_for_restart(self, clean_config):
        """Test configure_for_restart signal handler."""
        configs = [MagicMock()]
        main_mod.setup_signals(configs)
        # Find the USR1 handler (it should be the one calling configure_for_restart)
        with patch("signal.signal") as mock_sig:
            main_mod.setup_signals(configs)
            # Find the handler for SIGUSR1
            handler = [call.args[1] for call in mock_sig.call_args_list if call.args[0] == signal.SIGUSR1][0]
            handler(signal.SIGUSR1, None)
            assert active_config.home_assistant.enabled is False

    def test_reload_on_signal(self, clean_config):
        """Test reload_on_signal signal handler."""
        configs = [MagicMock()]
        with patch("signal.signal") as mock_sig, patch.object(active_config, "reload") as mock_reload:
            main_mod.setup_signals(configs)
            handler = [call.args[1] for call in mock_sig.call_args_list if call.args[0] == signal.SIGHUP][0]
            handler(signal.SIGHUP, None)
            assert mock_reload.called


class TestUpgrade:
    """Tests for upgrade version check."""

    def test_check_upgrade_no_ha(self, clean_config):
        """Test check_upgrade returns False if HA not enabled."""
        clean_config.home_assistant.enabled = False
        assert main_mod.check_upgrade() is False

    def test_check_upgrade_version_match(self, clean_config, tmp_path):
        """Test check_upgrade returns False if versions match."""
        clean_config.home_assistant.enabled = True
        clean_config.persistent_state_path = str(tmp_path)
        ver_file = tmp_path / ".current-version"
        ver_file.write_text(active_config.version())
        assert main_mod.check_upgrade() is False


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
    monkeypatch.setattr(main_mod.thread_config_registry, "get_config", lambda *a: mock_thread_config)
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
    monkeypatch.setattr(main_mod.thread_config_registry, "get_config", lambda *a: mock_thread_config)

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
