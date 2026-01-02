from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import WriteOptions
from sigenergy2mqtt.config import Config, Protocol
from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any, Awaitable, List
import asyncio
import json
import logging
import requests
import time


class InfluxService(Device):
    def __init__(self, logger: logging.Logger, plant_index: int = -1):
        # Create one service instance per plant_index so each caches its own sensors
        name = f"InfluxDB Updater Service (plant {plant_index})"
        unique = f"influxdb_updater_{plant_index}"
        super().__init__(name, plant_index, unique, "sigenergy2mqtt", "InfluxDB.Updater", Protocol.N_A)
        self.logger = logger
        self.plant_index = plant_index
        self._session = requests.Session()
        self._version = None
        self._base_url = None
        # Cache mapping state_topic -> {uom, object_id, unique_id}
        self._topic_cache: dict[str, dict] = {}
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
                self.logger.error(f"InfluxDB initialization failed during service init: {e}")
                raise

    def _init_connection(self) -> None:
        # Determine InfluxDB version/method and ensure target database/bucket exists.
        host = Config.influxdb.host
        port = Config.influxdb.port
        db = Config.influxdb.database
        user = Config.influxdb.username
        pwd = Config.influxdb.password
        base = f"http://{host}:{port}"

        # 1) Prefer official client when token provided
        if pwd:
            try:
                client = InfluxDBClient(url=base, token=pwd)
                # Try a write to the target bucket (may raise)
                write_api = client.write_api(write_options=WriteOptions(batch_size=1))
                test_line = b"_sigenergy_init value=1"
                try:
                    # Include `org=None` to match the signature of test dummies
                    write_api.write(bucket=db, org=None, record=test_line)
                except Exception:
                    client.close()
                    raise
                self._writer_type = "client"
                self._writer_obj = client
                self._writer_obj_bucket = db
                self._writer_obj_org = None
                self.logger.info("InfluxDB: using official client for writes")
                return
            except Exception as e:
                self.logger.debug(f"InfluxDB client detection/initial write failed: {e}")

        # 2) Try v2 HTTP write endpoint (uses token in password)
        try:
            url_v2 = f"{base}/api/v2/write?bucket={db}&precision=s"
            headers = {}
            if pwd:
                headers["Authorization"] = f"Token {pwd}"
            r = self._session.post(url_v2, headers=headers, data=b"_sigenergy_init value=1", timeout=5)
            if r.status_code in (204, 200):
                self._writer_type = "v2_http"
                self._write_url = url_v2
                self._write_headers = headers
                self.logger.info("InfluxDB: using v2 HTTP write endpoint")
                return
            # If bucket not found, attempt to create it (requires token)
            if r.status_code in (400, 404) and pwd:
                headers_create = {"Authorization": f"Token {pwd}", "Content-Type": "application/json"}
                orgs = self._session.get(f"{base}/api/v2/orgs", headers=headers_create, timeout=5)
                if orgs.status_code == 200:
                    items = orgs.json()
                    org_id = None
                    if isinstance(items, dict) and items.get("orgs"):
                        lst = items.get("orgs")
                        if isinstance(lst, list) and lst:
                            org_id = lst[0].get("id")
                    if org_id:
                        create_bucket = {"name": db, "orgID": org_id}
                        r2 = self._session.post(f"{base}/api/v2/buckets", headers=headers_create, data=json.dumps(create_bucket), timeout=5)
                        if r2.status_code in (201, 200):
                            # retry write
                            r3 = self._session.post(url_v2, headers=headers, data=b"_sigenergy_init value=1", timeout=5)
                            if r3.status_code in (204, 200):
                                self._writer_type = "v2_http"
                                self._write_url = url_v2
                                self._write_headers = headers
                                self.logger.info("InfluxDB: created v2 bucket and will use v2 HTTP write")
                                return
        except Exception as e:
            self.logger.debug(f"InfluxDB v2 HTTP detection failed: {e}")

        # 3) Try v1 HTTP write endpoint
        try:
            url_v1 = f"{base}/write"
            auth = (user, pwd) if user or pwd else None
            r = self._session.post(url_v1, params={"db": db}, data=b"_sigenergy_init value=1", auth=auth, timeout=5)
            if r.status_code in (204, 200):
                self._writer_type = "v1_http"
                self._write_url = url_v1
                self._write_auth = auth
                self.logger.info("InfluxDB: using v1 HTTP write endpoint")
                return
            # Attempt to create database and retry
            if r.status_code in (404, 400) or (r.status_code >= 400 and b"database" in r.content.lower() if r.content else False):
                create_url = f"{base}/query"
                q = {"q": f"CREATE DATABASE {db}"}
                r2 = self._session.post(create_url, params=q, auth=auth, timeout=5)
                if r2.status_code == 200:
                    r3 = self._session.post(url_v1, params={"db": db}, data=b"_sigenergy_init value=1", auth=auth, timeout=5)
                    if r3.status_code in (204, 200):
                        self._writer_type = "v1_http"
                        self._write_url = url_v1
                        self._write_auth = auth
                        self.logger.info("InfluxDB: created v1 database and will use v1 HTTP write")
                        return
        except Exception as e:
            self.logger.debug(f"InfluxDB v1 HTTP detection failed: {e}")

        # If we reach here, no writer was configured
        raise RuntimeError("InfluxDB initialization failed: could not determine writable endpoint or create database/bucket")

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

    def _write_line(self, line: str) -> None:
        # Write using the pre-configured writer (determined at init)
        try:
            if self._writer_type == "client" and self._writer_obj is not None:
                write_api = self._writer_obj.write_api(write_options=WriteOptions(batch_size=1))
                write_api.write(bucket=self._writer_obj_bucket, org=self._writer_obj_org, record=line)
                return
            if self._writer_type == "v2_http" and self._write_url:
                r = self._session.post(self._write_url, headers=self._write_headers or {}, data=line.encode("utf-8"), timeout=5)
                if r.status_code in (204, 200):
                    return
            if self._writer_type == "v1_http" and self._write_url:
                r = self._session.post(self._write_url, params={"db": Config.influxdb.database}, data=line.encode("utf-8"), auth=self._write_auth, timeout=5)
                if r.status_code in (204, 200):
                    return
        except Exception as e:
            self.logger.error(f"InfluxDB write failed: {e}")

        self.logger.error("Failed to write to InfluxDB using configured writer")

    def publish_availability(self, mqtt: MqttClient, ha_state, qos=2) -> None:
        pass

    def publish_discovery(self, mqtt: MqttClient, clean=False) -> Any:
        pass

    def schedule(self, modbus: Any, mqtt: MqttClient) -> List[Awaitable[None]]:
        async def keep_running(modbus, mqtt, *sensors):
            self.logger.info(f"{self.__class__.__name__} Commenced")
            while self.online:
                await asyncio.sleep(1)
            self.logger.info(f"{self.__class__.__name__} Completed: Flagged as offline ({self.online=})")

        return [keep_running(modbus, mqtt, [])]

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        # Subscribe only to sensors' state_topic when a unit_of_measurement is defined
        devices = DeviceRegistry.get(self.plant_index)
        if not devices:
            return
        for device in devices:
            try:
                for s in device.get_all_sensors().values():
                    if not getattr(s, "publishable", False):
                        continue
                    # subscribe to state_topic only when unit_of_measurement exists
                    try:
                        uom = s["unit_of_measurement"]
                    except Exception:
                        uom = None
                    # Cache sensor metadata keyed by state_topic for fast lookup during updates
                    try:
                        obj = s["object_id"]
                    except Exception:
                        obj = None
                    self._topic_cache[s.state_topic] = {"uom": uom, "object_id": obj, "unique_id": s.unique_id}
                    if uom:
                        mqtt_handler.register(mqtt, s.state_topic, self.handle_mqtt)
            except Exception:
                # Ignore devices we can't iterate
                continue

    async def handle_mqtt(self, modbus, client, payload: str, topic: str, mqtt_handler) -> None:
        try:
            # Fast path: check cache keyed by state_topic. If missing, skip early.
            cache_entry = self._topic_cache.get(topic)
            if not cache_entry:
                self.logger.warning(f"InfluxDB: Received update for unknown topic '{topic}' (no cache entry) - skipping")
                return

            # Check include/exclude using same substring logic as sensor_overrides
            if cache_entry:
                # Apply include/exclude using cached object_id and unique_id
                obj = cache_entry.get("object_id") or ""
                uid = cache_entry.get("unique_id") or ""
                if Config.influxdb.include and not any(ident in obj or ident in uid for ident in Config.influxdb.include):
                    self.logger.debug(f"InfluxDB: Skipping {uid} not in include list")
                    return
                if Config.influxdb.exclude and any(ident in obj or ident in uid for ident in Config.influxdb.exclude):
                    self.logger.debug(f"InfluxDB: Skipping {uid} because excluded")
                    return

            value = payload
            timestamp = int(time.time())

            measurement = None
            tags = {}
            fields = {}

            if cache_entry:
                measurement = cache_entry.get("uom") or cache_entry.get("object_id")
                measurement = str(measurement).replace("/", "_") if measurement else topic.replace("/", "_")
                # Determine numeric value when possible
                try:
                    fv = float(value)
                    fields["value"] = fv
                except Exception:
                    fields["value_str"] = value
                tags["object_id"] = cache_entry.get("object_id")
                tags["sensor"] = cache_entry.get("unique_id")
            else:
                measurement = topic.replace("/", "_")
                try:
                    fv = float(value)
                    fields["value"] = fv
                except Exception:
                    fields["value_str"] = value

            line = self._to_line_protocol(measurement, tags, fields, timestamp)
            await asyncio.get_event_loop().run_in_executor(None, self._write_line, line)
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__} Failed to handle mqtt message: {e}")
