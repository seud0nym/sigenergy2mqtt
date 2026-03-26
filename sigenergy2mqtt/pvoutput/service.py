"""Base PVOutput service helpers shared by status and output uploaders."""

import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from random import randint
from typing import Any

import paho.mqtt.client as mqtt
import requests
from requests.structures import CaseInsensitiveDict

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device


class Service(Device):
    """Common PVOutput device behavior for API timing and uploads."""
    _donator: bool = False
    _interval: int = 5  # Interval in minutes for PVOutput status updates
    _interval_updated: float | None = None

    def __init__(self, name: str, unique_id: str, model: str, logger: logging.Logger):
        """Initialize the shared service wrapper and synchronization lock.

        Args:
            name: Human-readable service name exposed through the device model.
            unique_id: Stable unique identifier for this virtual device.
            model: Model string used for metadata/logging.
            logger: Logger instance used by the service.
        """
        super().__init__(name, -1, unique_id, "sigenergy2mqtt", model, Protocol.N_A)
        self.logger = logger
        self._lock = asyncio.Lock()

    @property
    def request_headers(self) -> dict[str, str]:
        """Return HTTP headers required by the PVOutput API.

        Args:
            None.
        """
        return {
            "X-Pvoutput-Apikey": active_config.pvoutput.api_key,
            "X-Pvoutput-SystemId": active_config.pvoutput.system_id,
            "X-Rate-Limit": "1",
        }

    @asynccontextmanager
    async def lock(self, timeout=None):
        """Acquire and release the service lock with an optional timeout.

        Args:
            timeout: Optional number of seconds to wait for the lock.
        """
        acquired: bool = False
        try:
            if timeout is None:
                acquired = await self._lock.acquire()
            else:
                acquired = await asyncio.wait_for(self._lock.acquire(), timeout)
                if not acquired:
                    raise TimeoutError("Failed to acquire lock within the timeout period.")
            yield
        finally:
            if acquired and self._lock.locked():
                self._lock.release()

    # region Device overrides

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state, qos=2) -> None:
        """No-op override: PVOutput services do not publish availability topics.

        Args:
            mqtt_client: MQTT client instance (unused).
            ha_state: Home Assistant availability state (unused).
            qos: MQTT QoS level (unused).
        """
        pass

    def publish_discovery(self, mqtt_client: mqtt.Client, clean=False) -> mqtt.MQTTMessageInfo | None:
        """No-op override: PVOutput services are not Home Assistant entities.

        Args:
            mqtt_client: MQTT client instance (unused).
            clean: Cleanup mode flag (unused).
        """
        pass

    # endregion

    def get_response_headers(self, response: requests.Response) -> tuple[int, int, float, float]:
        """Extract PVOutput rate-limit metadata from an HTTP response.

        Args:
            response: HTTP response returned by a PVOutput endpoint.
        """
        limit = int(response.headers["X-Rate-Limit-Limit"])
        remaining = int(response.headers["X-Rate-Limit-Remaining"])
        at = float(response.headers["X-Rate-Limit-Reset"])
        reset = round(at - time.time())
        return limit, remaining, at, reset

    async def seconds_until_status_upload(self, rand_min: int = 1, rand_max: int = 15) -> tuple[float, int]:
        """Compute the next status upload slot and refresh interval metadata.

        Args:
            rand_min: Minimum random offset (seconds) added to the upload slot.
            rand_max: Maximum random offset (seconds) added to the upload slot.
        """
        url = "https://pvoutput.org/service/r2/getsystem.jsp?donations=1"
        current_time = time.time()  # Current time in seconds since epoch
        async with self._lock:
            if Service._interval_updated is None or (Service._interval_updated + 3600) < current_time:
                self.logger.debug(
                    f"{self.log_identity} Service cache needs updating: {Service._donator=} {Service._interval=} {Service._interval_updated=} {current_time=} next_update={(Service._interval_updated + 3600) if Service._interval_updated is not None else current_time}"
                )
                if active_config.pvoutput.testing:
                    Service._interval = 5
                    Service._interval_updated = current_time
                    Service._donator = True
                    self.logger.info(
                        f"{self.log_identity} Testing mode, not sending request to {url=} - using default/previous interval of {Service._interval} minutes and donator status {Service._donator}"
                    )
                else:
                    self.logger.debug(f"{self.log_identity} Acquiring System Information from PVOutput ({url=})")
                    try:
                        response = await asyncio.to_thread(requests.get, url, headers=self.request_headers, timeout=10)
                        limit, remaining, at, reset = self.get_response_headers(response)
                        if response.status_code == 200:
                            section = re.split(r"[;]", response.text)
                            interval = int(re.split(r"[,]", section[0])[15])
                            donations = int(section[2])
                            self.logger.debug(
                                f"{self.log_identity} Acquired {interval=} {donations=} OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)"
                            )
                            Service._interval_updated = current_time
                            if Service._interval != interval:
                                self.logger.info(f"{self.log_identity} Status Interval changed from {Service._interval} to {interval} minutes")
                                Service._interval = interval
                            if Service._donator != (donations != 0):
                                self.logger.info(f"{self.log_identity} Donation Status changed from {Service._donator} to {donations != 0}")
                                Service._donator = donations != 0
                        else:
                            self.logger.warning(f"{self.log_identity} FAILED to acquire System Information status_code={response.status_code} reason={response.reason}")
                    except Exception as exc:
                        Service._interval = 5  # Default interval in minutes if not set
                        Service._donator = False  # Default donator status if not set
                        self.logger.warning(
                            f"{self.log_identity} Failed to acquire System Information from PVOutput: {exc} - using default/previous interval of {Service._interval} minutes and donator status {Service._donator}"
                        )
        minutes = int(current_time // 60)  # Total minutes since epoch
        next_boundary = (minutes // Service._interval + 1) * Service._interval  # Next interval boundary
        next_time = (next_boundary * 60) + randint(rand_min, rand_max)  # Convert back to seconds with a random offset for variability
        seconds = 60 if active_config.pvoutput.testing else float(next_time - current_time)
        return seconds, next_time

    async def upload_payload(self, url: str, payload: dict[str, Any]) -> bool:
        """Upload one payload to PVOutput with retries and limit-aware backoff.

        Args:
            url: PVOutput endpoint URL.
            payload: Form payload to submit.
        """
        self.logger.info(f"{self.log_identity} Uploading {payload=}")
        uploaded: bool = False
        response: requests.Response = requests.Response()
        attempts: int = 0
        for i in range(1, 4, 1):
            attempts = i
            try:
                if active_config.pvoutput.testing:
                    uploaded = True
                    self.logger.info(f"{self.log_identity} Testing mode, not sending upload to {url=}")
                    cid = CaseInsensitiveDict()
                    cid["X-Rate-Limit-Remaining"] = "60"
                    response.status_code = 200
                    response.headers = cid
                    break
                else:
                    self.logger.debug(f"{self.log_identity} Attempt #{i} to {url=}...")
                    response = await asyncio.to_thread(requests.post, url, headers=self.request_headers, data=payload, timeout=10)
                    limit, remaining, at, reset = self.get_response_headers(response)
                    if response.status_code == 200:
                        uploaded = True
                        self.logger.debug(
                            f"{self.log_identity} Attempt #{i} OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)"
                        )
                        break
                    else:
                        response.raise_for_status()
                        break
            except requests.exceptions.HTTPError as exc:
                response = exc.response
                limit, remaining, at, reset = self.get_response_headers(response)
                if response.status_code == 400:
                    self.logger.error(f"{self.log_identity} Attempt #{i} Bad Request 400: {response.text} ({limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))})")
                    break
                else:
                    self.logger.error(f"{self.log_identity} Attempt #{i} HTTP Error: {exc} ({limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))})")
            except requests.exceptions.ConnectionError as exc:
                self.logger.error(f"{self.log_identity} Attempt #{i} Error Connecting: {exc}")
            except requests.exceptions.Timeout as exc:
                self.logger.error(f"{self.log_identity} Attempt #{i} Timeout Error: {exc}")
            except Exception as exc:
                self.logger.error(f"{self.log_identity} {exc}")
            if (
                response.status_code is not None
                and response.status_code != 200
                and hasattr(response, "headers")
                and "X-Rate-Limit-Remaining" in response.headers
                and int(response.headers["X-Rate-Limit-Remaining"]) < 10
            ):
                self.logger.warning(f"{self.log_identity} Only {remaining} requests left, sleeping until {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)")  # pyright: ignore[reportPossiblyUnboundVariable] # pyrefly: ignore
                try:
                    await asyncio.sleep(reset)  # pyright: ignore[reportPossiblyUnboundVariable]  # pyrefly: ignore
                except asyncio.CancelledError:
                    logging.debug(f"{self.log_identity} reset sleep interrupted")
                    break
            else:
                self.logger.info(f"{self.log_identity} Retrying in 10 seconds")
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    logging.debug(f"{self.log_identity} retry sleep interrupted")
                    break
        else:
            self.logger.error(f"{self.log_identity} Failed to upload to {url} after {attempts} attempts")
        return uploaded
