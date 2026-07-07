import logging
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.devices.base.device import Device, bind_cross_device_sensors
from sigenergy2mqtt.devices.base.registry import DeviceRegistry
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import CrossDeviceDerivedSensor, ReadableSensorMixin, Sensor


class MockSensor(ReadableSensorMixin, Sensor):
    def __init__(self, plant_index, device_address, name, unique_id, protocol_version=Protocol.V1_8):
        self.plant_index = plant_index
        self.device_address = device_address
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=unique_id,
            unit="W",
            device_class=None,
            state_class=None,
            icon=None,
            gain=1.0,
            precision=1,
            protocol_version=protocol_version,
            data_type=ModbusDataType.INT32,
            scan_interval=30
        )


class MockCrossSensor(CrossDeviceDerivedSensor):
    def update_from_source_sensor(self, sensor):
        return True

    def __init__(self, plant_index, device_address, name, unique_id, sources=None):
        self.plant_index = plant_index
        self.device_address = device_address
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=unique_id,
            unit="W",
            device_class=None,
            state_class=None,
            icon=None,
            gain=1.0,
            precision=1,
            data_type=ModbusDataType.INT32,
            scan_interval=30
        )
        if sources:
            self.declare_cross_device_sources(*sources)


@pytest.fixture(autouse=True)
def clear_registries():
    DeviceRegistry.clear()
    with patch.dict(Sensor._used_unique_ids, clear=True), \
         patch.dict(Sensor._used_object_ids, clear=True):
        yield


def test_cross_device_sensor_registration():
    """Test that CrossDeviceDerivedSensor can be added to a device without sources."""
    dev = Device(name="Test Device", plant_index=0, unique_id="sigen_test_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    
    # Create a cross-device sensor
    sensor = MockCrossSensor(0, 100, "Cross", "sigen_cross_uid")
    
    assert dev._add_sensor(sensor) is True
    assert "sigen_cross_uid" in dev.all_sensors


def test_bind_cross_device_sensors_success():
    """Test successful binding across two devices."""
    # Device 1 with a source sensor
    dev1 = Device(name="Dev1", plant_index=0, unique_id="sigen_dev1_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    source = MockSensor(0, 1, "Source", "sigen_source_uid")
    dev1._add_sensor(source)
    
    # Device 2 with a cross-device sensor
    dev2 = Device(name="Dev2", plant_index=0, unique_id="sigen_dev2_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    # Use a dummy source object just to record the unique_id we want
    dummy_source = MagicMock(spec=Sensor)
    dummy_source.unique_id = "sigen_source_uid"
    dummy_source.protocol_version = Protocol.V1_8
    
    cross = MockCrossSensor(0, 2, "Cross", "sigen_cross_uid", sources=[dummy_source])
    dev2._add_sensor(cross)
    
    # Before binding
    assert not cross.bound_source_sensors
    
    # Bind
    bind_cross_device_sensors(0)
    
    # After binding
    assert len(cross.bound_source_sensors) == 1
    assert cross.bound_source_sensors[0] == source
    assert cross in source.derived_sensors.values()


def test_bind_cross_device_sensors_protocol_mismatch():
    """Test that binding is skipped if source protocol > device protocol."""
    # Device 1 with a V2.8 source
    dev1 = Device(name="Dev1", plant_index=0, unique_id="sigen_dev1_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    source = MockSensor(0, 1, "Source", "sigen_source_uid", protocol_version=Protocol.V2_8)
    dev1._add_sensor(source)
    
    # Device 2 with V1.8 protocol
    dev2 = Device(name="Dev2", plant_index=0, unique_id="sigen_dev2_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    dev2.protocol_version = Protocol.V1_8
    
    dummy_source = MagicMock(spec=Sensor)
    dummy_source.unique_id = "sigen_source_uid"
    dummy_source.protocol_version = Protocol.V2_8
    
    cross = MockCrossSensor(0, 2, "Cross", "sigen_cross_uid", sources=[dummy_source])
    dev2._add_sensor(cross)
    
    # Bind
    bind_cross_device_sensors(0)
    
    # Should skip due to protocol
    assert not cross.bound_source_sensors


def test_bind_cross_device_sensors_missing_source(caplog):
    """Test warning when a declared cross-device source is missing."""
    dev = Device(name="Dev", plant_index=0, unique_id="sigen_dev_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    
    dummy_source = MagicMock(spec=Sensor)
    dummy_source.unique_id = "sigen_missing_uid"
    dummy_source.protocol_version = Protocol.V1_8
    
    cross = MockCrossSensor(0, 1, "Cross", "sigen_cross_uid", sources=[dummy_source])
    dev._add_sensor(cross)
    
    with caplog.at_level(logging.WARNING):
        bind_cross_device_sensors(0)
        assert "cannot bind cross-device source" in caplog.text
        assert "no cross-device sources were bound" in caplog.text


def test_declare_cross_device_sources_logs_when_empty(caplog):
    cross = MockCrossSensor(0, 1, "Cross Empty", "sigen_cross_empty_uid")

    with caplog.at_level(logging.ERROR):
        cross.declare_cross_device_sources(None)

    assert cross._pending_sources == []
    assert "no declared cross-device sources" in caplog.text


def test_finalise_binding_requires_parent_device():
    cross = MockCrossSensor(0, 1, "Cross Orphan", "sigen_cross_orphan_uid")

    with pytest.raises(RuntimeError, match="before sensor was added"):
        cross.finalise_binding(0)


def test_finalise_binding_logs_when_no_pending_sources(caplog):
    dev = Device(name="Dev", plant_index=0, unique_id="sigen_dev_no_pending_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    cross = MockCrossSensor(0, 1, "Cross No Pending", "sigen_cross_no_pending_uid")
    dev._add_sensor(cross)

    with caplog.at_level(logging.ERROR):
        assert cross.finalise_binding(0) is False

    assert "no pending cross-device sources to bind" in caplog.text


def test_finalise_binding_uses_explicit_sources_and_debug_logs(caplog):
    dev1 = Device(name="Dev Source", plant_index=0, unique_id="sigen_dev_explicit_src_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    source = MockSensor(0, 1, "Source Explicit", "sigen_source_explicit_uid")
    dev1._add_sensor(source)

    dev2 = Device(name="Dev Cross", plant_index=0, unique_id="sigen_dev_explicit_cross_uid", manufacturer="M", model="M", protocol_version=Protocol.V1_8)
    cross = MockCrossSensor(0, 2, "Cross Explicit", "sigen_cross_explicit_uid")
    cross.debug_logging = True
    dev2._add_sensor(cross)

    pending = MagicMock(spec=Sensor)
    pending.unique_id = "sigen_source_explicit_uid"
    pending.protocol_version = Protocol.V1_8

    with caplog.at_level(logging.DEBUG):
        assert cross.finalise_binding(0, pending, None) is True

    assert cross.bound_source_sensors == [source]
    assert cross.source_sensors == [source]
    assert cross._pending_sources == []
    assert "bound cross-device source" in caplog.text
