from contextlib import asynccontextmanager
from random import randint
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.mqtt import MqttClient
from typing import Any
import asyncio
import logging
import re
import requests
import time


class Service(Device):
    _donator: bool = None
    _interval: int = None  # Interval in minutes for PVOutput status updates
    _interval_updated: float = None

    def __init__(self, name: str, unique_id: str, model: str, logger: logging.Logger):
        super().__init__(name, -1, unique_id, "sigenergy2mqtt", model)
        self._logger = logger
        self._lock = asyncio.Lock()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def request_headers(self) -> dict[str, str]:
        return {
            "X-Pvoutput-Apikey": Config.pvoutput.api_key,
            "X-Pvoutput-SystemId": Config.pvoutput.system_id,
            "X-Rate-Limit": "1",
        }

    @asynccontextmanager
    async def lock(self, timeout=None):
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

    def publish_availability(self, mqtt: MqttClient, ha_state, qos=2) -> None:
        pass

    def publish_discovery(self, mqtt: MqttClient, clean=False) -> Any:
        pass

    # endregion

    def get_response_headers(self, response: requests.Response) -> tuple[int, int, float, float]:
        limit = int(response.headers["X-Rate-Limit-Limit"])
        remaining = int(response.headers["X-Rate-Limit-Remaining"])
        at = float(response.headers["X-Rate-Limit-Reset"])
        reset = round(at - time.time())
        return limit, remaining, at, reset

    async def seconds_until_status_upload(self, rand_min: int = 1, rand_max: int = 15) -> tuple[float, int]:
        url = "https://pvoutput.org/service/r2/getsystem.jsp?donations=1"
        current_time = time.time()  # Current time in seconds since epoch
        async with self._lock:
            if Service._interval is None or Service._interval_updated is None or (Service._interval_updated + 3600) < current_time:
                self.logger.debug(
                    f"{self.__class__.__name__} Service cache needs updating: {Service._donator=} {Service._interval=} {Service._interval_updated=} {current_time=} next_update={(Service._interval_updated + 3600) if Service._interval_updated is not None and Service._interval is not None else current_time}"
                )
                if Config.pvoutput.testing:
                    Service._interval = 5
                    Service._interval_updated = current_time
                    Service._donator = 1
                    self.logger.info(
                        f"{self.__class__.__name__} Testing mode, not sending request to {url=} - using default/previous interval of {Service._interval} minutes and donator status {Service._donator}"
                    )
                else:
                    self.logger.debug(f"{self.__class__.__name__} Acquiring System Information from PVOutput ({url=})")
                    try:
                        with requests.get(url, headers=self.request_headers, timeout=10) as response:
                            limit, remaining, at, reset = self.get_response_headers(response)
                            if response.status_code == 200:
                                section = re.split(r"[;]", response.text)
                                interval = int(re.split(r"[,]", section[0])[15])
                                donations = int(section[2])
                                self.logger.debug(
                                    f"{self.__class__.__name__} Acquired {interval=} {donations=} OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)"
                                )
                                Service._interval_updated = current_time
                                if Service._interval != interval:
                                    self.logger.info(f"{self.__class__.__name__} Status Interval changed from {Service._interval} to {interval} minutes")
                                    Service._interval = interval
                                if Service._donator != (donations != 0):
                                    self.logger.info(f"{self.__class__.__name__} Donation Status changed from {Service._donator} to {donations != 0}")
                                    Service._donator = donations != 0
                            else:
                                self.logger.warning(f"{self.__class__.__name__} FAILED to acquire System Information status_code={response.status_code} reason={response.reason}")
                    except Exception as exc:
                        if Service._interval is None:
                            Service._interval = 5  # Default interval in minutes if not set
                        if Service._donator is None:
                            Service._donator = False  # Default donator status if not set
                        self.logger.warning(
                            f"{self.__class__.__name__} Failed to acquire System Information from PVOutput: {exc} - using default/previous interval of {Service._interval} minutes and donator status {Service._donator}"
                        )
        minutes = int(current_time // 60)  # Total minutes since epoch
        next_boundary = (minutes // Service._interval + 1) * Service._interval  # Next interval boundary
        next_time = (next_boundary * 60) + randint(rand_min, rand_max)  # Convert back to seconds with a random offset for variability
        seconds = 60 if Config.pvoutput.testing else float(next_time - current_time)
        return seconds, next_time

    async def upload_payload(self, url: str, payload: dict[str, any]) -> bool:
        self.logger.info(f"{self.__class__.__name__} Uploading {payload=}")
        uploaded = False
        for i in range(1, 4, 1):
            try:
                if Config.pvoutput.testing:
                    uploaded = True
                    self.logger.info(f"{self.__class__.__name__} Testing mode, not sending upload to {url=}")
                    break
                else:
                    self.logger.debug(f"{self.__class__.__name__} Attempt #{i} to {url=}...")
                    with requests.post(url, headers=self.request_headers, data=payload, timeout=10) as response:
                        limit, remaining, at, reset = self.get_response_headers(response)
                        if response.status_code == 200:
                            uploaded = True
                            self.logger.debug(
                                f"{self.__class__.__name__} Attempt #{i} OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)"
                            )
                            break
                        else:
                            self.logger.warning(f"{self.__class__.__name__} Attempt #{i} FAILED status_code={response.status_code} reason={response.reason}")
                        if int(response.headers["X-Rate-Limit-Remaining"]) < 10:
                            self.logger.warning(f"{self.__class__.__name__} Only {remaining} requests left, sleeping until {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)")
                            await asyncio.sleep(reset)
                        else:
                            response.raise_for_status()
                            break
            except requests.exceptions.HTTPError as exc:
                response = exc.response
                limit, remaining, at, reset = self.get_response_headers(response)
                if response.status_code == 400:
                    self.logger.error(f"{self.__class__.__name__} Bad Request 400: {response.text} ({limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))})")
                    break
                else:
                    self.logger.error(f"{self.__class__.__name__} HTTP Error: {exc} ({limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))})")
            except requests.exceptions.ConnectionError as exc:
                self.logger.error(f"{self.__class__.__name__} Error Connecting: {exc}")
            except requests.exceptions.Timeout as exc:
                self.logger.error(f"{self.__class__.__name__} Timeout Error: {exc}")
            except Exception as exc:
                self.logger.error(f"{self.__class__.__name__} {exc}")
            if i <= 2:
                self.logger.info(f"{self.__class__.__name__} Retrying in 10 seconds")
                await asyncio.sleep(10)
        else:
            self.logger.error(f"{self.__class__.__name__} Failed to upload to {url} after 3 attempts")
        return uploaded
