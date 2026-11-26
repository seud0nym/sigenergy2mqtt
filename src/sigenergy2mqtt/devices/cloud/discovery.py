"""Startup discovery for cloud-backed devices."""

import asyncio
import logging
from dataclasses import dataclass, replace
from typing import Any

from aiohttp import ClientError

from sigenergy2mqtt.cloud.exceptions import (
    CloudControlError,
    CloudControlUnavailableError,
)
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import SigenergyCloudClient
from sigenergy2mqtt.config import active_config

logger = logging.getLogger(__name__)

_GATEWAY_DISCOVERY_ATTEMPTS = 3
_GATEWAY_DISCOVERY_RETRY_DELAY = 1.0


@dataclass(frozen=True)
class DcChargerDiscovery:
    """Static DC charger capabilities read once at startup."""

    serial_number: str
    charge_modes: tuple[int, ...] = ()
    soc_range: tuple[float, float] = (0.0, 100.0)


@dataclass(frozen=True)
class CloudDiscovery:
    """Cloud responses needed to assemble the control device and its children."""

    device_list: list[dict[str, Any]]
    gateway_info: dict[str, Any] | None = None
    operational_modes: dict[str, object] | None = None
    device_info: dict[str, tuple[dict[str, Any], dict[str, Any]]] | None = None
    battery_pack_info: dict[str, dict[str, Any]] | None = None
    dc_chargers: tuple[DcChargerDiscovery, ...] = ()
    #: ``sgDeviceType`` values sharing surplus PV, in the station's priority order.
    surplus_pv_devices: tuple[int, ...] = ()

    @property
    def has_battery(self) -> bool:
        return any(device.get("deviceType") == "Battery" for device in self.device_list)


async def _discover_cloud_gateway_info(cloud_port: CloudControlPort) -> dict[str, Any] | None:
    """Read gateway metadata, retrying transient startup failures."""
    for attempt in range(1, _GATEWAY_DISCOVERY_ATTEMPTS + 1):
        try:
            return await cloud_port.gateway_info()
        except CloudControlUnavailableError as exc:
            if attempt == _GATEWAY_DISCOVERY_ATTEMPTS:
                logger.warning("Cloud gateway discovery failed after %d attempts; gateway sensors will be disabled: %s", attempt, exc)
                return None
            logger.warning("Cloud gateway discovery failed (attempt %d/%d); retrying: %s", attempt, _GATEWAY_DISCOVERY_ATTEMPTS, exc)
            await asyncio.sleep(_GATEWAY_DISCOVERY_RETRY_DELAY)
        except (ClientError, CloudControlError) as exc:
            logger.warning("Cloud gateway discovery failed without retry; gateway sensors will be disabled: %s", exc)
            return None
    raise AssertionError("gateway discovery retry loop exhausted")


async def _discover_cloud_device_list(cloud_port: CloudControlPort) -> list[dict[str, Any]] | None:
    """Discover the plant device list from the cloud."""
    try:
        return await cloud_port.device_list()
    except (ClientError, CloudControlError) as exc:
        logger.warning("Cloud inverter discovery failed; Cloud API will be disabled for this run: %s", exc)
        return None


