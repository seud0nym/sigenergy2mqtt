import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config, _swap_active_config, active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.devices.base import child_devices as cd
from sigenergy2mqtt.persistence import Category


class FakeSensor:
    def __init__(self, unique_id):
        self.unique_id = unique_id
        self.publishable = True

    def get_discovery(self, mqtt_client):
        return {self.unique_id: {"p": "sensor", "uniq_id": self.unique_id}}

    def publish_attributes(self, mqtt_client, clean=False):
        return None


class PhysicalProduct(Device):
    ha_child_device_eligible = False


def _device(name, uid, cls=Device):
    device = cls(name, 0, uid, "mf", "mdl", ProtocolVersion.N_A)
    device.all_sensors = {f"{uid}-s": FakeSensor(f"{uid}-s")}
    return device


@pytest.fixture
def child_cfg(tmp_path):
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.enabled = True
    cfg.home_assistant.child_devices = True
    with _swap_active_config(cfg):
        yield cfg


@pytest.fixture
def store(monkeypatch):
    from sigenergy2mqtt.persistence import state_store

    saved: dict[str, str] = {}
    stored: dict[str, str | None] = {"value": None}

    async def load(category, key, **_):
        assert (category, key) == (Category.CONFIG, cd.MIGRATION_STATE_KEY)
        return stored["value"]

    async def save(category, key, value, **_):
        saved[key] = value

    monkeypatch.setattr(state_store, "load", load)
    monkeypatch.setattr(state_store, "save", save)
    monkeypatch.setattr(state_store, "save_sync", MagicMock(side_effect=lambda c, k, v: saved.__setitem__(k, v)))
    monkeypatch.setattr(cd, "fetch_ha_version", AsyncMock(return_value=None))
    return stored, saved


@pytest.mark.parametrize(
    ("version", "expected"),
    [("2026.11.0", (2026, 11)), ("2026.12.0b3", (2026, 12)), ("2026.11.0.dev20261101", (2026, 11)), ("garbage", None), ("", None)],
)
def test_parse_ha_version(version, expected):
    assert cd.parse_ha_version(version) == expected


def test_validate_hierarchy_accepts_single_level(child_cfg):
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("A", "a"))
    parent._add_child_device(_device("B", "b"))
    assert cd.validate_hierarchy([parent, *parent.children]) == []


def test_validate_hierarchy_rejects_nesting(child_cfg):
    root = _device("Root", "root")
    middle = _device("Middle", "middle")
    middle._add_child_device(_device("Leaf", "leaf"))
    root._add_child_device(middle)
    problems = cd.validate_hierarchy([root, middle, *middle.children])
    assert any("has child devices of its own" in p for p in problems)
    assert any("linked with via_device to" in p for p in problems)  # the leaf points at the middle child


def test_validate_hierarchy_allows_nesting_below_ineligible_child(child_cfg):
    # A physical product linked with via_device may have child devices of its own
    root = _device("Root", "root")
    product = _device("Product", "product", PhysicalProduct)
    product._add_child_device(_device("Part", "part"))
    root._add_child_device(product)
    assert cd.validate_hierarchy([root, product, *product.children]) == []


def test_validate_hierarchy_rejects_shared_identifiers(child_cfg):
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Same as parent", "parent-twin"))
    parent.children[0]["identifiers"] = ["parent-twin"]
    parent["identifiers"] = ["parent", "parent-twin"]
    parent._add_child_device(_device("Dup 1", "dup"))
    parent._add_child_device(_device("Dup 2", "dup"))
    problems = cd.validate_hierarchy([parent])
    assert any("same identifier as its parent" in p for p in problems)
    assert any("share the identifier dup" in p for p in problems)


@pytest.mark.asyncio
async def test_prepare_first_run_records_pending_reload(child_cfg, store, caplog):
    _, saved = store
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))

    with caplog.at_level(logging.WARNING):
        assert await cd.child_device_migration.prepare([parent, *parent.children]) is True

    assert saved == {cd.MIGRATION_STATE_KEY: cd.STAGE_PENDING_RELOAD}
    assert cd.child_device_migration.stage == cd.STAGE_PENDING_RELOAD
    assert "Reload the MQTT integration" in caplog.text
    assert active_config.home_assistant.child_devices is True


