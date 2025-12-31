import sys
import os
from unittest.mock import patch

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
