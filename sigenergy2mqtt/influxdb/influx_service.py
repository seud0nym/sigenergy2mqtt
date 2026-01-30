import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Awaitable, cast

import paho.mqtt.client as mqtt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.metrics.metrics import Metrics
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

        # Enhanced connection pooling with retry strategy
        self._session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Cache mapping state_topic -> {uom, object_id, unique_id}
        self._topic_cache: dict[str, dict[str, Any]] = {}

        # Batch write buffer
        self._write_buffer: list[str] = []
        self._batch_size: int = 100  # Batch threshold
        self._batch_lock = asyncio.Lock()
        self._last_flush: float = time.time()
        self._flush_interval: float = 1.0  # Flush every 1 second even if batch not full

        # Rate limiting for queries
        self._rate_limit_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent queries
        self._query_interval: float = 0.1  # Minimum 100ms between queries
        self._last_query_time: float = 0.0
        self._query_lock = asyncio.Lock()

        # Only attempt to initialize connection when InfluxDB is enabled in config
        # Otherwise set defaults so unit tests can instantiate without network
        self._writer_type = None
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

    def _get_config_values(self):
        """Extract InfluxDB configuration values with backwards compatibility."""
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
        auth = (user, pwd) if user or pwd else None

        return {"host": host, "port": port, "db": db, "user": user, "pwd": pwd, "token": token, "org": org, "bucket": bucket, "base": base, "auth": auth}

    def _try_v2_write(self, base: str, bucket: str, org: str | None, token: str | None, test_line: bytes) -> bool:
        """Attempt to write using v2 HTTP endpoint."""
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
                return True

            # If bucket not found and token provided, attempt to create it
            if r.status_code in (400, 404) and token:
                if self._create_v2_bucket(base, bucket, token):
                    # Retry write after creating bucket
                    r3 = self._session.post(url_v2, headers=headers or None, data=test_line, timeout=5)
                    if r3.status_code in (204, 200):
                        self._writer_type = "v2_http"
                        self._write_url = url_v2
                        self._write_headers = headers or {}
                        self.logger.info(f"{self.name} Created v2 bucket and will use v2 HTTP write to {url_v2}")
                        return True
        except Exception as e:
            self.logger.debug(f"{self.name} v2 HTTP detection failed: {e}")

        return False

    def _create_v2_bucket(self, base: str, bucket: str, token: str) -> bool:
        """Create a v2 bucket and return True if successful."""
        try:
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
                    return r2.status_code in (201, 200)
        except Exception as e:
            self.logger.debug(f"{self.name} v2 bucket creation failed: {e}")
        return False

    def _try_v1_write(self, base: str, db: str, auth: tuple | None, test_line: bytes) -> bool:
        """Attempt to write using v1 HTTP endpoint."""
        try:
            url_v1 = f"{base}/write"
            r = self._session.post(url_v1, params={"db": db}, data=test_line, auth=auth, timeout=5)
            if r.status_code in (204, 200):
                self._writer_type = "v1_http"
                self._write_url = url_v1
                self._write_auth = auth
                self.logger.info(f"{self.name} Using v1 HTTP write endpoint to {url_v1}")
                return True

            # Attempt to create database and retry
            if r.status_code in (404, 400) or (r.status_code >= 400 and r.content and b"database" in r.content.lower()):
                if self._create_v1_database(base, db, auth):
                    # Retry write after creating database
                    r3 = self._session.post(url_v1, params={"db": db}, data=test_line, auth=auth, timeout=5)
                    if r3.status_code in (204, 200):
                        self._writer_type = "v1_http"
                        self._write_url = url_v1
                        self._write_auth = auth
                        self.logger.info(f"{self.name} Created v1 database and will use v1 HTTP write to {url_v1}")
                        return True
        except Exception as e:
            self.logger.debug(f"{self.name} v1 HTTP detection failed: {e}")

        return False

    def _create_v1_database(self, base: str, db: str, auth: tuple | None) -> bool:
        """Create a v1 database and return True if successful."""
        try:
            create_url = f"{base}/query"
            q = {"q": f"CREATE DATABASE {db}"}
            r2 = self._session.post(create_url, params=q, auth=auth, timeout=5)
            return r2.status_code == 200
        except Exception as e:
            self.logger.debug(f"{self.name} v1 database creation failed: {e}")
        return False

    def _init_connection(self) -> None:
        """Determine InfluxDB version/method and ensure target database/bucket exists."""
        config = self._get_config_values()
        test_line = b"state value=1"

        # Try v2 HTTP write endpoint (preferred if token provided)
        if config["token"]:
            if self._try_v2_write(config["base"], config["bucket"], config["org"], config["token"], test_line):
                return

        # If username is provided, prefer v1 HTTP (InfluxDB 1.x)
        if config["user"]:
            if self._try_v1_write(config["base"], config["db"], config["auth"], test_line):
                return

        # Try v2 without token (some setups)
        if not self._writer_type:
            if self._try_v2_write(config["base"], config["bucket"], config["org"], None, test_line):
                return

        # Final fallback: try v1 HTTP without username (no auth)
        if not self._writer_type:
            if self._try_v1_write(config["base"], config["db"], config["auth"], test_line):
                return

        # If we reach here, no writer was configured
        raise RuntimeError(f"{self.name} Initialization failed: could not determine writable endpoint or create database/bucket")

    def _to_line_protocol(self, measurement: str, tags: dict, fields: dict, timestamp: int) -> str:
        """Build line protocol string from measurement, tags, fields, and timestamp."""

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
        """Add line to write buffer. Flushes buffer when threshold reached or interval exceeded."""
        async with self._batch_lock:
            self._write_buffer.append(line)
            should_flush = len(self._write_buffer) >= self._batch_size or (time.time() - self._last_flush) >= self._flush_interval
            if should_flush:
                await self._flush_buffer_internal()

    async def flush_buffer(self) -> None:
        """Public method to flush any pending writes."""
        async with self._batch_lock:
            await self._flush_buffer_internal()

    async def _flush_buffer_internal(self) -> None:
        """Flush buffered writes to InfluxDB. Must be called within _batch_lock."""
        if not self._write_buffer:
            return

        batch = self._write_buffer
        self._write_buffer = []
        self._last_flush = time.time()

        batch_data = "\n".join(batch).encode("utf-8")
        batch_size = len(batch)
        start = time.time()

        try:
            success = await self._execute_write(batch_data)
            elapsed = time.time() - start
            if success:
                await Metrics.influxdb_write(batch_size, elapsed)
            else:
                await Metrics.influxdb_write_error()
        except Exception as e:
            self.logger.error(f"InfluxDB batch write failed: {e} (type={self._writer_type} url={self._write_url} batch_size={batch_size})")
            await Metrics.influxdb_write_error()

    async def _execute_write(self, data: bytes) -> bool:
        """Execute the HTTP write to InfluxDB. Returns True on success."""
        try:
            if self._writer_type == "v2_http" and self._write_url:
                r = await asyncio.to_thread(self._session.post, self._write_url, headers=self._write_headers or {}, data=data, timeout=5)
                if r.status_code in (204, 200):
                    return True
                else:
                    self.logger.error(f"InfluxDB v2 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url})")
                    return False
            elif self._writer_type == "v1_http" and self._write_url:
                r = await asyncio.to_thread(self._session.post, self._write_url, params={"db": Config.influxdb.database}, data=data, auth=self._write_auth, timeout=5)
                if r.status_code in (204, 200):
                    return True
                else:
                    self.logger.error(f"InfluxDB v1 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url})")
                    return False
        except Exception as e:
            self.logger.error(f"InfluxDB write failed: {e} (type={self._writer_type} url={self._write_url})")
        return False

    async def _query_v2(self, base: str, org: str | None, token: str, flux_query: str, timeout: int = 10, max_retries: int = 3) -> tuple[bool, Any]:
        """Execute a Flux query on v2 API with retry and rate limiting. Returns (success, response_text)."""
        return await self._rate_limited_query(
            lambda: self._query_v2_internal(base, org, token, flux_query, timeout),
            "v2 query",
            max_retries,
        )

    async def _query_v2_internal(self, base: str, org: str | None, token: str, flux_query: str, timeout: int) -> tuple[bool, Any]:
        """Internal v2 query execution."""
        headers = {"Authorization": f"Token {token}", "Content-Type": "application/vnd.flux"}
        url = f"{base}/api/v2/query"
        params = {"org": org} if org else {}
        start = time.time()
        r = await asyncio.to_thread(self._session.post, url, headers=headers, params=params, data=flux_query, timeout=timeout)
        elapsed = time.time() - start
        if r.status_code == 200:
            await Metrics.influxdb_query(elapsed)
            return True, r.text
        raise Exception(f"HTTP {r.status_code}: {r.text}")

    async def _query_v1(self, base: str, db: str, auth: tuple | None, query: str, epoch: str | None = None, timeout: int = 10, max_retries: int = 3) -> tuple[bool, Any]:
        """Execute an InfluxQL query on v1 API with retry and rate limiting. Returns (success, json_result)."""
        return await self._rate_limited_query(
            lambda: self._query_v1_internal(base, db, auth, query, epoch, timeout),
            "v1 query",
            max_retries,
        )

    async def _query_v1_internal(self, base: str, db: str, auth: tuple | None, query: str, epoch: str | None, timeout: int) -> tuple[bool, Any]:
        """Internal v1 query execution."""
        url = f"{base}/query"
        params = {"db": db, "q": query}
        if epoch:
            params["epoch"] = epoch
        start = time.time()
        r = await asyncio.to_thread(self._session.get, url, params=params, auth=auth, timeout=timeout)
        elapsed = time.time() - start
        if r.status_code == 200:
            await Metrics.influxdb_query(elapsed)
            return True, r.json()
        raise Exception(f"HTTP {r.status_code}: {r.text}")

    async def _rate_limited_query(self, query_func, operation_name: str, max_retries: int = 3, base_delay: float = 0.5) -> tuple[bool, Any]:
        """Execute query with rate limiting and exponential backoff retry."""
        async with self._rate_limit_semaphore:
            # Apply rate limiting delay
            async with self._query_lock:
                now = time.time()
                wait_time = max(0.0, self._query_interval - (now - self._last_query_time))
                if wait_time > 0:
                    await Metrics.influxdb_rate_limit_wait()
                    await asyncio.sleep(wait_time)
                self._last_query_time = time.time()

            # Execute with retry logic
            for attempt in range(max_retries + 1):
                try:
                    return await query_func()
                except Exception as e:
                    if attempt == max_retries:
                        self.logger.debug(f"{self.name} {operation_name} failed after {max_retries + 1} attempts: {e}")
                        await Metrics.influxdb_query_error()
                        return False, None
                    delay = base_delay * (2**attempt)
                    self.logger.debug(f"{self.name} {operation_name} attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await Metrics.influxdb_retry()
                    await asyncio.sleep(delay)
        return False, None

    def _parse_timestamp(self, time_str: str) -> int:
        """Parse ISO timestamp string to Unix timestamp in seconds."""
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return int(dt.timestamp())

    def _build_tag_filters(self, tags: dict[str, str]) -> dict[str, str]:
        """Build tag filter strings for v1 and v2 queries."""
        v1_filter = " AND ".join([f"\"{k}\"='{v}'" for k, v in tags.items()]) if tags else ""
        return {"v1": v1_filter}

    async def detect_homeassistant_db(self) -> bool:
        """
        Detect if a 'homeassistant' database exists on the same InfluxDB server.
        Returns True if found, False otherwise.
        """
        try:
            config = self._get_config_values()

            # Try v2 API first (if token available)
            if config["token"]:
                try:
                    headers = {"Authorization": f"Token {config['token']}"}
                    url = f"{config['base']}/api/v2/buckets"
                    r = await asyncio.to_thread(self._session.get, url, headers=headers, timeout=5)
                    if r.status_code == 200:
                        buckets = r.json()
                        if isinstance(buckets, dict) and "buckets" in buckets:
                            for bucket in buckets["buckets"]:
                                if bucket.get("name") == "homeassistant":
                                    self.logger.info(f"{self.name} Found 'homeassistant' bucket in InfluxDB v2")
                                    return True
                except Exception as e:
                    self.logger.debug(f"{self.name} v2 bucket detection failed: {e}")

            # Try v1 API
            success, result = await self._query_v1(config["base"], config["db"], config["auth"], "SHOW DATABASES", timeout=5)
            if success and result:
                if "results" in result and result["results"]:
                    series = result["results"][0].get("series", [])
                    if series and "values" in series[0]:
                        databases = [db[0] for db in series[0]["values"]]
                        if "homeassistant" in databases:
                            self.logger.info(f"{self.name} Found 'homeassistant' database in InfluxDB v1")
                            return True

            self.logger.info(f"{self.name} 'homeassistant' database/bucket not found")
            return False

        except Exception as e:
            self.logger.error(f"{self.name} Error detecting homeassistant database: {e}")
            return False

    async def get_earliest_timestamp(self, measurement: str, tags: dict[str, str]) -> int | None:
        """
        Get the earliest timestamp for a given measurement and tag combination in the target database.
        Returns timestamp in seconds, or None if no records exist.
        """
        try:
            config = self._get_config_values()
            tag_filters = self._build_tag_filters(tags)

            # Try v2 API (Flux query)
            if config["token"]:
                flux_query = f'from(bucket: "{config["bucket"]}")\n  |> range(start: 0)\n  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
                for k, v in tags.items():
                    flux_query += f'  |> filter(fn: (r) => r.{k} == "{v}")\n'
                flux_query += '  |> first()\n  |> yield(name: "earliest")\n'

                success, response_text = await self._query_v2(config["base"], config["org"], config["token"], flux_query)
                if success and response_text:
                    lines = response_text.strip().split("\n")
                    for line in lines:
                        if line.startswith("_") or not line.strip():
                            continue
                        parts = line.split(",")
                        if len(parts) > 5:
                            time_str = parts[5].strip()
                            if time_str and time_str != "_time":
                                timestamp = self._parse_timestamp(time_str)
                                self.logger.debug(f"{self.name} Found earliest timestamp {timestamp} for {measurement} with tags {tags}")
                                return timestamp
                    return None

            # Try v1 API (InfluxQL)
            where_clause = f"WHERE {tag_filters['v1']}" if tag_filters["v1"] else ""
            query = f'SELECT * FROM "{measurement}" {where_clause} ORDER BY time ASC LIMIT 1'
            success, result = await self._query_v1(config["base"], config["db"], config["auth"], query)
            if success and result:
                if "results" in result and result["results"]:
                    series = result["results"][0].get("series", [])
                    if series and "values" in series[0] and series[0]["values"]:
                        time_str = series[0]["values"][0][0]
                        timestamp = self._parse_timestamp(time_str)
                        self.logger.debug(f"{self.name} Found earliest timestamp {timestamp} for {measurement} with tags {tags}")
                        return timestamp

            return None

        except Exception as e:
            self.logger.error(f"{self.name} Error getting earliest timestamp: {e}")
            return None

    async def _copy_records_v2(self, config: dict, measurement: str, tags: dict[str, str], before_timestamp: int | None) -> int:
        """Copy records using v2 API."""
        records_copied = 0
        time_filter = f"stop: time(v: {before_timestamp})" if before_timestamp else "start: 0"

        flux_query = f'from(bucket: "homeassistant")\n  |> range({time_filter})\n  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
        for k, v in tags.items():
            flux_query += f'  |> filter(fn: (r) => r.{k} == "{v}")\n'
        flux_query += '  |> yield(name: "records")\n'

        success, response_text = await self._query_v2(config["base"], config["org"], config["token"], flux_query, timeout=30)
        if not success or not response_text:
            return 0

        # Parse CSV response and convert to line protocol
        lines = response_text.strip().split("\n")
        headers_parsed = False
        header_indices = {}

        for line in lines:
            if not line.strip():
                continue

            if not headers_parsed:
                if line.startswith("_"):
                    parts = line.split(",")
                    for i, part in enumerate(parts):
                        header_indices[part.strip()] = i
                    headers_parsed = True
                continue

            parts = line.split(",")
            if len(parts) <= 1:
                continue

            # Extract timestamp
            time_idx = header_indices.get("_time", 5)
            time_str = parts[time_idx].strip() if time_idx < len(parts) else None
            if not time_str:
                continue

            timestamp = self._parse_timestamp(time_str)

            # Extract field and value
            field_idx = header_indices.get("_field", 6)
            value_idx = header_indices.get("_value", 7)

            field_name = parts[field_idx].strip() if field_idx < len(parts) else "value"
            field_value = parts[value_idx].strip() if value_idx < len(parts) else None

            if field_value is None:
                continue

            # Build fields dict
            fields = {}
            try:
                fields[field_name] = float(field_value)
            except Exception:
                fields[field_name] = field_value

            # Write the record
            line_protocol = self._to_line_protocol(measurement, tags, fields, timestamp)
            await self._write_line(line_protocol)
            records_copied += 1

        return records_copied

    async def _copy_records_v1(self, config: dict, measurement: str, tags: dict[str, str], before_timestamp: int | None) -> int:
        """Copy records using v1 API."""
        records_copied = 0
        tag_filters = self._build_tag_filters(tags)

        where_parts = []
        if tag_filters["v1"]:
            where_parts.append(tag_filters["v1"])
        if before_timestamp:
            where_parts.append(f"time < {before_timestamp}s")

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        query = f'SELECT * FROM "{measurement}" {where_clause} ORDER BY time ASC'

        success, result = await self._query_v1(config["base"], "homeassistant", config["auth"], query, epoch="s", timeout=30)
        if not success or not result:
            return 0

        if "results" in result and result["results"]:
            series = result["results"][0].get("series", [])
            for s in series:
                if "values" not in s or "columns" not in s:
                    continue

                columns = s["columns"]
                time_idx = columns.index("time") if "time" in columns else 0

                for row in s["values"]:
                    timestamp = int(row[time_idx])

                    # Build fields from non-time, non-tag columns
                    fields = {}
                    for i, col in enumerate(columns):
                        if col == "time" or col in tags:
                            continue
                        if row[i] is not None:
                            fields[col] = row[i]

                    if not fields:
                        continue

                    # Write the record
                    line_protocol = self._to_line_protocol(measurement, tags, fields, timestamp)
                    await self._write_line(line_protocol)
                    records_copied += 1

        return records_copied

    async def copy_records_from_homeassistant(self, measurement: str, tags: dict[str, str], before_timestamp: int | None = None) -> int:
        """
        Copy records from 'homeassistant' database with the same measurement and tags.
        If before_timestamp is provided, only copy records with timestamps earlier than it.
        If before_timestamp is None, copy all records for that measurement/tag combination.
        Returns the number of records copied.
        """
        try:
            config = self._get_config_values()
            records_copied = 0

            # Try v2 API first
            if config["token"]:
                records_copied = await self._copy_records_v2(config, measurement, tags, before_timestamp)
                if records_copied > 0:
                    self.logger.info(f"{self.name} Copied {records_copied} records from homeassistant (v2) for {measurement} with tags {tags}")
                    return records_copied

            # Try v1 API
            records_copied = await self._copy_records_v1(config, measurement, tags, before_timestamp)
            if records_copied > 0:
                self.logger.info(f"{self.name} Copied {records_copied} records from homeassistant (v1) for {measurement} with tags {tags}")

            return records_copied

        except Exception as e:
            self.logger.error(f"{self.name} Error copying records from homeassistant: {e}")
            return 0

    async def sync_from_homeassistant(self) -> dict[str, int]:
        """
        Main method to detect homeassistant database and sync all cached measurements.
        Returns a dict mapping measurement/tag combinations to number of records copied.
        """
        results = {}

        # First check if homeassistant database exists
        if not await self.detect_homeassistant_db():
            self.logger.info(f"{self.name} No homeassistant database found, skipping sync")
            return results

        self.logger.info(f"{self.name} Starting sync from homeassistant database")

        # Iterate through cached topics to get unique measurement/tag combinations
        seen_combinations = set()

        for topic, sensor in self._topic_cache.items():
            measurement = cast(str, sensor.get("uom", "state")).replace("/", "_")
            tags = {"entity_id": cast(str, sensor.get("object_id"))}

            # Create a hashable key for this combination
            combo_key = (measurement, tuple(sorted(tags.items())))
            if combo_key in seen_combinations:
                continue
            seen_combinations.add(combo_key)

            # Get earliest timestamp in target database
            earliest_ts = await self.get_earliest_timestamp(measurement, tags)

            # Copy records from homeassistant
            if earliest_ts is None:
                self.logger.info(f"{self.name} No existing records for {measurement}/{tags}, copying all from homeassistant")
                count = await self.copy_records_from_homeassistant(measurement, tags, before_timestamp=None)
            else:
                self.logger.info(f"{self.name} Found earliest timestamp {earliest_ts} for {measurement}/{tags}, copying older records")
                count = await self.copy_records_from_homeassistant(measurement, tags, before_timestamp=earliest_ts)

            result_key = f"{measurement}[{','.join(f'{k}={v}' for k, v in tags.items())}]"
            results[result_key] = count

        total_copied = sum(results.values())
        self.logger.info(f"{self.name} Sync complete: copied {total_copied} total records across {len(results)} measurement/tag combinations")

        return results

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
