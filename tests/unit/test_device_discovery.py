import json
import logging
from pathlib import Path

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device


class DummyMQTT:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return None


class FakeSensor:
    def __init__(self, unique_id, comp=None):
        self.unique_id = unique_id
        self._comp = comp or {}

    def get_discovery(self, mqtt_client):
        return self._comp

    def publish_attributes(self, mqtt_client, clean=False):
        return None


def test_publish_discovery_empty(tmp_path, monkeypatch):
    # Ensure no components -> publish availability and clear discovery
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()

    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.discovery_prefix = "homeassistant"

    with _swap_active_config(cfg):
        dev = Device("TestDevice", 0, "uid-123", "mf", "mdl", Protocol.N_A)
        dev.all_sensors = {}
        dev.publish_discovery(mqtt, clean=True)

        # Two publishes: availability cleared and discovery cleared
        assert len(mqtt.published) >= 2
        avail_topic = f"{active_config.home_assistant.discovery_prefix}/device/{dev.unique_id}/availability"
        # discovery topic publish will be with None payload when empty
        disc_topic = f"{active_config.home_assistant.discovery_prefix}/device/{dev.unique_id}/config"
        assert any(p[0] == avail_topic and p[1] is None for p in mqtt.published)
        assert any(p[0] == disc_topic and p[1] is None for p in mqtt.published)


def test_publish_discovery_populated_writes_file(tmp_path, monkeypatch):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()

    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.log_level = logging.DEBUG

    with _swap_active_config(cfg):
        dev = Device("TestDevice2", 0, "uid-456", "mf", "mdl", Protocol.N_A)

        # sensor returns a discovery component
        sensor = FakeSensor("s1", {"comp1": {"k": "v"}})
        dev.all_sensors = {sensor.unique_id: sensor}

        dev.publish_discovery(mqtt, clean=False)

        disc_topic = f"{active_config.home_assistant.discovery_prefix}/device/{dev.unique_id}/config"
        found = [p for p in mqtt.published if p[0] == disc_topic]
        assert found, "Discovery publish not called"
        topic, payload, qos, retain = found[0]
        assert qos == 2
        assert retain is True

        # verify file written
        fpath = Path(tmp_path, f"{dev.unique_id}.discovery.json")
        assert fpath.exists()
        data = json.loads(fpath.read_text())
        assert "cmps" in data
