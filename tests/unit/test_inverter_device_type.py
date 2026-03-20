"""
Unit tests for Inverter device creation with different DeviceTypes.

Verifies that Inverter.create() works correctly with each valid DeviceType
(HybridInverter, PVInverter), and that the sensors registered on the inverter
inherit the correct device type.

Also covers the regression where PACKBCUCount.get_state was called for
PVInverter devices, causing a failure because PACKBCUCount only applies
to HybridInverter devices.
"""

from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import HybridInverter, Protocol, PVInverter
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.inverter.inverter import Inverter
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.inverter_read_only import PACKBCUCount


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


@pytest.fixture
def mock_config():
    cfg = Config()
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.enabled = True
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.home_assistant.device_name_prefix = ""
    cfg.modbus = [MagicMock()]
    cfg.modbus[0].scan_interval.high = 10
    cfg.modbus[0].scan_interval.realtime = 5
    cfg.modbus[0].scan_interval.low = 600
    cfg.modbus[0].scan_interval.medium = 60
    cfg.modbus[0].registers = None
    cfg.modbus[0].smartport.enabled = False
    cfg.sensor_overrides = {}

    with _swap_active_config(cfg):
        yield cfg


def _mock_get_state(default_values: dict[str, object] | None = None):
    """Create a mock for ReadOnlySensor.get_state that returns type-appropriate values.

    Args:
        default_values: Optional mapping of sensor class name to return value.
    """
    defaults = {
        "InverterModel": "SigenStor EC 10.0 SP",
        "PVStringCount": 2,
        "InverterFirmwareVersion": "v2.0.1",
        "InverterSerialNumber": "TEST123456",
        "PACKBCUCount": 0,
        "OutputType": 0,  # L/N = 1 phase
    }
    if default_values:
        defaults.update(default_values)

    async def _get_state(self, *args, **kwargs):
        class_name = self.__class__.__name__
        if class_name in defaults:
            value = defaults[class_name]
            self.set_state(value)
            return value
        return None

    return _get_state


class TestInverterCreateWithDeviceType:
    """Test Inverter.create() with each valid DeviceType."""

    @pytest.mark.asyncio
    async def test_create_hybrid_inverter(self, mock_config):
        """Inverter.create() should succeed with HybridInverter device type."""
        mock_modbus = MagicMock()
        device_type = HybridInverter()

        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state()):
            inverter = await Inverter.create(
                plant_index=0,
                device_address=1,
                device_type=device_type,
                protocol_version=Protocol.V2_4,
                modbus_client=mock_modbus,
            )

        assert inverter is not None
        assert isinstance(inverter._device_type, HybridInverter)

    @pytest.mark.asyncio
    async def test_create_pv_inverter(self, mock_config):
        """Inverter.create() should succeed with PVInverter device type."""
        mock_modbus = MagicMock()
        device_type = PVInverter()

        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state()):
            inverter = await Inverter.create(
                plant_index=0,
                device_address=1,
                device_type=device_type,
                protocol_version=Protocol.V2_4,
                modbus_client=mock_modbus,
            )

        assert inverter is not None
        assert isinstance(inverter._device_type, PVInverter)


class TestInverterSensorDeviceTypeInheritance:
    """Test that sensors registered on an Inverter inherit the correct device type."""

    @pytest.mark.asyncio
    async def test_hybrid_inverter_sensors_inherit_hybrid(self, mock_config):
        """All sensors on a HybridInverter device must be instances of HybridInverter."""
        mock_modbus = MagicMock()
        device_type = HybridInverter()

        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state({"PACKBCUCount": 0})):
            inverter = await Inverter.create(
                plant_index=0,
                device_address=1,
                device_type=device_type,
                protocol_version=Protocol.V2_4,
                modbus_client=mock_modbus,
            )

        for sensor in inverter.all_sensors.values():
            assert isinstance(sensor, HybridInverter), f"Sensor {sensor.__class__.__name__} (unique_id={sensor.unique_id}) on HybridInverter device does not inherit HybridInverter"

    @pytest.mark.asyncio
    async def test_pv_inverter_sensors_inherit_pv(self, mock_config):
        """All sensors on a PVInverter device must be instances of PVInverter."""
        mock_modbus = MagicMock()
        device_type = PVInverter()

        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state()):
            inverter = await Inverter.create(
                plant_index=0,
                device_address=1,
                device_type=device_type,
                protocol_version=Protocol.V2_4,
                modbus_client=mock_modbus,
            )

        for sensor in inverter.all_sensors.values():
            assert isinstance(sensor, PVInverter), f"Sensor {sensor.__class__.__name__} (unique_id={sensor.unique_id}) on PVInverter device does not inherit PVInverter"

    @pytest.mark.asyncio
    async def test_hybrid_has_more_sensors_than_pv(self, mock_config):
        """HybridInverter should register more sensors than PVInverter.

        HybridInverter has battery-related sensors (e.g. PACKBCUCount,
        ReservedDailyExportEnergy) that PVInverter does not.
        """
        mock_modbus = MagicMock()

        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state({"PACKBCUCount": 0})):
            hybrid = await Inverter.create(
                plant_index=0,
                device_address=1,
                device_type=HybridInverter(),
                protocol_version=Protocol.V2_4,
                modbus_client=mock_modbus,
            )

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state()):
                pv = await Inverter.create(
                    plant_index=0,
                    device_address=1,
                    device_type=PVInverter(),
                    protocol_version=Protocol.V2_4,
                    modbus_client=mock_modbus,
                )

        hybrid_count = len(hybrid.all_sensors)
        pv_count = len(pv.all_sensors)

        assert hybrid_count > pv_count, f"HybridInverter ({hybrid_count} sensors) should have more sensors than PVInverter ({pv_count} sensors)"

    @pytest.mark.asyncio
    async def test_pack_bcu_count_on_hybrid_only(self, mock_config):
        """PACKBCUCount sensor should only appear on HybridInverter, not PVInverter."""
        mock_modbus = MagicMock()

        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state({"PACKBCUCount": 0})):
            hybrid = await Inverter.create(
                plant_index=0,
                device_address=1,
                device_type=HybridInverter(),
                protocol_version=Protocol.V2_4,
                modbus_client=mock_modbus,
            )

        has_pack_bcu_on_hybrid = any(isinstance(s, PACKBCUCount) for s in hybrid.all_sensors.values())
        assert has_pack_bcu_on_hybrid, "PACKBCUCount should be registered on HybridInverter"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", _mock_get_state()):
                pv = await Inverter.create(
                    plant_index=0,
                    device_address=1,
                    device_type=PVInverter(),
                    protocol_version=Protocol.V2_4,
                    modbus_client=mock_modbus,
                )

        has_pack_bcu_on_pv = any(isinstance(s, PACKBCUCount) for s in pv.all_sensors.values())
        assert not has_pack_bcu_on_pv, "PACKBCUCount should NOT be registered on PVInverter"