@pytest.mark.asyncio
async def test_prepare_refuses_old_home_assistant_without_changes(child_cfg, store, monkeypatch, caplog):
    _, saved = store
    monkeypatch.setattr(cd, "fetch_ha_version", AsyncMock(return_value="2026.10.4"))
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))

    with caplog.at_level(logging.ERROR):
        assert await cd.child_device_migration.prepare([parent, *parent.children]) is False

    assert active_config.home_assistant.child_devices is False
    assert saved == {}
    assert "2026.10.4 does not support MQTT child devices" in caplog.text
    assert cd.publishes_as_ha_child(parent.children[0]) is False


@pytest.mark.asyncio
async def test_prepare_accepts_supported_home_assistant(child_cfg, store, monkeypatch):
    monkeypatch.setattr(cd, "fetch_ha_version", AsyncMock(return_value="2026.11.1"))
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))
    assert await cd.child_device_migration.prepare([parent, *parent.children]) is True


@pytest.mark.asyncio
async def test_prepare_refuses_invalid_hierarchy_before_publishing(child_cfg, store):
    _, saved = store
    root = _device("Root", "root")
    middle = _device("Middle", "middle")
    middle._add_child_device(_device("Leaf", "leaf"))
    root._add_child_device(middle)

    assert await cd.child_device_migration.prepare([root, middle, *middle.children]) is False
    assert active_config.home_assistant.child_devices is False
    assert saved == {}
    cd.fetch_ha_version.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_after_conversion_keeps_stage_quietly(child_cfg, store, caplog):
    stored, saved = store
    stored["value"] = cd.STAGE_CHILD_DEVICES
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))

    with caplog.at_level(logging.WARNING):
        assert await cd.child_device_migration.prepare([parent, *parent.children]) is True

    assert saved == {}
    assert "Reload the MQTT integration" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("previous", [cd.STAGE_PENDING_RELOAD, cd.STAGE_CHILD_DEVICES])
async def test_prepare_disabled_after_migration_warns_about_rollback(child_cfg, store, caplog, previous):
    stored, saved = store
    stored["value"] = previous
    child_cfg.home_assistant.child_devices = False

    with caplog.at_level(logging.WARNING):
        assert await cd.child_device_migration.prepare([]) is False

    assert "can't convert a child device back" in caplog.text
    assert saved == {cd.MIGRATION_STATE_KEY: cd.STAGE_LEGACY}


@pytest.mark.asyncio
async def test_prepare_disabled_on_legacy_install_is_silent(child_cfg, store, caplog):
    _, saved = store
    child_cfg.home_assistant.child_devices = False
    with caplog.at_level(logging.WARNING):
        assert await cd.child_device_migration.prepare([]) is False
    assert saved == {}
    assert caplog.text == ""


@pytest.mark.asyncio
async def test_note_ha_online_ignores_immediate_birth_then_records_reload(child_cfg, store, monkeypatch):
    _, saved = store
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))
    clock = {"now": 1000.0}
    monkeypatch.setattr(cd.time, "monotonic", lambda: clock["now"])
    await cd.child_device_migration.prepare([parent, *parent.children])
    saved.clear()

    clock["now"] += 1  # e.g. a retained birth message delivered on subscribe
    await cd.child_device_migration.note_ha_online()
    assert cd.child_device_migration.stage == cd.STAGE_PENDING_RELOAD

    clock["now"] += 120
    await cd.child_device_migration.note_ha_online()
    assert cd.child_device_migration.stage == cd.STAGE_CHILD_DEVICES
    assert saved == {cd.MIGRATION_STATE_KEY: cd.STAGE_CHILD_DEVICES}

    saved.clear()
    await cd.child_device_migration.note_ha_online()
    assert saved == {}


