"""Unit tests for the three modbus_test_server fixes.

Covers:
- _get_initial_value() returns ("write_only_sensor") for WriteOnlySensorMixin sensors.
- add_sensor() seeds _initial_registers and registers the address for write-only sensors,
  so that build_sim_device() includes the address in SimData (preventing ILLEGAL_ADDRESS).
- DEBUG log records are emitted when the logger level is set to DEBUG.
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor, WriteOnlySensorMixin
from sigenergy2mqtt.sensors.inverter_read_write import DCChargerStatus
from sigenergy2mqtt.sensors.plant_read_write import PlantStatus
from tests.utils.modbus_test_server import CustomDataBlock, LatencyBudget


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
    from sigenergy2mqtt.config.settings import ModbusConfig

    cfg = Config()
    mc = ModbusConfig(host="127.0.0.1", port=502, inverters=[1])
    cfg.modbus = [mc]
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.enabled = True
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.device_name_prefix = ""
    cfg.home_assistant.republish_discovery_interval = 0
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.home_assistant.enabled_by_default = True
    cfg.persistent_state_path = Path(".")

    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()

    with _swap_active_config(cfg):
        yield cfg

    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


def _make_data_block(device_address: int = 2) -> CustomDataBlock:
    """Return a CustomDataBlock with no MQTT client."""
    return CustomDataBlock(device_address, mqtt_client=None, latency_budget=LatencyBudget())


# ---------------------------------------------------------------------------
# Helpers to instantiate concrete WriteOnlySensor instances
# ---------------------------------------------------------------------------


def _make_dc_charger_status(mock_config) -> DCChargerStatus:
    """Instantiate a DCChargerStatus sensor (a concrete WriteOnlySensor)."""
    return DCChargerStatus(
        plant_index=1,
        device_address=2,
    )


def _make_plant_status(mock_config) -> PlantStatus:
    """Instantiate a PlantStatus sensor (a concrete WriteOnlySensor)."""
    return PlantStatus(
        plant_index=1,
    )


# ---------------------------------------------------------------------------
# Test 1 — _get_initial_value returns write_only_sensor for WriteOnlySensorMixin
# ---------------------------------------------------------------------------


class TestGetInitialValueWriteOnly:
    """_get_initial_value must return source='write_only_sensor' and value=value_off."""

    def test_dc_charger_status_source(self, mock_config):
        """DCChargerStatus _get_initial_value should return 'write_only_sensor' source."""
        sensor = _make_dc_charger_status(mock_config)
        block = _make_data_block(device_address=sensor.device_address)

        value, source = block._get_initial_value(sensor)

        assert source == "write_only_sensor", (
            f"Expected source='write_only_sensor', got {source!r}"
        )

    def test_dc_charger_status_value_is_off(self, mock_config):
        """_get_initial_value should return value_off (0) as the initial value."""
        sensor = _make_dc_charger_status(mock_config)
        block = _make_data_block(device_address=sensor.device_address)

        value, source = block._get_initial_value(sensor)

        assert value == sensor._values["off"], (
            f"Expected value={sensor._values['off']!r}, got {value!r}"
        )

    def test_plant_status_source(self, mock_config):
        """PlantStatus _get_initial_value should also return 'write_only_sensor'."""
        sensor = _make_plant_status(mock_config)
        block = _make_data_block(device_address=sensor.device_address)

        value, source = block._get_initial_value(sensor)

        assert source == "write_only_sensor"
        assert isinstance(value, int)


# ---------------------------------------------------------------------------
# Test 2 — add_sensor seeds _initial_registers and registers address
# ---------------------------------------------------------------------------


class TestAddSensorWriteOnly:
    """add_sensor must register the address and seed _initial_registers for write-only sensors.

    If either of these is missing, build_sim_device() will omit the address from SimData
    and pymodbus will return ILLEGAL_ADDRESS for any Modbus write to that address.
    """

    def test_address_registered(self, mock_config):
        """add_sensor must add the sensor address to block.addresses."""
        sensor = _make_dc_charger_status(mock_config)
        block = _make_data_block(device_address=sensor.device_address)

        block.add_sensor(sensor)

        assert sensor.address in block.addresses, (
            f"Address {sensor.address} not found in block.addresses after add_sensor()"
        )

    def test_initial_registers_seeded(self, mock_config):
        """add_sensor must write at least one value into _initial_registers."""
        sensor = _make_dc_charger_status(mock_config)
        block = _make_data_block(device_address=sensor.device_address)

        block.add_sensor(sensor)

        seeded = [
            addr
            for addr in range(sensor.address, sensor.address + sensor.count)
            if addr in block._initial_registers
        ]
        assert seeded, (
            f"No registers seeded for addresses {sensor.address}-{sensor.address + sensor.count - 1}; "
            "build_sim_device() would omit them from SimData, causing ILLEGAL_ADDRESS on writes."
        )

    def test_build_sim_device_includes_address(self, mock_config):
        """build_sim_device must include write-only sensor addresses in the SimData list."""
        sensor = _make_dc_charger_status(mock_config)
        block = _make_data_block(device_address=sensor.device_address)
        block.add_sensor(sensor)

        sim_device = block.build_sim_device()

        sim_addresses = {sd.address for sd in sim_device.simdata}
        assert sensor.address in sim_addresses, (
            f"Address {sensor.address} missing from SimDevice.simdata; "
            "Modbus writes to this address will return ILLEGAL_ADDRESS."
        )

    def test_no_mqtt_subscription_attempted(self, mock_config):
        """add_sensor must not attempt MQTT subscription for write-only sensors."""
        sensor = _make_dc_charger_status(mock_config)
        block = _make_data_block(device_address=sensor.device_address)

        # Provide an mqtt_client to verify that _register_mqtt_topic skips write-only sensors.
        mock_mqtt = MagicMock()
        mock_handler = MagicMock()
        mock_handler.register = MagicMock()
        mock_mqtt.user_data_get.return_value = mock_handler
        block._mqtt_client = mock_mqtt

        block.add_sensor(sensor)

        # register() should not have been called for a write-only sensor
        mock_handler.register.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3 — DEBUG log records are emitted when logger level is DEBUG
# ---------------------------------------------------------------------------


class TestDebugLogging:
    """When _logger is set to DEBUG, debug records must reach attached handlers."""

    def test_debug_records_emitted_at_debug_level(self):
        """A debug log record must be captured when _logger.level == DEBUG."""
        import tests.utils.modbus_test_server as server_module

        logger = server_module._logger
        original_level = logger.level
        original_propagate = logger.propagate

        records: list[logging.LogRecord] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _CapturingHandler()
        try:
            logger.setLevel(logging.DEBUG)
            logger.propagate = False
            logger.addHandler(handler)

            logger.debug("test_debug_record")

            assert any(r.getMessage() == "test_debug_record" for r in records), (
                "No DEBUG record captured — logger is not emitting at DEBUG level."
            )
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)
            logger.propagate = original_propagate

    def test_debug_records_suppressed_at_info_level(self):
        """DEBUG records must be suppressed when _logger.level == INFO."""
        import tests.utils.modbus_test_server as server_module

        logger = server_module._logger
        original_level = logger.level
        original_propagate = logger.propagate

        records: list[logging.LogRecord] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _CapturingHandler()
        try:
            logger.setLevel(logging.INFO)
            logger.propagate = False
            logger.addHandler(handler)

            logger.debug("should_not_appear")

            assert not any(r.getMessage() == "should_not_appear" for r in records), (
                "DEBUG record appeared even though logger level is INFO."
            )
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)
            logger.propagate = original_propagate

    @pytest.mark.asyncio
    async def test_registers_to_debug_promotes_level(self, mock_config, monkeypatch):
        """When registers_to_debug is set, run_async_server must promote the logger to DEBUG."""
        import tests.utils.modbus_test_server as server_module
        from tests.utils.modbus_test_server import TestConfig, run_async_server

        monkeypatch.setattr("tests.utils.modbus_test_server.ModbusTcpServer.serve_forever", AsyncMock())

        original_level = server_module._logger.level
        original_registers = TestConfig.registers_to_debug[:]
        try:
            TestConfig.registers_to_debug = [41000]
            await run_async_server(mqtt_client=None, modbus_client=None, use_simplified_topics=False, host="127.0.0.1", port=0, log_level=logging.INFO)
            assert server_module._logger.isEnabledFor(logging.DEBUG), (
                "_logger must be at DEBUG level when registers_to_debug is non-empty."
            )
        finally:
            TestConfig.registers_to_debug = original_registers
            server_module._logger.setLevel(original_level)
