import logging
import os
from unittest.mock import MagicMock, patch

from sigenergy2mqtt.common import PERCENTAGE, UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.config import ConsumptionSource, StatusField, VoltageSource, const
from sigenergy2mqtt.devices.smartport.enphase import EnphaseVoltage
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.pvoutput import get_gain, get_pvoutput_services
from sigenergy2mqtt.sensors.inverter_read_only import DailyChargeEnergy, DailyDischargeEnergy, PhaseVoltage, PVVoltageSensor
from sigenergy2mqtt.sensors.plant_derived import GridSensorDailyExportEnergy, GridSensorDailyImportEnergy, TotalDailyPVEnergy, TotalLifetimePVEnergy, TotalPVPower
from sigenergy2mqtt.sensors.plant_read_only import (
    ESSTotalChargedEnergy,
    ESSTotalDischargedEnergy,
    PlantBatterySoC,
    PlantPVPower,
    PlantRatedEnergyCapacity,
    PlantTotalImportedEnergy,
    TotalLoadConsumption,
    TotalLoadDailyConsumption,
)

# Disable auto-discovery for all tests in this file
os.environ[const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY] = "none"


def mock_sensor(cls, topic="test/topic", gain=100.0, unit=UnitOfEnergy.KILO_WATT_HOUR):
    sensor = MagicMock(spec=cls)
    sensor.__class__ = cls
    sensor.raw_state_topic = topic
    sensor.state_topic = topic
    sensor.publishable = True
    sensor.gain = gain
    sensor.unit = unit
    sensor.scan_interval = 60
    sensor.precision = 2
    sensor.device_class = "power"
    sensor.data_type = ModbusDataType.INT16
    sensor.__getitem__.side_effect = lambda key: "mock_id" if key == "object_id" else None
    return sensor


def test_get_pvoutput_services_full_coverage():
    # Setup mocks for all sensors
    sensors = [
        mock_sensor(DailyChargeEnergy),
        mock_sensor(DailyDischargeEnergy),
        mock_sensor(ESSTotalChargedEnergy),
        mock_sensor(ESSTotalDischargedEnergy),
        mock_sensor(GridSensorDailyExportEnergy),
        mock_sensor(GridSensorDailyImportEnergy),
        mock_sensor(PhaseVoltage),
        mock_sensor(PlantBatterySoC),
        mock_sensor(PlantPVPower),
        mock_sensor(PlantRatedEnergyCapacity),
        mock_sensor(PlantTotalImportedEnergy),
        mock_sensor(PVVoltageSensor),
        mock_sensor(EnphaseVoltage),
        mock_sensor(TotalDailyPVEnergy),
        mock_sensor(TotalLifetimePVEnergy),
        mock_sensor(TotalLoadConsumption),
        mock_sensor(TotalLoadDailyConsumption),
        mock_sensor(TotalPVPower),
    ]

    # Configure PhaseVoltage specifically
    sensors[6].phase = "A"

    mock_device = MagicMock()
    mock_device.get_all_sensors.return_value = {str(i): s for i, s in enumerate(sensors)}

    mock_thread_config = MagicMock()
    mock_thread_config.devices = [mock_device]

    from sigenergy2mqtt.config.config import active_config

    with (
        patch.object(active_config.pvoutput, "enabled", True),
        patch.object(active_config.pvoutput, "consumption", ConsumptionSource.NET_OF_BATTERY),
        patch.object(active_config.pvoutput, "voltage", VoltageSource.PHASE_A),
        patch.object(active_config.pvoutput, "log_level", logging.DEBUG),
        patch.object(active_config.pvoutput, "extended", {k: "" for k in StatusField if k.value.startswith("v") and k.value not in ("v1", "v2", "v3", "v4", "v5", "v6")} | {StatusField.V7: "TotalPVPower"}),
        patch.object(active_config.pvoutput, "temperature_topic", "temp/topic"),
    ):
        services = get_pvoutput_services([mock_thread_config])
        assert len(services) == 2


def test_get_pvoutput_services_additional_branches():
    # Test different consumption and voltage sources
    sensors = [
        mock_sensor(GridSensorDailyImportEnergy),
        mock_sensor(PlantTotalImportedEnergy),
        mock_sensor(PhaseVoltage),
        mock_sensor(PVVoltageSensor),
    ]
    sensors[2].phase = "B"

    mock_device = MagicMock()
    mock_device.get_all_sensors.return_value = {str(i): s for i, s in enumerate(sensors)}
    mock_thread_config = MagicMock()
    mock_thread_config.devices = [mock_device]

    from sigenergy2mqtt.config.config import active_config

    with (
        patch.object(active_config.pvoutput, "enabled", True),
        patch.object(active_config.pvoutput, "consumption", ConsumptionSource.IMPORTED),
        patch.object(active_config.pvoutput, "voltage", VoltageSource.PHASE_B),
        patch.object(active_config.pvoutput, "extended", {k: "" for k in StatusField if k.value.startswith("v") and k.value not in ("v1", "v2", "v3", "v4", "v5", "v6")}),
    ):
        services = get_pvoutput_services([mock_thread_config])
        assert len(services) == 2


