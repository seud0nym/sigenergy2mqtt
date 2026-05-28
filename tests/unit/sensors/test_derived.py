import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Fixtures for mocking to avoid background thread and registry issues
@pytest.fixture(scope="module", autouse=True)
def mock_modules():
    # Mock Metrics
    mock_metrics = MagicMock()
    mock_metrics.modbus_read = AsyncMock()
    mock_metrics.modbus_write = AsyncMock()

    # Mock DeviceRegistry
    mock_registry = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "sigenergy2mqtt.metrics.metrics": mock_metrics,
            "sigenergy2mqtt.devices": mock_registry,
        },
    ):
        yield


from sigenergy2mqtt.common import ConsumptionMethod, DeviceClass, Protocol, StateClass  # noqa: E402
from sigenergy2mqtt.config import Config, _swap_active_config  # noqa: E402
from sigenergy2mqtt.sensors.base import PVPowerSensor, Sensor  # noqa: E402
from sigenergy2mqtt.sensors.plant_derived import (  # noqa: E402
    BatteryChargingPower,
    BatteryDischargingPower,
    GridSensorExportPower,
    GridSensorImportPower,
    PlantConsumedPower,
    TotalLifetimePVEnergy,
    TotalPVPower,
)
from sigenergy2mqtt.sensors.plant_read_only import BatteryPower, GridSensorActivePower, GridStatus, PlantPVPower  # noqa: E402


@pytest.fixture(autouse=True)
def mock_config_all():
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.enabled = True
    cfg.sensor_overrides = {}
    cfg.consumption = ConsumptionMethod.CALCULATED
    mock_modbus = MagicMock()
    mock_modbus.scan_interval.low = 600
    mock_modbus.scan_interval.medium = 60
    mock_modbus.scan_interval.high = 10
    mock_modbus.scan_interval.realtime = 5
    cfg.modbus = [mock_modbus]

    with _swap_active_config(cfg):
        yield cfg


class TestBatteryDerivedPower:
    def test_battery_charging_power(self):
        proxy_battery = MagicMock(spec=BatteryPower)
        proxy_battery.device_class = DeviceClass.POWER
        proxy_battery.state_class = StateClass.MEASUREMENT
        proxy_battery.protocol_version = Protocol.V2_4
        proxy_battery.latest_raw_state = 1000.5

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = BatteryChargingPower(0, proxy_battery)
            sensor.set_source_values(proxy_battery)
            assert sensor.latest_raw_state == 1000.5
            proxy_battery.latest_raw_state = -500.0
            sensor.set_source_values(proxy_battery)
            assert sensor.latest_raw_state == 0

    def test_battery_discharging_power(self):
        proxy_battery = MagicMock(spec=BatteryPower)
        proxy_battery.device_class = DeviceClass.POWER
        proxy_battery.state_class = StateClass.MEASUREMENT
        proxy_battery.protocol_version = Protocol.V2_4
        proxy_battery.latest_raw_state = 100.5

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = BatteryDischargingPower(0, proxy_battery)
            sensor.set_source_values(proxy_battery)
            assert sensor.latest_raw_state == 0
            proxy_battery.latest_raw_state = -500.5
            sensor.set_source_values(proxy_battery)
            assert sensor.latest_raw_state == 500.5


class TestGridDerivedPower:
    def test_grid_export_power(self):
        proxy_grid = MagicMock(spec=GridSensorActivePower)
        proxy_grid.device_class = DeviceClass.POWER
        proxy_grid.state_class = StateClass.MEASUREMENT
        proxy_grid.protocol_version = Protocol.V2_4
        proxy_grid.precision = 1
        proxy_grid.latest_raw_state = -100.2

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = GridSensorExportPower(0, proxy_grid)
            sensor.set_source_values(proxy_grid)
            assert sensor.latest_raw_state == 100.2

    def test_grid_import_power(self):
        proxy_grid = MagicMock(spec=GridSensorActivePower)
        proxy_grid.device_class = DeviceClass.POWER
        proxy_grid.state_class = StateClass.MEASUREMENT
        proxy_grid.protocol_version = Protocol.V2_4
        proxy_grid.precision = 1
        proxy_grid.latest_raw_state = 100.2

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = GridSensorImportPower(0, proxy_grid)
            sensor.set_source_values(proxy_grid)
            assert sensor.latest_raw_state == 100.2
            proxy_grid.latest_raw_state = -50.0
            sensor.set_source_values(proxy_grid)
            assert sensor.latest_raw_state == 0


