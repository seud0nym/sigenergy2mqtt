from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any, Awaitable, Callable, Iterable, List
import logging
import asyncio
import requests
try:
    from influxdb_client import InfluxDBClient, Point, WriteOptions
    HAS_INFLUX_CLIENT = True
except Exception:
    HAS_INFLUX_CLIENT = False
import time
import json


class InfluxService(Device):
    def __init__(self, logger: logging.Logger):
        super().__init__("InfluxDB Updater Service", -1, "influxdb_updater", "sigenergy2mqtt", "InfluxDB.Updater", Config.protocol)
        self.logger = logger
        self._session = requests.Session()
        self._version = None
        self._base_url = None

    def publish_availability(self, mqtt: MqttClient, ha_state, qos=2) -> None:
        pass

    def publish_discovery(self, mqtt: MqttClient, clean=False) -> Any:
        pass

    def schedule(self, modbus: Any, mqtt: MqttClient) -> List[Callable[[Any, MqttClient, Iterable[Any]], Awaitable[None]]]:
        async def keep_running(modbus, mqtt, *sensors):
            self.logger.info(f"{self.__class__.__name__} Commenced")
            while self.online:
                await asyncio.sleep(1)
            self.logger.info(f"{self.__class__.__name__} Completed: Flagged as offline ({self.online=})")

        return [keep_running(modbus, mqtt)]

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        # Subscribe to all topics and handle messages
        mqtt_handler.register(mqtt, "#", self.handle_mqtt)

    async def handle_mqtt(self, modbus, client, payload: str, topic: str, mqtt_handler) -> None:
        try:
            # Find matching sensor (if any)
            sensor = None
            for plant_index in range(len(Config.devices)):
                devices = DeviceRegistry.get(plant_index)
                if not devices:
                    continue
                for device in devices:
                    for s in device.get_all_sensors().values():
                        if not getattr(s, "publishable", False):
                            continue
                        if s.state_topic == topic or s.raw_state_topic == topic or getattr(s, "json_attributes_topic", None) == topic:
                            sensor = s
                            break
                    if sensor:
                        break
                if sensor:
                    break

            # Check include/exclude using same substring logic as sensor_overrides
            if sensor:
                if Config.influxdb.include and not any(ident in sensor.__class__.__name__ or ident in sensor["object_id"] or ident in sensor.unique_id for ident in Config.influxdb.include):
                    self.logger.debug(f"InfluxDB: Skipping {sensor.unique_id} not in include list")
                    return
                if Config.influxdb.exclude and any(ident in sensor.__class__.__name__ or ident in sensor["object_id"] or ident in sensor.unique_id for ident in Config.influxdb.exclude):
                    self.logger.debug(f"InfluxDB: Skipping {sensor.unique_id} because excluded")
                    return

            value = payload
            timestamp = int(time.time())

            measurement = None
            tags = {}
            fields = {}

            if sensor:
                measurement = sensor["object_id"].replace("/", "_")
                # Determine numeric value when possible
                try:
                    fv = float(value)
                    fields["value"] = fv
                except Exception:
                    fields["value_str"] = value
                tags["sensor"] = sensor.unique_id
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
            return f'"{str(v).replace("\"", "\\\"")}"'

        fields_part = ",".join(f"{esc(k)}={fmt_val(v)}" for k, v in fields.items())
        ts_ns = int(timestamp) * 1_000_000_000
        return f"{esc(measurement)}{','+tags_part if tags_part else ''} {fields_part} {ts_ns}"

    def _write_line(self, line: str) -> None:
        # Lazy detect and write using common endpoints for InfluxDB v2 and v1 compatibility
        host = Config.influxdb.host
        port = Config.influxdb.port
        db = Config.influxdb.database
        user = Config.influxdb.username
        pwd = Config.influxdb.password
        base = f"http://{host}:{port}"
        headers = {}

        # Prefer official client when available (supports v2 and v3 where token-based)
        if HAS_INFLUX_CLIENT and pwd:
            try:
                org = None
                with InfluxDBClient(url=base, token=pwd, org=org) as client:
                    write_api = client.write_api(write_options=WriteOptions(batch_size=1))
                    # If bucket exists, write directly; client will throw on failure
                    write_api.write(bucket=db, org=org, record=line)
                    self.logger.debug("InfluxDB client write OK")
                    return
            except Exception:
                # Fall through to HTTP methods if client fails
                pass

        # Try v2 write endpoint using token in password
        try:
            url_v2 = f"{base}/api/v2/write?bucket={db}&precision=s"
            if pwd:
                headers["Authorization"] = f"Token {pwd}"
            r = self._session.post(url_v2, headers=headers, data=line.encode("utf-8"), timeout=5)
            if r.status_code in (204, 200):
                self.logger.debug(f"InfluxDB v2 write OK ({r.status_code}) to {url_v2}")
                return
        except Exception:
            pass

        # Try v1 write endpoint
        try:
            url_v1 = f"{base}/write"
            params = {"db": db}
            auth = (user, pwd) if user or pwd else None
            r = self._session.post(url_v1, params=params, data=line.encode("utf-8"), auth=auth, timeout=5)
            if r.status_code in (204, 200):
                self.logger.debug(f"InfluxDB v1 write OK ({r.status_code}) to {url_v1}")
                return
            # If database not found, attempt to create (v1)
            if r.status_code == 404 or (r.status_code >= 400 and b"database" in r.content.lower()):
                # Try to create database
                try:
                    create_url = f"{base}/query"
                    q = {"q": f"CREATE DATABASE {db}"}
                    r2 = self._session.post(create_url, params=q, auth=auth, timeout=5)
                    if r2.status_code == 200:
                        self.logger.info(f"Created InfluxDB v1 database '{db}'")
                        # Retry write
                        r3 = self._session.post(url_v1, params=params, data=line.encode("utf-8"), auth=auth, timeout=5)
                        if r3.status_code in (204, 200):
                            self.logger.debug("InfluxDB v1 write after create OK")
                            return
                except Exception:
                    pass
        except Exception:
            pass

        # Try v2 bucket create if token provided
        try:
            if pwd:
                url_buckets = f"{base}/api/v2/buckets?name={db}"
                headers = {"Authorization": f"Token {pwd}", "Content-Type": "application/json"}
                r = self._session.get(url_buckets, headers=headers, timeout=5)
                if r.status_code == 200 and r.json().get("buckets"):
                    # bucket exists, retry write
                    r2 = self._session.post(f"{base}/api/v2/write?bucket={db}&precision=s", headers={"Authorization": f"Token {pwd}"}, data=line.encode("utf-8"), timeout=5)
                    if r2.status_code in (204, 200):
                        self.logger.debug("InfluxDB v2 write OK after bucket confirm")
                        return
                # Create bucket using first org
                orgs = self._session.get(f"{base}/api/v2/orgs", headers=headers, timeout=5)
                if orgs.status_code == 200:
                    items = orgs.json().get("orgs") or orgs.json().get("orgs", [])
                    if not items:
                        items = orgs.json()
                    org_id = None
                    if isinstance(items, list) and len(items) > 0:
                        org_id = items[0].get("id")
                    elif isinstance(items, dict):
                        org_id = items.get("id")
                    if org_id:
                        create_bucket = {"name": db, "orgID": org_id}
                        r3 = self._session.post(f"{base}/api/v2/buckets", headers=headers, data=json.dumps(create_bucket), timeout=5)
                        if r3.status_code in (201, 200):
                            self.logger.info(f"Created InfluxDB v2 bucket '{db}'")
                            r4 = self._session.post(f"{base}/api/v2/write?bucket={db}&precision=s", headers={"Authorization": f"Token {pwd}"}, data=line.encode("utf-8"), timeout=5)
                            if r4.status_code in (204, 200):
                                self.logger.debug("InfluxDB v2 write OK after bucket create")
                                return
        except Exception:
            pass

        self.logger.error("Failed to write to InfluxDB using v2 or v1 endpoints")
