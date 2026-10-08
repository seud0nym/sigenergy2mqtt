"""Tests for modbus_sensors utility and DummyCloudControlPort."""

import pytest

from sigenergy2mqtt.cloud.models import InstantControlMode, InstantOverrideCommand
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.cloud.device_info import DeviceInfoSensor
from sigenergy2mqtt.sensors.cloud.read_only import (
    GatewayCommunicationStatus,
    GatewayGridVoltage,
)
from sigenergy2mqtt.sensors.cloud.read_write import (
    BatteryChargePowerLimit,
    GridExportLimit,
    InstantControlDuration,
    InstantControlSwitch,
    OperationalMode,
)
from sigenergy2mqtt.sensors.cloud.read_write import (
    InstantControlMode as InstantControlModeSensor,
)
from sigenergy2mqtt.sensors.settings import CloudLogLevel
from tests.utils.modbus_sensors import DummyCloudControlPort, get_sensor_instances
from tests.utils.modbus_test_server import CloudApiTestServer


async def test_dummy_cloud_control_port_methods_and_properties() -> None:
    server = CloudApiTestServer(None, None)
    port = DummyCloudControlPort(server)

    assert port.station_id == str(server.station_home_data["stationId"])
    assert port.model == "Sigenergy Cloud"
    assert port.capabilities.min_duration.total_seconds() == 60
    assert port.capabilities.max_duration.total_seconds() == 1440 * 60

    await port.connect()
    await port.close()
    assert await port.device_list() == []

    gateway = await port.gateway_info()
    assert gateway == server.gateway_info

    dyn3 = await port.device_dynamic_info(3, "INV")
    assert dyn3 == server.device_dynamic_info[3]
    dyn99 = await port.device_dynamic_info(99, "UNKNOWN")
    assert dyn99 == {}

    stat4 = await port.device_static_info(4, "BAT")
    assert stat4 == server.device_static_info[4]
    stat99 = await port.device_static_info(99, "UNKNOWN")
    assert stat99 == {}

    await port.set_instant_override(InstantOverrideCommand(InstantControlMode.CHARGE, port.capabilities.min_duration))
    await port.clear_instant_override()

    status = await port.instant_control_status()
    assert status.enabled == server.instant_control["enable"]

    modes = await port.available_operational_modes()
    assert modes == server.available_modes_data

    current_mode, current_profile = await port.get_operational_mode()
    assert current_mode == server.operational_mode
    assert current_profile == server.profile_id

    set_mode_resp = await port.set_operational_mode(1, 42)
    assert set_mode_resp == {"code": 0}
    assert server.operational_mode == 1
    assert server.profile_id == 42

    export_limit = await port.grid_export_limit()
    assert export_limit == server.grid_export_limit
    assert await port.set_grid_export_limit(5.0) == {"code": 0}

    import_limit = await port.grid_import_limit()
    assert import_limit == server.grid_import_limit
    assert await port.set_grid_import_limit(5.0) == {"code": 0}

    conn_limit = await port.grid_connection_limit()
    assert conn_limit == server.grid_connection_limit
    assert await port.set_grid_connection_limit(20.0) == {"code": 0}

    bat_limit = await port.battery_power_limit()
    assert bat_limit == server.battery_power_limit
    assert await port.set_battery_power_limit(max_charge_kw=3.0, max_discharge_kw=3.0) == {"code": 0}

    solar_limit = await port.solar_power_limit()
    assert solar_limit == server.solar_power_limit
    assert await port.set_solar_power_limit(4.0) == {"code": 0}

    bat_export = await port.battery_export_limitation()
    assert bat_export == server.battery_export_limitation
    assert await port.set_battery_export_limitation(enabled=True) == {"code": 0}


async def test_get_sensor_instances_includes_cloud_control_and_child_sensors(caplog: pytest.LogCaptureFixture) -> None:
    with _swap_active_config(Config()), caplog.at_level("WARNING"):
        sensors = await get_sensor_instances(concrete_sensor_check=True)

    sensor_classes = {type(s) for s in sensors.values()}

    # Assert CloudControl and child sensors are included
    assert InstantControlSwitch in sensor_classes
    assert InstantControlModeSensor in sensor_classes
    assert InstantControlDuration in sensor_classes
    assert OperationalMode in sensor_classes
    assert GridExportLimit in sensor_classes
    assert BatteryChargePowerLimit in sensor_classes
    assert GatewayCommunicationStatus in sensor_classes
    assert GatewayGridVoltage in sensor_classes
    assert DeviceInfoSensor in sensor_classes
    assert CloudLogLevel in sensor_classes

    # Assert no warnings about unused classes were logged
    unused_warnings = [record.message for record in caplog.records if "has not been used" in record.message]
    assert unused_warnings == []