class TestPlantConsumedPower:
    def test_plant_consumed_power_calculated(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
            sensor.debug_logging = False
            sensor._update_source("battery", -200.0)
            sensor._update_source("grid", 500.0)
            sensor._update_source("pv", 1000.0)
            sensor._set_latest_consumption()
            assert sensor.latest_raw_state == 1700.0

    @pytest.mark.asyncio
    async def test_plant_consumed_power_publish_after_sources(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
            sensor.debug_logging = False

            b = MagicMock(spec=BatteryPower)
            b.latest_raw_state = -200.0

            g = MagicMock(spec=GridSensorActivePower)
            g.latest_raw_state = 500.0

            ppv = MagicMock(spec=PlantPVPower)
            ppv.latest_raw_state = 1000.0

            sensor.set_source_values(b)
            sensor.set_source_values(g)
            sensor.set_source_values(ppv)

            mock_mqtt = AsyncMock()
            mock_modbus = AsyncMock()
            with patch("sigenergy2mqtt.sensors.plant_derived.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
                assert await sensor.publish(mock_mqtt, mock_modbus) is True
                mock_pub.assert_called_once()
                assert sensor.latest_raw_state == 1700.0

    def test_plant_consumed_power_set_source_values(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)

            b = MagicMock(spec=BatteryPower)
            b.latest_raw_state = -200.0

            g = MagicMock(spec=GridSensorActivePower)
            g.latest_raw_state = 500.0

            s = MagicMock(spec=GridStatus)
            s.latest_raw_state = 0

            sensor.set_source_values(b)
            sensor.set_source_values(g)
            sensor.set_source_values(s)

            ppv = MagicMock(spec=PlantPVPower)
            ppv.latest_raw_state = 1000.0

            sensor.set_source_values(ppv)
            assert sensor.latest_raw_state == 1700.0

            # Test TotalLoadPower and GeneralLoadPower branches
            from sigenergy2mqtt.sensors.plant_read_only import GeneralLoadPower, TotalLoadPower

            tlp = MagicMock(spec=TotalLoadPower)
            tlp.unique_id = "tlp"
            tlp.latest_raw_state = 2000.0
            sensor._sources[ConsumptionMethod.TOTAL.value] = PlantConsumedPower.Value()
            sensor.set_source_values(tlp)
            assert sensor._sources[ConsumptionMethod.TOTAL.value].state == 2000.0

            glp = MagicMock(spec=GeneralLoadPower)
            glp.unique_id = "glp"
            glp.latest_raw_state = 1500.0
            sensor._sources[ConsumptionMethod.GENERAL.value] = PlantConsumedPower.Value()
            sensor.set_source_values(glp)
            assert sensor._sources[ConsumptionMethod.GENERAL.value].state == 1500.0


class TestTotalPVPower:
    @pytest.mark.asyncio
    async def test_total_pv_power_aggregation(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class MockPV(Sensor, PVPowerSensor):
                def __init__(self, name, object_id):
                    self["name"] = name
                    self.name = name
                    self.unique_id = self["unique_id"] = object_id
                    self._gain = 1.0
                    self["display_precision"] = 2

                async def _update_internal_state(self, **kwargs):
                    return False

            s1 = MockPV("PV1", "sigen_pv1")
            s1._states = [(time.time(), 0.0)]
            sensor = TotalPVPower(0, s1)
            sensor.debug_logging = False

            with patch("sigenergy2mqtt.sensors.plant_derived.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
                s1.latest_raw_state = 600.0
                sensor.set_source_values(s1)
                assert sensor.latest_raw_state == 600.0
                await sensor.publish(AsyncMock(), AsyncMock())
                mock_pub.assert_called_once()

    def test_total_pv_power_set_source_values(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class MockPV(Sensor, PVPowerSensor):
                def __init__(self, name, object_id):
                    self["name"] = name
                    self.name = name
                    self.unique_id = self["unique_id"] = object_id
                    self._gain = 1.0
                    self["display_precision"] = 2
                    self._states = [(time.time(), 500.0)]

            s1 = MockPV("PV1", "sigen_pv1")
            sensor = TotalPVPower(0, s1)

            # Test direct set_source_values
            sensor.set_source_values(s1)
            assert sensor.latest_raw_state == 500.0


class TestTotalLifetimePVEnergy:
    def test_total_lifetime_pv_energy_set_source_values(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantPVTotalGeneration, ThirdPartyLifetimePVEnergy

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0, PlantPVTotalGeneration(0), ThirdPartyLifetimePVEnergy(0))

            gen = MagicMock(spec=PlantPVTotalGeneration)
            gen.unique_id = "gen"
            gen.latest_raw_state = 1000.0

            tp = MagicMock(spec=ThirdPartyLifetimePVEnergy)
            tp.unique_id = "tp"
            tp.latest_raw_state = 500.0

            # Set first source
            assert sensor.set_source_values(gen) is False
            assert sensor.plant_lifetime_pv_energy == 1000.0

            # Set second source
            assert sensor.set_source_values(tp) is True
            assert sensor.plant_3rd_party_lifetime_pv_energy == 500.0
            assert sensor.latest_raw_state == 1500.0
