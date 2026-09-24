"""Selection and lifecycle ownership for cloud control."""

import logging
from typing import Literal

from sigenergy2mqtt.config.models.cloud import CloudConfig

from .mysigen_adapter import MySigenCloudAdapter
from .port import CloudControlPort

logger = logging.getLogger("sigenergy2mqtt.cloud")
Provider = Literal["mysigen", "official"]


class CloudControlRegistry:
    def __init__(self) -> None:
        self._adapter: CloudControlPort | None = None
        self._provider: Provider | None = None

    def configure(self, config: CloudConfig) -> None:
        if not config.enabled:
            self._adapter = None
            self._provider = None
            return
        if not config.accept_unofficial_api_risk:
            raise ValueError("cloud.accept-unofficial-api-risk must be true to use the unofficial mySigen cloud API")
        logger.warning("Using the unofficial mySigen cloud API. Use a delegated 'View and Edit' account created with mySigen System Share rather than the primary account.")
        self._adapter = MySigenCloudAdapter(config.username, config.password, config.region)
        self._provider = "mysigen"

    @property
    def active(self) -> CloudControlPort | None:
        return self._adapter

    @property
    def provider(self) -> Provider | None:
        return self._provider

    async def transport_factory(self) -> CloudControlPort | None:
        if self._adapter is not None:
            try:
                await self._adapter.connect()
            except BaseException:
                # connect() may have opened an owned HTTP session before auth
                # or station discovery failed. The adapter never reached the
                # device thread in that case, so the registry must close it.
                try:
                    await self._adapter.close()
                except Exception:
                    logger.exception("Failed to close cloud adapter after connect failure")
                raise
        return self._adapter

    async def close(self) -> None:
        if self._adapter is not None:
            await self._adapter.close()


cloud_control_registry = CloudControlRegistry()
