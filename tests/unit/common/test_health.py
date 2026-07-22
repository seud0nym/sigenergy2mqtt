"""Unit tests for ServiceHealthRegistry."""

from sigenergy2mqtt.common import ServiceHealthRegistry, service_health_registry


def test_service_health_registry_basic_operations():
    registry = ServiceHealthRegistry()

    # Default value for unrecorded service
    assert registry.get_health("pvoutput") is True
    assert registry.get_health("pvoutput", default=False) is False

    # Setting health status
    registry.set_health("pvoutput", False)
    assert registry.get_health("pvoutput") is False

    registry.set_health("pvoutput", True)
    assert registry.get_health("pvoutput") is True

    # Snapshot
    registry.set_health("influxdb", False)
    snap = registry.snapshot()
    assert snap == {"pvoutput": True, "influxdb": False}

    # Clear
    registry.clear()
    assert registry.snapshot() == {}
    assert registry.get_health("pvoutput") is True


def test_global_service_health_registry_instance():
    assert isinstance(service_health_registry, ServiceHealthRegistry)
