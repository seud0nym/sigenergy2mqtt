import logging
import os
import sys
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from ruamel.yaml import YAML

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("paho.mqtt")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_yaml = YAML(typ="safe", pure=True)
with open("test/.debug.yaml", "r") as f:
    config = _yaml.load(f)
    username = config.get("mqtt", {}).get("username")
    password = config.get("mqtt", {}).get("password")
    broker = config.get("mqtt", {}).get("broker", "localhost")
    port = config.get("mqtt", {}).get("port", 1883)

mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="modbus_test_client")
mqtt_client.enable_logger(logger)

mqtt_client.username_pw_set(username, password)
mqtt_client.connect(broker, port, 60)
mqtt_client.loop_start()

logger.info(mqtt_client.publish("sigenergy2mqtt/sigen_0_plant_remote_ems/set", payload="0", qos=1))
time.sleep(1)
logger.info(mqtt_client.publish("sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/set", payload="Command Charging (Consume power from the PV first)", qos=1))
time.sleep(1)
logger.info(mqtt_client.publish("sigenergy2mqtt/sigen_0_plant_remote_ems/set", payload="1", qos=1))
time.sleep(1)
logger.info(mqtt_client.publish("sigenergy2mqtt/sigen_0_plant_remote_ems_control_mode/set", payload="Command Charging (Consume power from the PV first)", qos=1))

mqtt_client.loop_stop()
mqtt_client.disconnect()
