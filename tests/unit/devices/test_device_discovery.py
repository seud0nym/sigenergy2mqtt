import json
import logging
from pathlib import Path

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device


class DummyMQTT:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


class FakeSensor:
    def __init__(self, unique_id, comp=None):
        self.unique_id = unique_id
        self._comp = comp or {}
        self.publishable = True

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
        dev = Device("TestDevice", 0, "uid-123", "mf", "mdl", ProtocolVersion.N_A)
        dev.all_sensors = {}
        dev.publish_discovery(mqtt, clean=True)

        # Two publishes: availability cleared and discovery cleared
        assert len(mqtt.published) >= 2
        avail_topic = f"{active_config.home_assistant.discovery_prefix}/device/{dev.unique_id}/availability"
        # discovery topic publish will be with b"" payload when empty
        disc_topic = f"{active_config.home_assistant.discovery_prefix}/device/{dev.unique_id}/config"
        assert any(p[0] == avail_topic and p[1] == b"" for p in mqtt.published)
        assert any(p[0] == disc_topic and p[1] == b"" for p in mqtt.published)


def test_publish_discovery_populated_writes_file(tmp_path, monkeypatch):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()

    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.log_level = logging.DEBUG

    with _swap_active_config(cfg):
        dev = Device("TestDevice2", 0, "uid-456", "mf", "mdl", ProtocolVersion.N_A)

        # sensor returns a discovery component
        sensor = FakeSensor("s1", {"comp1": {"k": "v"}})
        dev.all_sensors = {sensor.unique_id: sensor}

        dev.publish_discovery(mqtt, clean=False)

        disc_topic = f"{active_config.home_assistant.discovery_prefix}/device/{dev.unique_id}/config"
        found = [p for p in mqtt.published if p[0] == disc_topic]
        assert found, "Discovery publish not called"
        _topic, _payload, qos, retain = found[0]
        assert qos == 2
        assert retain is True

        # verify file written
        fpath = Path(tmp_path, f"{dev.unique_id}.discovery.json")
        assert fpath.exists()
        data = json.loads(fpath.read_text())
        assert "cmps" in data


def test_publish_discovery_child_devices(tmp_path):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.child_devices = True

    with _swap_active_config(cfg):
        parent = Device("Parent", 0, "parent-id", "mf", "mdl", ProtocolVersion.N_A)
        child = Device("Child", 0, "child-id", "mf", "mdl", ProtocolVersion.N_A)
        parent_sensor = FakeSensor("parent-sensor", {"parent-component": {"p": "sensor", "uniq_id": "parent-sensor"}})
        child_sensor = FakeSensor(
            "child-sensor",
            {
                "child-component": {
                    "p": "sensor",
                    "uniq_id": "child-sensor",
                    "avty": [{"topic": "homeassistant/device/child-id/availability"}],
                }
            },
        )
        parent.all_sensors = {parent_sensor.unique_id: parent_sensor}
        child.all_sensors = {child_sensor.unique_id: child_sensor}
        parent._add_child_device(child)

        parent.publish_discovery(mqtt)

        parent_topic = f"{active_config.home_assistant.discovery_prefix}/device/{parent.unique_id}/config"
        child_topic = f"{active_config.home_assistant.discovery_prefix}/device/{child.unique_id}/config"
        parent_payload = next(payload for topic, payload, _qos, _retain in mqtt.published if topic == parent_topic)
        discovery = json.loads(parent_payload)

        assert set(discovery["cmps"]) == {"parent-component"}
        assert discovery["cdevs"] == [
            {
                "ids": "child-id",
                "name": "Child",
                "cmps": {
                    "child-component": {
                        "p": "sensor",
                        "uniq_id": "child-sensor",
                        "avty": [{"topic": "homeassistant/device/child-id/availability"}],
                    }
                },
            }
        ]
        assert any(topic == child_topic and payload == b"" and retain for topic, payload, _qos, retain in mqtt.published)
        clear_index = next(index for index, item in enumerate(mqtt.published) if item[0] == child_topic and item[1] == b"")
        parent_index = next(index for index, item in enumerate(mqtt.published) if item[0] == parent_topic and item[1] != b"")
        assert clear_index < parent_index

        publish_count = len(mqtt.published)
        child.publish_discovery(mqtt)
        assert len([item for item in mqtt.published[publish_count:] if item[0] == parent_topic]) == 1
        assert not any(item[0] == child_topic and item[1] != b"" for item in mqtt.published[publish_count:])


def test_publish_discovery_legacy_child_devices_remains_default(tmp_path):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    with _swap_active_config(cfg):
        parent = Device("Legacy Parent", 0, "legacy-parent", "mf", "mdl", ProtocolVersion.N_A)
        child = Device("Legacy Child", 0, "legacy-child", "mf", "mdl", ProtocolVersion.N_A)
        parent.all_sensors = {"parent": FakeSensor("parent", {"parent-component": {"p": "sensor"}})}
        child.all_sensors = {"child": FakeSensor("child", {"child-component": {"p": "sensor"}})}
        parent._add_child_device(child)

        parent.publish_discovery(mqtt)

        parent_topic = f"{active_config.home_assistant.discovery_prefix}/device/{parent.unique_id}/config"
        child_topic = f"{active_config.home_assistant.discovery_prefix}/device/{child.unique_id}/config"
        parent_payload = json.loads(next(payload for topic, payload, _qos, _retain in mqtt.published if topic == parent_topic))
        child_payload = json.loads(next(payload for topic, payload, _qos, _retain in mqtt.published if topic == child_topic and payload))

        assert "cdevs" not in parent_payload
        assert child_payload["dev"]["via_device"] == parent.unique_id
