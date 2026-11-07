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


def _parent_and_child(prefix="homeassistant"):
    parent = Device("Parent", 0, "parent-id", "mf", "mdl", ProtocolVersion.N_A)
    child = Device("Child", 0, "child-id", "mf", "mdl", ProtocolVersion.N_A)
    parent_sensor = FakeSensor("parent-sensor", {"parent-component": {"p": "sensor", "uniq_id": "parent-sensor"}})
    child_component = {
        "child-component": {
            "p": "sensor",
            "uniq_id": "child-sensor",
            "avty": [{"topic": f"{prefix}/device/child-id/availability"}],
        }
    }
    parent.all_sensors = {parent_sensor.unique_id: parent_sensor}
    child.all_sensors = {"child-sensor": FakeSensor("child-sensor", child_component)}
    parent._add_child_device(child)
    return parent, child, child_component


def test_publish_discovery_child_devices_keeps_child_topic_and_component_ids(tmp_path):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.child_devices = True

    with _swap_active_config(cfg):
        parent, child, child_component = _parent_and_child(active_config.home_assistant.discovery_prefix)

        parent.publish_discovery(mqtt)

        prefix = active_config.home_assistant.discovery_prefix
        parent_topic = f"{prefix}/device/{parent.unique_id}/config"
        child_topic = f"{prefix}/device/{child.unique_id}/config"

        # Nothing is cleared: a cleared topic would remove the entities in HA
        assert not any(payload == b"" for _topic, payload, _qos, _retain in mqtt.published)

        parent_payload = json.loads(next(payload for topic, payload, _qos, _retain in mqtt.published if topic == parent_topic))
        assert set(parent_payload["cmps"]) == {"parent-component"}
        assert "cdevs" not in parent_payload  # the child is not listed twice

        # The child keeps its own topic (same discovery hash in HA), with the parent as root device
        child_payload = json.loads(next(payload for topic, payload, _qos, retain in mqtt.published if topic == child_topic and retain))
        assert "cmps" not in child_payload
        assert child_payload["dev"] == json.loads(json.dumps(parent))
        assert child_payload["dev"]["identifiers"] == ["parent-id"]
        assert child_payload["cdevs"] == [{"ids": ["child-id"], "name": "Child", "cmps": child_component}]

        # Publishing the child alone republishes only its own topic
        count = len(mqtt.published)
        child.publish_discovery(mqtt)
        assert [item[0] for item in mqtt.published[count:] if item[0].endswith("/config")] == [child_topic]


def test_publish_discovery_ineligible_child_stays_via_device(tmp_path):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    class PhysicalProduct(Device):
        ha_child_device_eligible = False

    mqtt = DummyMQTT()
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.child_devices = True

    with _swap_active_config(cfg):
        parent = Device("Parent", 0, "parent-id", "mf", "mdl", ProtocolVersion.N_A)
        product = PhysicalProduct("Product", 0, "product-id", "mf", "mdl", ProtocolVersion.N_A)
        parent.all_sensors = {"p": FakeSensor("p", {"p": {"p": "sensor"}})}
        product.all_sensors = {"c": FakeSensor("c", {"c": {"p": "sensor"}})}
        parent._add_child_device(product)

        parent.publish_discovery(mqtt)

        topic = f"{active_config.home_assistant.discovery_prefix}/device/product-id/config"
        payload = json.loads(next(p for t, p, _q, _r in mqtt.published if t == topic))
        assert "cdevs" not in payload
        assert payload["dev"]["identifiers"] == ["product-id"]
        assert payload["dev"]["via_device"] == "parent-id"


def test_publish_discovery_clean_clears_child_topics(tmp_path):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.child_devices = True

    with _swap_active_config(cfg):
        parent, _child, _ = _parent_and_child()
        parent.publish_discovery(mqtt, clean=True)
        prefix = active_config.home_assistant.discovery_prefix
        cleared = {t for t, p, _q, r in mqtt.published if p == b"" and r and t.endswith("/config")}
        assert cleared == {f"{prefix}/device/parent-id/config", f"{prefix}/device/child-id/config"}


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


def test_publish_discovery_child_device_name_drops_parent_name(tmp_path):
    from sigenergy2mqtt.config import _swap_active_config, active_config

    mqtt = DummyMQTT()
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.child_devices = True

    with _swap_active_config(cfg):
        parent = Device("SigenStor EC 12.0 TP CMU123", 0, "inverter-id", "mf", "mdl", ProtocolVersion.N_A, translate=False)
        child = Device("SigenStor EC 12.0 TP CMU123 PV String 1", 0, "pv1-id", "mf", "mdl", ProtocolVersion.N_A, translate=False)
        parent.all_sensors = {"p": FakeSensor("p", {"p": {"p": "sensor"}})}
        child.all_sensors = {"c": FakeSensor("c", {"c": {"p": "sensor"}})}
        parent._add_child_device(child)

        parent.publish_discovery(mqtt)

        topic = f"{active_config.home_assistant.discovery_prefix}/device/pv1-id/config"
        payload = json.loads(next(p for t, p, _q, _r in mqtt.published if t == topic))
        assert payload["cdevs"][0]["name"] == "PV String 1"
        assert payload["dev"]["name"] == "SigenStor EC 12.0 TP CMU123"
        assert child.name == "SigenStor EC 12.0 TP CMU123 PV String 1"  # unchanged for logs and legacy payloads
