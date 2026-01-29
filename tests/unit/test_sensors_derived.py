import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock circular dependencies and other imports
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types

# Mock Metrics
mock_metrics = MagicMock()
mock_metrics.modbus_read = AsyncMock()
mock_metrics.modbus_write = AsyncMock()
sys.modules["sigenergy2mqtt.metrics.metrics"] = mock_metrics

# Mock DeviceRegistry
mock_registry = MagicMock()
sys.modules["sigenergy2mqtt.devices"] = mock_registry

from sigenergy2mqtt.common import ConsumptionMethod, Protocol  # noqa: E402
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
    with patch("sigenergy2mqtt.sensors.plant_derived.Config") as mock_config:
        mock_config.home_assistant.unique_id_prefix = "sigenergy"
        mock_config.home_assistant.entity_id_prefix = "sigenergy"
        mock_config.home_assistant.enabled = True
        mock_config.sensor_overrides = {}
        mock_config.consumption = ConsumptionMethod.CALCULATED
        mock_dev = MagicMock()
        mock_dev.smartport.enabled = False
        mock_config.modbus = [mock_dev]
        yield mock_config


class TestBatteryDerivedPower:
    def test_battery_charging_power(self):
        class ProxyBatteryPower(BatteryPower):
            def __init__(self):
                self.protocol_version = Protocol.V2_4
                self["device_class"] = MagicMock()
                self.state_class = self["state_class"] = MagicMock()
                self.precision = 2

        proxy_battery = ProxyBatteryPower()
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = BatteryChargingPower(0, proxy_battery)
            sensor.set_source_values(proxy_battery, [(time.time(), 1000.5)])
            assert sensor.latest_raw_state == 1000.5
            sensor.set_source_values(proxy_battery, [(time.time(), -500.0)])
            assert sensor.latest_raw_state == 0

    def test_battery_discharging_power(self):
        class ProxyBatteryPower(BatteryPower):
            def __init__(self):
                self.protocol_version = Protocol.V2_4
                self["device_class"] = MagicMock()
                self.state_class = self["state_class"] = MagicMock()
                self.precision = 2

        proxy_battery = ProxyBatteryPower()
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = BatteryDischargingPower(0, proxy_battery)
            sensor.set_source_values(proxy_battery, [(time.time(), 1000.0)])
            assert sensor.latest_raw_state == 0
            sensor.set_source_values(proxy_battery, [(time.time(), -500.5)])
            assert sensor.latest_raw_state == 500.5


