import pytest

from sigenergy2mqtt.config.auto_discovery_settings import AutoDiscoverySettings


def test_validate_networks_empty():
    settings = AutoDiscoverySettings(modbus_auto_discovery_networks=None)
    assert settings.modbus_auto_discovery_networks == []

    settings = AutoDiscoverySettings(modbus_auto_discovery_networks=[])
    assert settings.modbus_auto_discovery_networks == []

    settings = AutoDiscoverySettings(modbus_auto_discovery_networks="")
    assert settings.modbus_auto_discovery_networks == []

def test_validate_networks_valid_string():
    settings = AutoDiscoverySettings(modbus_auto_discovery_networks="192.168.1.0/24, 10.0.0.1/32")
    assert settings.modbus_auto_discovery_networks == ["192.168.1.0/24", "10.0.0.1/32"]

def test_validate_networks_valid_list():
    settings = AutoDiscoverySettings(modbus_auto_discovery_networks=["192.168.1.0/24", "10.0.0.1"])
    assert settings.modbus_auto_discovery_networks == ["192.168.1.0/24", "10.0.0.1/32"]

def test_validate_networks_invalid():
    with pytest.raises(ValueError, match="Invalid IPv4 CIDR network"):
        AutoDiscoverySettings(modbus_auto_discovery_networks="invalid_ip")

    with pytest.raises(ValueError, match="Invalid IPv4 CIDR network"):
        AutoDiscoverySettings(modbus_auto_discovery_networks=["invalid_ip"])