async def discover_cloud(cloud_port: CloudControlPort) -> CloudDiscovery | None:
    """Collect discovery data that is safe to obtain before plant matching."""
    gateway_info = await _discover_cloud_gateway_info(cloud_port)
    if (device_list := await _discover_cloud_device_list(cloud_port)) is None:
        return None
    if not active_config.cloud.discover_inverters:
        logger.info("Cloud inverter discovery disabled by configuration; discovered inverters will be ignored")
    device_info: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    battery_pack_info: dict[str, dict[str, Any]] = {}
    for device in device_list:
        device_name = device.get("deviceType")
        if not active_config.cloud.discover_inverters and device_name == "Inverter":
            continue
        device_type = {"Inverter": 3, "Battery": 4}.get(device_name) if isinstance(device_name, str) else None
        sn_code = device.get("serialNumber")
        if device_type is None or not isinstance(sn_code, str) or not sn_code:
            continue
        valid_device_type: int = device_type
        valid_sn_code: str = sn_code

        async def read_info(
            static: bool,
            dtype: int = valid_device_type,
            sn: str = valid_sn_code,
        ) -> dict[str, Any]:
            try:
                method = cloud_port.device_static_info if static else cloud_port.device_dynamic_info
                return await method(dtype, sn)
            except (ClientError, CloudControlError) as exc:
                kind = "static" if static else "dynamic"
                logger.warning("Cloud %s device discovery failed for %s: %s", kind, sn, exc)
                return {}

        dynamic, static = await asyncio.gather(read_info(False), read_info(True), return_exceptions=False)
        device_info[valid_sn_code] = (dynamic, static)
        if device_name == "Battery":
            try:
                battery_pack_info[valid_sn_code] = await cloud_port.battery_pack_merge_info(valid_sn_code)
            except (ClientError, CloudControlError) as exc:
                logger.warning("Cloud battery pack discovery failed for %s: %s", valid_sn_code, exc)
    return CloudDiscovery(device_list=device_list, gateway_info=gateway_info, device_info=device_info, battery_pack_info=battery_pack_info)


async def discover_operational_modes(cloud_port: CloudControlPort, discovery: CloudDiscovery) -> CloudDiscovery:
    """Add operational modes after the cloud station has matched a local plant."""
    operational_modes: dict[str, object] | None = None
    try:
        payload = await cloud_port.available_operational_modes()
        if isinstance(payload, dict):
            operational_modes = payload
        else:
            logger.warning("Cloud operational-mode discovery returned an invalid response")
    except (ClientError, CloudControlError) as exc:
        logger.warning("Cloud operational-mode discovery failed; sensor will be disabled: %s", exc)
    return replace(discovery, operational_modes=operational_modes)


def _soc_range(payload: object) -> tuple[float, float]:
    """Return the (lower, upper) SOC limits, defaulting to 0-100%."""
    if isinstance(payload, dict):
        try:
            lower, upper = float(payload["socLowerLimit"]), float(payload["socUpperLimit"])
            if 0.0 <= lower < upper <= 100.0:
                return lower, upper
        except (KeyError, TypeError, ValueError):
            pass
    return 0.0, 100.0


async def discover_dc_chargers(cloud_port: CloudControlPort, discovery: CloudDiscovery) -> CloudDiscovery:
    """Add DC charger capabilities after the cloud station has matched a local plant."""
    serials = [
        str(device["serialNumber"])
        for device in discovery.device_list
        if device.get("deviceType") == "DcCharger" and isinstance(device.get("serialNumber"), str) and device["serialNumber"]
    ]
    if not serials:
        return discovery

    surplus_pv_devices: tuple[int, ...] = ()
    soc_range = (0.0, 100.0)
    try:
        surplus_pv_devices = tuple(SigenergyCloudClient.surplus_pv_priority_order(await cloud_port.energy_profile_setting()))
    except (ClientError, CloudControlError) as exc:
        logger.warning("Cloud Site PV Surplus Priority discovery failed; the sensor will be disabled: %s", exc)
    try:
        soc_range = _soc_range(await cloud_port.dc_charge_mode_soc_range())
    except (ClientError, CloudControlError) as exc:
        logger.warning("Cloud DC charger SOC range discovery failed; using 0-100%%: %s", exc)

    chargers: list[DcChargerDiscovery] = []
    for sn in serials:
        charge_modes: tuple[int, ...] = ()
        try:
            if await cloud_port.dc_charge_mode_supported(sn):
                charge_modes = tuple(await cloud_port.dc_supported_charge_modes(sn))
            else:
                logger.info("Cloud DC charger %s does not support charging modes; mode sensors will be disabled", sn)
        except (ClientError, CloudControlError) as exc:
            logger.warning("Cloud DC charger %s charging-mode discovery failed; mode sensors will be disabled: %s", sn, exc)
        chargers.append(DcChargerDiscovery(sn, charge_modes=charge_modes, soc_range=soc_range))
    return replace(discovery, dc_chargers=tuple(chargers), surplus_pv_devices=surplus_pv_devices)
