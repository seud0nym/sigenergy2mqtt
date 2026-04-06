import sys
from unittest.mock import MagicMock

import pytest

# Mock circular dependencies for all unit tests
# Many sensor modules import from common.types which causes issues in standalone tests
mock_types = MagicMock()


from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.persistence import state_store


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


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
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
    """Ensure StateStore is clean before each test."""
    import traceback

    traceback.print_stack()
    state_store.shutdown()
    yield
    import traceback

    traceback.print_stack()
    state_store.shutdown()
