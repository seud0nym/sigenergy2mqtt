import asyncio
import json
import logging
import time
from typing import Any, Awaitable, cast

import paho.mqtt.client as mqtt
import requests
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import WriteOptions
from requests.adapters import HTTPAdapter

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.modbus.types import ModbusClientType
from sigenergy2mqtt.mqtt import MqttHandler


class InfluxService(Device):
    def __init__(self, logger: logging.Logger, plant_index: int = -1):
        # Create one service instance per plant_index so each caches its own sensors
        name = f"Sigenergy InfluxDB Updater Service (Plant {plant_index})"
        unique = f"influxdb_updater_{plant_index}"
        super().__init__(name, plant_index, unique, "sigenergy2mqtt", "InfluxDB.Updater", Protocol.N_A)

        self.logger = logger
        urllib3 = logging.getLogger("urllib3")
        urllib3.setLevel(logging.INFO)
        urllib3.propagate = True

        self.plant_index = plant_index
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        self._version = None
        self._base_url = None

        # Cache mapping state_topic -> {uom, object_id, unique_id}
        self._topic_cache: dict[str, dict[str, Any]] = {}

        # Only attempt to initialize connection when InfluxDB is enabled in config
        # Otherwise set defaults so unit tests can instantiate without network
        self._writer_type = None
        self._writer_obj = None
        self._write_url = None
        self._write_headers = None
        self._write_auth = None
        self._writer_obj_bucket = None
        self._writer_obj_org = None

        if getattr(Config, "influxdb", None) and getattr(Config.influxdb, "enabled", False):
            try:
                self._init_connection()
            except Exception as e:
                self.logger.error(f"{self.name} Initialization failed during service init: {e}")
                raise

    def _init_connection(self) -> None:
        # Determine InfluxDB version/method and ensure target database/bucket exists.
        host = Config.influxdb.host
        port = Config.influxdb.port
        db = Config.influxdb.database
        user = Config.influxdb.username
        pwd = Config.influxdb.password
        token = Config.influxdb.token
        org = Config.influxdb.org
        bucket = Config.influxdb.bucket or db
        # Backwards-compat: if no explicit token provided but a password is
        # supplied and no username, treat the password as a v2 token.
        if not token and pwd and not user:
            token = pwd
        base = f"http://{host}:{port}"

        test_line = b"state value=1"

        # Prefer v2/client only when token provided. If a username is provided, prefer v1 HTTP.
        # 1) Official client (v2) when token is provided
        if token:
            try:
                client = InfluxDBClient(url=base, token=token)
                write_api = client.write_api(write_options=WriteOptions(batch_size=1))
                try:
                    write_api.write(bucket=bucket, org=org, record=test_line)
                except Exception:
                    client.close()
                    raise
                self._writer_type = "client"
                self._writer_obj = client
                self._writer_obj_bucket = bucket
                self._writer_obj_org = org
                self.logger.info(f"{self.name} Using official client for writes (v2 token)")
                return
            except Exception as e:
                self.logger.debug(f"{self.name} Client detection/initial write failed: {e}")

        # If username is provided, prefer v1 HTTP (InfluxDB 1.x)
        if user:
            try:
                url_v1 = f"{base}/write"
                auth = (user, pwd) if user or pwd else None
                r = self._session.post(url_v1, params={"db": db}, data=test_line, auth=auth, timeout=5)
                if r.status_code in (204, 200):
                    self._writer_type = "v1_http"
                    self._write_url = url_v1
                    self._write_auth = auth
                    self.logger.info(f"{self.name} Using v1 HTTP write endpoint to {url_v1}")
                    return
                # Attempt to create database and retry
                if r.status_code in (404, 400) or (r.status_code >= 400 and r.content and b"database" in r.content.lower()):
                    create_url = f"{base}/query"
                    q = {"q": f"CREATE DATABASE {db}"}
                    r2 = self._session.post(create_url, params=q, auth=auth, timeout=5)
                    if r2.status_code == 200:
                        r3 = self._session.post(url_v1, params={"db": db}, data=test_line, auth=auth, timeout=5)
                        if r3.status_code in (204, 200):
                            self._writer_type = "v1_http"
                            self._write_url = url_v1
                            self._write_auth = auth
                            self.logger.info(f"{self.name} Created v1 database and will use v1 HTTP write to {url_v1}")
                            return
            except Exception as e:
                self.logger.debug(f"{self.name} v1 HTTP detection failed: {e}")

        # Try v2 HTTP write endpoint (may succeed without a token)
        try:
            url_v2 = f"{base}/api/v2/write?bucket={bucket}&precision=s"
            if org:
                url_v2 += f"&org={org}"
            headers = {"Authorization": f"Token {token}"} if token else {}
            r = self._session.post(url_v2, headers=headers or None, data=test_line, timeout=5)
            if r.status_code in (204, 200):
                self._writer_type = "v2_http"
                self._write_url = url_v2
                self._write_headers = headers or {}
                self.logger.info(f"{self.name} Using v2 HTTP write endpoint to {url_v2}")
                return
            # If bucket not found and token provided, attempt to create it
            if r.status_code in (400, 404) and token:
                headers_create = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
                orgs = self._session.get(f"{base}/api/v2/orgs", headers=headers_create, timeout=5)
                if orgs.status_code == 200:
                    items = orgs.json()
                    org_id = None
                    if isinstance(items, dict) and items.get("orgs"):
                        lst = items.get("orgs")
                        if isinstance(lst, list) and lst:
                            org_id = lst[0].get("id")
                    if org_id:
                        create_bucket = {"name": bucket, "orgID": org_id}
                        r2 = self._session.post(f"{base}/api/v2/buckets", headers=headers_create, data=json.dumps(create_bucket), timeout=5)
                        if r2.status_code in (201, 200):
                            # retry write
                            r3 = self._session.post(url_v2, headers=headers or None, data=test_line, timeout=5)
                            if r3.status_code in (204, 200):
                                self._writer_type = "v2_http"
                                self._write_url = url_v2
                                self._write_headers = headers or {}
                                self.logger.info(f"{self.name} Created v2 bucket and will use v2 HTTP write to {url_v2}")
                                return
        except Exception as e:
            self.logger.debug(f"{self.name} v2 HTTP detection failed: {e}")

        # Final fallback: try v1 HTTP without username (no auth)
        try:
            url_v1 = f"{base}/write"
            auth = (user, pwd) if user or pwd else None
            r = self._session.post(url_v1, params={"db": db}, data=test_line, auth=auth, timeout=5)
            if r.status_code in (204, 200):
                self._writer_type = "v1_http"
                self._write_url = url_v1
                self._write_auth = auth
                self.logger.info(f"{self.name} Using v1 HTTP write endpoint to {url_v1}")
                return
            # Attempt to create database and retry
            if r.status_code in (404, 400) or (r.status_code >= 400 and r.content and b"database" in r.content.lower()):
                create_url = f"{base}/query"
                q = {"q": f"CREATE DATABASE {db}"}
                r2 = self._session.post(create_url, params=q, auth=auth, timeout=5)
                if r2.status_code == 200:
                    r3 = self._session.post(url_v1, params={"db": db}, data=test_line, auth=auth, timeout=5)
                    if r3.status_code in (204, 200):
                        self._writer_type = "v1_http"
                        self._write_url = url_v1
                        self._write_auth = auth
                        self.logger.info(f"{self.name} Created v1 database and will use v1 HTTP write to {url_v1}")
                        return
        except Exception as e:
            self.logger.debug(f"{self.name} v1 HTTP detection failed: {e}")

        # If we reach here, no writer was configured
        raise RuntimeError(f"{self.name} Initialization failed: could not determine writable endpoint or create database/bucket")

    def _to_line_protocol(self, measurement: str, tags: dict, fields: dict, timestamp: int) -> str:
        # Simple line protocol builder; timestamp in seconds converted to nanoseconds
        def esc(s: str) -> str:
            return str(s).replace(" ", "\\ ").replace(",", "\\,")

        tags_part = ",".join(f"{esc(k)}={esc(v)}" for k, v in tags.items()) if tags else ""

        def fmt_val(v):
            if isinstance(v, int):
                return f"{v}i"
            if isinstance(v, float):
                return f"{v}"
            return f'"{str(v).replace('"', '\\"')}"'

        fields_part = ",".join(f"{esc(k)}={fmt_val(v)}" for k, v in fields.items())
        ts_ns = int(timestamp) * 1_000_000_000
        return f"{esc(measurement)}{',' + tags_part if tags_part else ''} {fields_part} {ts_ns}"

    async def _write_line(self, line: str) -> None:
        # Write using the pre-configured writer (determined at init)
        try:
            if self._writer_type == "client" and self._writer_obj is not None:
                write_api = self._writer_obj.write_api(write_options=WriteOptions(batch_size=1))
                await asyncio.to_thread(write_api.write, bucket=self._writer_obj_bucket, org=self._writer_obj_org, record=line)
                return
            if self._writer_type == "v2_http" and self._write_url:
                r = await asyncio.to_thread(self._session.post, self._write_url, headers=self._write_headers or {}, data=line.encode("utf-8"), timeout=5)
                if r.status_code in (204, 200):
                    return
                else:
                    self.logger.error(f"InfluxDB v2 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url} line={line})")
            if self._writer_type == "v1_http" and self._write_url:
                r = await asyncio.to_thread(self._session.post, self._write_url, params={"db": Config.influxdb.database}, data=line.encode("utf-8"), auth=self._write_auth, timeout=5)
                if r.status_code in (204, 200):
                    return
                else:
                    self.logger.error(f"InfluxDB v1 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url} line={line})")
        except Exception as e:
            self.logger.error(f"InfluxDB write failed: {e} (type={self._writer_type} url={self._write_url} line={line})")

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: str | None, qos: int = 2) -> None:
        pass

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        pass

    def schedule(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        async def keep_running(modbus_client, mqtt_client, *sensors):
            self.logger.info(f"{self.name} Commenced")
            while self.online:
                try:
                    task = asyncio.create_task(asyncio.sleep(1))
                    self.sleeper_task = task
                    await task
                except asyncio.CancelledError:
                    self.logger.debug(f"{self.name} sleep interrupted")
                    break
                finally:
                    self.sleeper_task = None

            for topic in self._topic_cache.keys():
                mqtt_client.unsubscribe(topic)
            self.logger.info(f"{self.name} Unsubscribed from {len(self._topic_cache)} topics")

            self.logger.info(f"{self.name} Completed: Flagged as offline ({self.online=})")

        return [keep_running(modbus_client, mqtt_client, [])]

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        devices = DeviceRegistry.get(self.plant_index)
        if not devices:
            return
        for device in devices:
            try:
                for s in device.get_all_sensors().values():
                    obj: str = cast(str, s["object_id"])
                    uid: str = cast(str, getattr(s, "unique_id"))
                    tpc: str = cast(str, getattr(s, "state_topic"))

                    if not getattr(s, "publishable", False):
                        self.logger.info(f"{self.name} [{tpc}] Skipping because object_id '{obj}' is not publishable")
                        continue

                    if Config.influxdb.include and not any(ident in obj or ident in uid for ident in Config.influxdb.include):
                        self.logger.info(f"{self.name} [{tpc}] Skipping because object_id '{obj}' is not in include list")
                        continue
                    if Config.influxdb.exclude and any(ident in obj or ident in uid for ident in Config.influxdb.exclude):
                        self.logger.info(f"{self.name} [{tpc}] Skipping because object_id '{obj}' is excluded")
                        continue

                    self._topic_cache[tpc] = {"uom": s["unit_of_measurement"] if s["unit_of_measurement"] else "state", "object_id": obj, "unique_id": uid, "debug_logging": s.debug_logging}
                    mqtt_handler.register(mqtt_client, tpc, self.handle_mqtt)
            except Exception:
                continue
        self.logger.info(f"{self.name} Subscribed to {len(self._topic_cache)} topics")

    async def handle_mqtt(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, payload: str, topic: str, mqtt_handler: MqttHandler) -> bool:
        try:
            sensor = self._topic_cache.get(topic)
            if not sensor:
                self.logger.warning(f"{self.name} Received update for unknown topic '{topic}' (no cache entry)")
                return False

            timestamp = int(time.time())
            tags: dict[str, str] = {}
            fields: dict[str, int | float | str] = {}
            measurement = cast(str, sensor.get("uom")).replace("/", "_")

            try:
                fv = float(payload)
                fields["value"] = fv
            except Exception:
                fields["value_str"] = payload
            tags["entity_id"] = cast(str, sensor.get("object_id"))

            line = self._to_line_protocol(measurement, tags, fields, timestamp)
            if sensor.get("debug_logging"):
                self.logger.debug(f"{self.name} [{topic}] Writing line protocol: {line}")
            await self._write_line(line)
        except Exception as e:
            self.logger.error(f"{self.name} Failed to handle MQTT message from {topic}: {e}")
            return False
        return True
