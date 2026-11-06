"""Home Assistant MQTT child-device support and the migration from ``via_device``.

Migration design (see the "Child Devices" option in the configuration README):

* Every device keeps publishing to its own discovery topic with unchanged
  component IDs, so the Home Assistant discovery hash of every entity stays the
  same. A child only changes the *shape* of its payload: the root ``dev`` becomes
  the parent's device info and its components move into a single ``cdevs`` entry.
  Nothing is cleared, so no entity is removed and re-added.
* Home Assistant converts an existing device to a child device in place (keeping
  its device ID, area, user-set name and labels) when the child identifiers match.
  It refuses while the MQTT config entry still has the device registered as a
  regular device in the current setup session, so the conversion only happens
  once the MQTT integration is reloaded or Home Assistant restarts. Until then the
  update is cancelled with a warning and the entities keep working unchanged.
* MQTT ``cdevs`` support arrived in Home Assistant 2026.11.0. Older releases reject
  the whole payload as invalid. That is harmless while running, but after a
  restart those entities would not be discovered, so the feature is refused when
  the Supervisor API reports an older release.
* A child device can't be converted back. Rolling back requires deleting the child
  devices in Home Assistant and reloading MQTT, which restores them as regular
  devices with the same device and entity IDs.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING

from sigenergy2mqtt.config import active_config

if TYPE_CHECKING:
    from .device import Device

logger = logging.getLogger(__name__)

MIN_HA_VERSION: tuple[int, int] = (2026, 11)
"""First Home Assistant release whose MQTT integration supports ``cdevs``."""

MIGRATION_STATE_KEY = "ha-child-devices-migration"

STAGE_LEGACY = "legacy"
"""Discovery uses separate devices linked with ``via_device``."""
STAGE_PENDING_RELOAD = "pending-reload"
"""Child-device payloads have been published; Home Assistant has not yet reloaded MQTT."""
STAGE_CHILD_DEVICES = "child-devices"
"""Home Assistant has (re)loaded MQTT since the child-device payloads were published."""
STAGES = {STAGE_LEGACY, STAGE_PENDING_RELOAD, STAGE_CHILD_DEVICES}

# A retained birth message is delivered as soon as it is subscribed to, which can
# happen right after the first child-device publish. Only a birth message received
# this long after publishing counts as Home Assistant having reloaded MQTT.
_RELOAD_GRACE_SECONDS = 30.0

_RELOAD_ADVICE = (
    "Reload the MQTT integration in Home Assistant (Settings > Devices & services > MQTT > ⋮ > Reload) or restart Home Assistant "
    "to convert the existing devices to child devices. Until then Home Assistant logs 'Unable to register MQTT device' warnings "
    "and the entities keep working unchanged."
)


def publishes_as_ha_child(device: Device) -> bool:
    """Return True if *device* is published as a Home Assistant child of its parent."""
    return active_config.home_assistant.child_devices and device.parent_device is not None and device.ha_child_device_eligible


def _ha_children(device: Device) -> list[Device]:
    return [child for child in device.children if child.ha_child_device_eligible]


def validate_hierarchy(devices: Iterable[Device]) -> list[str]:
    """Check the child-device constraints Home Assistant enforces.

    Returns a list of problems; an empty list means the hierarchy can be published.
    Checked before anything is published, so a failure changes nothing.
    """
    devices = list(devices)
    problems: list[str] = []
    # Home Assistant only resolves via_device to a regular device, and converting a
    # device to a child detaches every via_device link that pointed at it.
    ha_child_ids = {d.unique_id: d for d in devices if publishes_as_ha_child(d)}
    for device in devices:
        if (target := ha_child_ids.get(device.via_device or "")) is not None:
            problems.append(f"{device.log_identity} is linked with via_device to {target.log_identity}, which is published as a child device")
    for device in devices:
        children = _ha_children(device)
        if not children:
            continue
        if device.parent_device is not None and device.ha_child_device_eligible:
            problems.append(f"{device.log_identity} is a child device but has child devices of its own ({', '.join(c.log_identity for c in children)})")
        seen: dict[str, str] = {}
        parent_ids = set(device.get("identifiers", []))
        for child in children:
            if child.parent_device is not device:
                problems.append(f"{child.log_identity} is listed as a child of {device.log_identity} but its parent is {getattr(child.parent_device, 'log_identity', None)}")
            if child.unique_id in parent_ids:
                problems.append(f"{child.log_identity} has the same identifier as its parent {device.log_identity}: {child.unique_id}")
            if child.unique_id in seen:
                problems.append(f"{child.log_identity} and {seen[child.unique_id]} share the identifier {child.unique_id}")
            seen[child.unique_id] = child.log_identity
    return problems


def parse_ha_version(version: str) -> tuple[int, int] | None:
    match = re.match(r"^\s*(\d+)\.(\d+)", version or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


class HaVersionUnavailable(Exception):
    """Running under the Supervisor, but the Home Assistant version could not be read."""


def _fetch_ha_version_sync() -> str | None:
    import requests

    token = os.getenv("SUPERVISOR_TOKEN")
    if not token:
        return None
    base_url = os.getenv("SUPERVISOR_URL", "http://supervisor").rstrip("/")
    try:
        response = requests.get(f"{base_url}/core/api/config", headers={"Authorization": f"Bearer {token}"}, timeout=5)
    except (OSError, requests.RequestException) as exc:
        raise HaVersionUnavailable(str(exc)) from exc
    if response.status_code != 200:
        raise HaVersionUnavailable(f"status_code={response.status_code}")
    try:
        version = response.json().get("version")
    except (AttributeError, ValueError) as exc:
        raise HaVersionUnavailable(f"invalid response: {exc}") from exc
    if not isinstance(version, str):
        raise HaVersionUnavailable(f"no version in response: {version!r}")
    return version


async def fetch_ha_version() -> str | None:
    """Return the Home Assistant Core version when running as an add-on, or None for a standalone install.

    Raises:
        HaVersionUnavailable: running as an add-on, but the version could not be read
            (for example because Home Assistant is still starting).
    """
    return await asyncio.to_thread(_fetch_ha_version_sync)


class ChildDeviceMigration:
    """Preflight checks and persisted migration stage for Home Assistant child devices."""

    def __init__(self) -> None:
        self.stage: str | None = None
        self._published_at: float | None = None
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self.stage = None
            self._published_at = None

    async def prepare(self, devices: Iterable[Device]) -> bool:
        """Run before any discovery is published. Returns whether child devices are in effect.

        On a failed preflight, ``home-assistant.child-devices`` is switched off for this
        run (the legacy payloads are published unchanged) and the reason is logged.
        """
        from sigenergy2mqtt.persistence import Category, state_store

        self.reset()
        devices = list(devices)
        stored = await state_store.load(Category.CONFIG, MIGRATION_STATE_KEY)
        stored = stored if stored in STAGES else None
        ha = active_config.home_assistant

        if not ha.enabled or not ha.child_devices:
            if stored in (STAGE_PENDING_RELOAD, STAGE_CHILD_DEVICES):
                logger.warning(
                    "home-assistant.child-devices was disabled after child-device discovery was published. Home Assistant can't convert a child device "
                    "back to a regular device: until each sigenergy2mqtt child device is deleted in Home Assistant and the MQTT integration is reloaded, "
                    "the affected entities stay on their child devices (and may be unavailable after a restart). Deleting them is safe: they return "
                    "as regular devices with the same device and entity IDs."
                )
                await state_store.save(Category.CONFIG, MIGRATION_STATE_KEY, STAGE_LEGACY)
            self.stage = STAGE_LEGACY
            return False

        problems = validate_hierarchy(devices)
        if problems:
            for problem in problems:
                logger.error(f"Home Assistant child devices: {problem}")
            return self._refuse("the device hierarchy does not meet Home Assistant's child-device constraints")

        try:
            version = await fetch_ha_version()
        except HaVersionUnavailable as exc:
            if stored not in (STAGE_PENDING_RELOAD, STAGE_CHILD_DEVICES):
                return self._refuse(
                    f"running as a Home Assistant add-on, but the Home Assistant version could not be read via the Supervisor API ({exc}); "
                    "Home Assistant may still be starting. Restart sigenergy2mqtt once Home Assistant is running to retry"
                )
            # A previous run already published child-device discovery after a successful
            # version check. Falling back now would replace it with via_device payloads that
            # Home Assistant can't apply to converted child devices.
            logger.warning(f"Unable to read the Home Assistant version via the Supervisor API ({exc}); keeping the child-device discovery already published")
            version = None
        else:
            if version is None:
                logger.info(
                    f"Home Assistant child devices enabled; the Home Assistant version can't be checked outside the add-on, so make sure it is "
                    f"{MIN_HA_VERSION[0]}.{MIN_HA_VERSION[1]}.0 or later (older releases reject child-device discovery and will not rediscover "
                    "those entities after a restart)"
                )
        if version is not None:
            parsed = parse_ha_version(version)
            if parsed is None or parsed < MIN_HA_VERSION:
                return self._refuse(f"Home Assistant {version} does not support MQTT child devices (requires {MIN_HA_VERSION[0]}.{MIN_HA_VERSION[1]}.0 or later)")
            logger.debug(f"Home Assistant {version} supports MQTT child devices")

        if not any(publishes_as_ha_child(d) for d in devices):
            self.stage = stored or STAGE_LEGACY
            return True

        if stored == STAGE_CHILD_DEVICES:
            self.stage = STAGE_CHILD_DEVICES
            return True

        self.stage = STAGE_PENDING_RELOAD
        self._published_at = time.monotonic()
        if stored != STAGE_PENDING_RELOAD:
            await state_store.save(Category.CONFIG, MIGRATION_STATE_KEY, STAGE_PENDING_RELOAD)
            logger.warning(f"Publishing Home Assistant child-device discovery for the first time. {_RELOAD_ADVICE}")
        else:
            logger.warning(f"Home Assistant child-device discovery is still waiting for a reload of the MQTT integration. {_RELOAD_ADVICE}")
        return True

    def _refuse(self, reason: str) -> bool:
        logger.error(f"Home Assistant child devices NOT enabled: {reason}. Publishing the existing via_device discovery unchanged.")
        active_config.home_assistant.child_devices = False
        self.stage = STAGE_LEGACY
        return False

    async def note_ha_online(self) -> None:
        """Record that Home Assistant (re)loaded MQTT after child-device discovery was published.

        HA sends its birth message whenever its MQTT client connects: after a restart or
        an MQTT reload, but also after a broker reconnect, which does not convert the
        devices. The recorded stage is therefore only used for log guidance.

        Called from the device threads, each with its own event loop.
        """
        with self._lock:
            if self.stage != STAGE_PENDING_RELOAD or self._published_at is None:
                return
            if time.monotonic() - self._published_at < _RELOAD_GRACE_SECONDS:
                return
            self.stage = STAGE_CHILD_DEVICES
        logger.info("Home Assistant reconnected after child-device discovery was published; existing devices should now be child devices")

        from sigenergy2mqtt.persistence import Category, state_store

        # save_sync posts to the state store's own loop when called from another thread
        await asyncio.to_thread(state_store.save_sync, Category.CONFIG, MIGRATION_STATE_KEY, STAGE_CHILD_DEVICES)


child_device_migration = ChildDeviceMigration()
