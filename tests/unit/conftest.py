import sys
from unittest.mock import MagicMock

import pytest

# Mock circular dependencies for all unit tests
# Many sensor modules import from common.types which causes issues in standalone tests
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


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
