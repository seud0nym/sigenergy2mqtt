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
        from sigenergy2mqtt import i18n
        from sigenergy2mqtt.config import Config
        from sigenergy2mqtt.devices.device import DeviceRegistry
        from sigenergy2mqtt.modbus.client_factory import ModbusClientFactory
        from sigenergy2mqtt.modbus.lock_factory import ModbusLockFactory
    except SystemExit:
        # If it still correctly exits (validation failure?), capture it.
        pass
    except Exception as e:
        print(f"Failed to load sigenergy2mqtt components during conftest setup: {e}")


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
def mock_language_detection(request):
    """Global fixture to mock language detection, avoiding slow system calls.

    Use @pytest.mark.no_language_mock to disable this mock for specific tests.
    """
    if "no_language_mock" in [m.name for m in request.node.iter_markers()]:
        yield
    else:
        with patch("sigenergy2mqtt.i18n.get_default_language", return_value="en"):
            yield


# Baseline env vars required for Config to initialize properly
_BASELINE_ENV = {
    "SIGENERGY2MQTT_MODBUS_HOST": "127.0.0.1",
    "SIGENERGY2MQTT_MODBUS_PORT": "502",
    "SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID": "1",
}


@pytest.fixture(autouse=True)
def reset_config():
    """Global fixture to ensure Config is reset for every test.

    Saves and restores SIGENERGY2MQTT_* env vars to prevent cross-test pollution.
    Does NOT use monkeypatch because that conflicts with tests that also use
    monkeypatch to set/clear these same env vars.
    """
    # Save all SIGENERGY2MQTT_* env vars
    saved_env = {k: v for k, v in os.environ.items() if k.startswith("SIGENERGY2MQTT_")}

    # Ensure baseline env vars are set for Config.reload()
    for k, v in _BASELINE_ENV.items():
        os.environ[k] = v

    Config.reset()
    Config.reload()
    DeviceRegistry.clear()
    ModbusClientFactory.clear()
    ModbusLockFactory.clear()

    yield

    # Teardown: restore env vars to pre-test state
    # Remove any SIGENERGY2MQTT_* vars that tests may have added
    for k in list(os.environ.keys()):
        if k.startswith("SIGENERGY2MQTT_"):
            del os.environ[k]
    # Restore saved vars
    os.environ.update(saved_env)

    DeviceRegistry.clear()
    ModbusClientFactory.clear()
    ModbusLockFactory.clear()


@pytest.fixture(autouse=True)
def reset_i18n():
    """Global fixture to ensure i18n is reset for every test."""
    i18n.reset()
    i18n.load("en")
    yield
    i18n.reset()
