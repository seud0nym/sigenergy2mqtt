import sys
from unittest.mock import MagicMock

import pytest

# Mock circular dependencies for all unit tests
# Many sensor modules import from common.types which causes issues in standalone tests
mock_types = MagicMock()


from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.i18n import _t


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
def mock_sensor_types():
    """Fixture that ensures sigenergy2mqtt.common.types is mocked.
    Since we already did it at module level, this is just for explicit documentation
    and to provide access to the mock if needed.
    """
    return mock_types
