import sys
from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.persistence import state_store

# Mock circular dependencies for all unit tests
# Many sensor modules import from common.types which causes issues in standalone tests
mock_types = MagicMock()


class MockHybridInverter:
    def __init__(self, *args, **kwargs):
        self.protocol_version = kwargs.get("protocol_version", Protocol.N_A)

    def __str__(self) -> str:
        return _t("HybridInverter.name", "Hybrid Inverter")


class MockPVInverter:
    def __init__(self, *args, **kwargs):
        self.protocol_version = kwargs.get("protocol_version", Protocol.N_A)

    def __str__(self) -> str:
        return _t("PVInverter.name", "PV Inverter")


class MockNonInverter:
    def __init__(self, *args, **kwargs):
        self.protocol_version = kwargs.get("protocol_version", Protocol.N_A)

    def __str__(self) -> str:
        return ""


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
mock_types.NonInverter = MockNonInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types


@pytest.fixture(autouse=True)
def mock_persistence_defaults(monkeypatch):
    """Ensure MQTT redundancy is disabled by default for all unit tests.

    This avoids multi-second timeouts in tests that accidentally trigger
    persistence initialization.
    """
    monkeypatch.setenv("SIGENERGY2MQTT_PERSISTENCE_MQTT_REDUNDANCY", "false")


@pytest.fixture(autouse=True)
def reset_state_store():
    """Ensure StateStore is shut down after each test to prevent side effects."""
    yield
    try:
        state_store.shutdown()
    except Exception:
        pass