def test_get_pvoutput_services_peak_power_branches():
    # Test plant_pv_power branch when total_pv_power is missing
    sensors = [
        mock_sensor(PlantPVPower),
    ]
    mock_device = MagicMock()
    mock_device.get_all_sensors.return_value = {"0": sensors[0]}
    mock_thread_config = MagicMock()
    mock_thread_config.devices = [mock_device]

    from sigenergy2mqtt.config.config import active_config

    with (
        patch.object(active_config.pvoutput, "enabled", True),
        patch.object(active_config.pvoutput, "extended", {k: "" for k in StatusField if k.value.startswith("v") and k.value not in ("v1", "v2", "v3", "v4", "v5", "v6")}),
    ):
        services = get_pvoutput_services([mock_thread_config])
        assert len(services) == 2


def test_get_pvoutput_services_voltage_sources():
    sources = [VoltageSource.L_N_AVG, VoltageSource.L_L_AVG, VoltageSource.PHASE_C, VoltageSource.PV]
    for source in sources:
        sensors = [mock_sensor(PhaseVoltage), mock_sensor(PVVoltageSensor)]
        sensors[0].phase = "C"
        mock_device = MagicMock()
        mock_device.get_all_sensors.return_value = {"0": sensors[0], "1": sensors[1]}
        mock_thread_config = MagicMock()
        mock_thread_config.devices = [mock_device]

        from sigenergy2mqtt.config.config import active_config

        with (
            patch.object(active_config.pvoutput, "enabled", True),
            patch.object(active_config.pvoutput, "voltage", source),
            patch.object(active_config.pvoutput, "extended", {k: "" for k in StatusField if k.value.startswith("v") and k.value not in ("v1", "v2", "v3", "v4", "v5", "v6")}),
        ):
            services = get_pvoutput_services([mock_thread_config])
            assert len(services) == 2


def test_get_pvoutput_services_donation_logging(caplog):
    # Test warning for non-numeric sensor in donation
    from sigenergy2mqtt.sensors.base import TypedSensorMixin

    class MockTypedSensor(TotalPVPower, TypedSensorMixin):
        pass

    sensor = mock_sensor(MockTypedSensor)
    sensor.data_type = ModbusDataType.STRING

    mock_device = MagicMock()
    mock_device.get_all_sensors.return_value = {"0": sensor}
    mock_thread_config = MagicMock()
    mock_thread_config.devices = [mock_device]

    from sigenergy2mqtt.config.config import active_config

    with (
        patch.object(active_config.pvoutput, "enabled", True),
        patch.object(active_config.pvoutput, "log_level", logging.WARNING),
        patch.object(active_config.pvoutput, "extended", {k: "" for k in StatusField if k.value.startswith("v") and k.value not in ("v1", "v2", "v3", "v4", "v5", "v6")} | {StatusField.V8: "MockTypedSensor"}),
    ):
        with caplog.at_level(logging.WARNING, logger="pvoutput"):
            get_pvoutput_services([mock_thread_config])
            assert "does not have a numeric data type" in caplog.text


def test_get_gain_additional():
    # Test negation and different units
    s1 = MagicMock()
    s1.gain = 100.0
    s1.unit = UnitOfEnergy.KILO_WATT_HOUR
    assert get_gain(s1, negate=True) == -10.0
    assert get_gain(s1, negate=False) == 10.0

    s2 = MagicMock()
    s2.gain = 2.0
    s2.unit = UnitOfPower.WATT
    assert get_gain(s2, negate=False) == 2.0
    assert get_gain(s2, negate=True) == -2.0

    s3 = MagicMock()
    s3.gain = None
    s3.unit = PERCENTAGE
    assert get_gain(s3, negate=False) == 1.0
    assert get_gain(s3, negate=True) == -1.0

    s4 = MagicMock()
    s4.gain = 50.0
    s4.unit = PERCENTAGE
    assert get_gain(s4, negate=True) == -50.0


def test_get_pvoutput_services_disabled():
    from sigenergy2mqtt.config.config import active_config

    with patch.object(active_config.pvoutput, "enabled", False):
        services = get_pvoutput_services([])
        assert services == []