class TestGridDerivedPower:
    def test_grid_export_power(self):
        class ProxyGridPower(GridSensorActivePower):
            def __init__(self):
                self.protocol_version = Protocol.V2_4
                self["device_class"] = MagicMock()
                self.state_class = self["state_class"] = MagicMock()
                self["display_precision"] = 1
                self.precision = 1

        proxy_grid = ProxyGridPower()
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = GridSensorExportPower(0, proxy_grid)
            sensor.set_source_values(proxy_grid, [(time.time(), -100.2)])
            assert sensor.latest_raw_state == 100.2

    def test_grid_import_power(self):
        class ProxyGridPower(GridSensorActivePower):
            def __init__(self):
                self.protocol_version = Protocol.V2_4
                self["device_class"] = MagicMock()
                self.state_class = self["state_class"] = MagicMock()
                self["display_precision"] = 1
                self.precision = 1

        proxy_grid = ProxyGridPower()
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = GridSensorImportPower(0, proxy_grid)
            sensor.set_source_values(proxy_grid, [(time.time(), 100.2)])
            assert sensor.latest_raw_state == 100.2
            sensor.set_source_values(proxy_grid, [(time.time(), -50.0)])
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
    async def test_plant_consumed_power_notify(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)
            sensor.debug_logging = False
            sensor._update_source("grid", 500.0)
            sensor._update_source("pv", 1000.0)
            mock_mqtt = AsyncMock()
            mock_modbus = AsyncMock()
            with patch("sigenergy2mqtt.sensors.plant_derived.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
                await sensor.notify(mock_modbus, mock_mqtt, -200.0, "battery", MagicMock())
                assert sensor.latest_raw_state == 1700.0
                mock_pub.assert_called_once()

    def test_plant_consumed_power_set_source_values(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PlantConsumedPower(0, ConsumptionMethod.CALCULATED)

            class P_BatteryPower(BatteryPower):
                def __init__(self):
                    pass

            class P_GridPower(GridSensorActivePower):
                def __init__(self):
                    pass

            class P_GridStatus(GridStatus):
                def __init__(self):
                    pass

            b = P_BatteryPower()
            g = P_GridPower()
            s = P_GridStatus()
            sensor.set_source_values(b, [(0, -200.0)])
            sensor.set_source_values(g, [(0, 500.0)])
            sensor.set_source_values(s, [(0, 0)])

            class P_PlantPV(PlantPVPower, PVPowerSensor):
                def __init__(self):
                    self["unique_id"] = "ppv_uid"
                    self._gain = 1.0

                @property
                def unique_id(self):
                    return self["unique_id"]

            ppv = P_PlantPV()
            sensor.set_source_values(ppv, [(0, 1000.0)])
            assert sensor.latest_raw_state == 1700.0

            # Test TotalLoadPower and GeneralLoadPower branches
            from sigenergy2mqtt.sensors.plant_read_only import GeneralLoadPower, TotalLoadPower

            tlp = MagicMock(spec=TotalLoadPower)
            tlp.unique_id = "tlp"
            sensor._sources[ConsumptionMethod.TOTAL.value] = PlantConsumedPower.Value()
            sensor.set_source_values(tlp, [(0, 2000.0)])
            assert sensor._sources[ConsumptionMethod.TOTAL.value].state == 2000.0

            glp = MagicMock(spec=GeneralLoadPower)
            glp.unique_id = "glp"
            sensor._sources[ConsumptionMethod.GENERAL.value] = PlantConsumedPower.Value()
            sensor.set_source_values(glp, [(0, 1500.0)])
            assert sensor._sources[ConsumptionMethod.GENERAL.value].state == 1500.0


class TestTotalPVPower:
    @pytest.mark.asyncio
    async def test_total_pv_power_aggregation_and_notify(self):
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

            s1 = MockPV("PV1", "sigenergy_pv1")
            sensor = TotalPVPower(0, s1)
            sensor.debug_logging = False

            with patch("sigenergy2mqtt.sensors.plant_derived.DerivedSensor.publish", new_callable=AsyncMock) as mock_pub:
                await sensor.notify(AsyncMock(), AsyncMock(), 600.0, "sigenergy_pv1", MagicMock())
                assert sensor.latest_raw_state == 600.0
                mock_pub.assert_called_once()

    def test_total_pv_power_set_source_values_and_fallback(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class MockPV(Sensor, PVPowerSensor):
                def __init__(self, name, object_id):
                    self["name"] = name
                    self.name = name
                    self.unique_id = self["unique_id"] = object_id
                    self._gain = 1.0
                    self["display_precision"] = 2

            s1 = MockPV("PV1", "sigenergy_pv1")
            sensor = TotalPVPower(0, s1)

            # Test direct set_source_values
            sensor.set_source_values(s1, [(0, 500.0)])
            assert sensor.latest_raw_state == 500.0

            # Test fallback logic
            sensor._sources["sigenergy_pv1"].type = TotalPVPower.SourceType.SMARTPORT
            sensor._sources["sigenergy_pv1"].enabled = False

            with patch.object(sensor, "fallback") as mock_fallback:
                sensor.set_source_values(s1, [(0, 600.0)])
                mock_fallback.assert_called_once_with("sigenergy_pv1")


class TestTotalLifetimePVEnergy:
    def test_total_lifetime_pv_energy_set_source_values(self):
        from sigenergy2mqtt.sensors.plant_read_only import PlantPVTotalGeneration, ThirdPartyLifetimePVEnergy

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TotalLifetimePVEnergy(0)

            gen = MagicMock(spec=PlantPVTotalGeneration)
            gen.unique_id = "gen"

            tp = MagicMock(spec=ThirdPartyLifetimePVEnergy)
            tp.unique_id = "tp"

            # Set first source
            assert sensor.set_source_values(gen, [(0, 1000.0)]) is False
            assert sensor.plant_lifetime_pv_energy == 1000.0

            # Set second source
            assert sensor.set_source_values(tp, [(0, 500.0)]) is True
            assert sensor.plant_3rd_party_lifetime_pv_energy == 500.0
            assert sensor.latest_raw_state == 1500.0