def test_fetch_ha_version_without_supervisor(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    assert cd._fetch_ha_version_sync() is None


def test_fetch_ha_version_via_supervisor(monkeypatch):
    import requests

    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")
    monkeypatch.setenv("SUPERVISOR_URL", "http://supervisor/")
    response = MagicMock(status_code=200)
    response.json.return_value = {"version": "2026.11.0"}
    get = MagicMock(return_value=response)
    monkeypatch.setattr(requests, "get", get)

    assert cd._fetch_ha_version_sync() == "2026.11.0"
    assert get.call_args.args[0] == "http://supervisor/core/api/config"
    assert get.call_args.kwargs["headers"] == {"Authorization": "Bearer token"}


def test_fetch_ha_version_supervisor_error(monkeypatch):
    import requests

    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")
    monkeypatch.setattr(requests, "get", MagicMock(side_effect=requests.ConnectionError("down")))
    with pytest.raises(cd.HaVersionUnavailable, match="down"):
        cd._fetch_ha_version_sync()


@pytest.mark.parametrize(
    ("status", "body", "match"),
    [(502, {}, "status_code=502"), (200, {"message": "starting"}, "no version"), (200, ValueError("not json"), "invalid response")],
)
def test_fetch_ha_version_supervisor_bad_response(monkeypatch, status, body, match):
    import requests

    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")
    response = MagicMock(status_code=status)
    if isinstance(body, Exception):
        response.json.side_effect = body
    else:
        response.json.return_value = body
    monkeypatch.setattr(requests, "get", MagicMock(return_value=response))
    with pytest.raises(cd.HaVersionUnavailable, match=match):
        cd._fetch_ha_version_sync()


@pytest.mark.asyncio
async def test_prepare_refuses_when_supervisor_version_check_fails(child_cfg, store, monkeypatch, caplog):
    _, saved = store
    monkeypatch.setattr(cd, "fetch_ha_version", AsyncMock(side_effect=cd.HaVersionUnavailable("status_code=502")))
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))

    with caplog.at_level(logging.ERROR):
        assert await cd.child_device_migration.prepare([parent, *parent.children]) is False

    assert active_config.home_assistant.child_devices is False
    assert cd.publishes_as_ha_child(parent.children[0]) is False
    assert saved == {}
    assert "version could not be read" in caplog.text and "status_code=502" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("previous", [cd.STAGE_PENDING_RELOAD, cd.STAGE_CHILD_DEVICES])
async def test_prepare_keeps_published_child_devices_when_supervisor_version_check_fails(child_cfg, store, monkeypatch, caplog, previous):
    stored, _ = store
    stored["value"] = previous
    monkeypatch.setattr(cd, "fetch_ha_version", AsyncMock(side_effect=cd.HaVersionUnavailable("timed out")))
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))

    with caplog.at_level(logging.WARNING):
        assert await cd.child_device_migration.prepare([parent, *parent.children]) is True

    assert active_config.home_assistant.child_devices is True
    assert "keeping the child-device discovery already published" in caplog.text


@pytest.mark.asyncio
async def test_prepare_standalone_unchecked_opt_in(child_cfg, store, caplog):
    # fetch_ha_version returns None (no SUPERVISOR_TOKEN): the explicit opt-in is accepted
    parent = _device("Parent", "parent")
    parent._add_child_device(_device("Child", "child"))
    with caplog.at_level(logging.INFO):
        assert await cd.child_device_migration.prepare([parent, *parent.children]) is True
    assert "can't be checked outside the add-on" in caplog.text


def test_validate_hierarchy_rejects_via_device_to_child_device(child_cfg):
    # e.g. a charger linked to an inverter's ESS: HA can't resolve via_device to a child
    inverter = _device("Inverter", "inverter")
    ess = _device("ESS", "ess")
    inverter._add_child_device(ess)
    charger = _device("Charger", "charger")
    charger.via_device = ess.unique_id
    problems = cd.validate_hierarchy([inverter, ess, charger])
    assert len(problems) == 1 and "linked with via_device to" in problems[0]


def test_validate_hierarchy_allows_via_device_to_main_and_ineligible_devices(child_cfg):
    plant = _device("Plant", "plant")
    inverter = _device("Inverter", "inverter")
    inverter.via_device = plant.unique_id  # as the device factories do
    inverter._add_child_device(_device("ESS", "ess"))
    product = _device("Gateway", "gateway", PhysicalProduct)
    plant._add_child_device(product)
    accessory = _device("Accessory", "accessory")
    accessory.via_device = product.unique_id
    assert cd.validate_hierarchy([plant, inverter, *inverter.children, product, accessory]) == []


def test_validate_hierarchy_ignores_via_device_targets_when_disabled(child_cfg):
    child_cfg.home_assistant.child_devices = False
    inverter = _device("Inverter", "inverter")
    ess = _device("ESS", "ess")
    inverter._add_child_device(ess)
    charger = _device("Charger", "charger")
    charger.via_device = ess.unique_id
    assert cd.validate_hierarchy([inverter, ess, charger]) == []
