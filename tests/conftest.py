import os
import sys
from unittest.mock import patch

import pytest

# Ensure the package is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Ensure the test helpers are in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "utils")))

# Set environment variables to satisfy Config validation
os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
os.environ["SIGENERGY2MQTT_MODBUS_PORT"] = "502"
os.environ["SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID"] = "1"

# Prevent argparse from parsing pytest arguments by mocking sys.argv during import
with patch.object(sys, "argv", ["sigenergy2mqtt"]):
    try:
        import sigenergy2mqtt.config  # noqa: F401
    except SystemExit:
        # If it still correctly exits (validation failure?), capture it.
        pass
    except Exception as e:
        print(f"Failed to load sigenergy2mqtt.config during conftest setup: {e}")


@pytest.fixture(autouse=True)
def mock_persistent_state_path(request, tmp_path, reset_config):
    """Global fixture to ensure persistent_state_path is always a temp dir.

    Use @pytest.mark.no_persistent_state_mock to disable this mock.
    """
    if "no_persistent_state_mock" in [m.name for m in request.node.iter_markers()]:
        yield tmp_path
    else:
        with patch("sigenergy2mqtt.config.Config.persistent_state_path", tmp_path):
            yield tmp_path


@pytest.fixture(autouse=True)
def mock_locale_detection(request):
    """Global fixture to mock locale detection, avoiding slow system calls.

    Use @pytest.mark.no_locale_mock to disable this mock for specific tests.
    """
    if "no_locale_mock" in [m.name for m in request.node.iter_markers()]:
        yield
    else:
        with patch("sigenergy2mqtt.i18n.get_default_locale", return_value="en"):
            yield


@pytest.fixture(autouse=True)
def reset_config():
    """Global fixture to ensure Config is reset for every test."""
    from sigenergy2mqtt.config import Config

    Config.reset()
    Config.reload()
    yield
    Config.reset()
    Config.reload()


@pytest.fixture(autouse=True)
def reset_i18n():
    """Global fixture to ensure i18n is reset for every test."""
    from sigenergy2mqtt import i18n

    i18n.reset()
    i18n.load("en")
    yield
    i18n.reset()
