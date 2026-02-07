import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device
from sigenergy2mqtt.metrics.metrics import Metrics


class InfluxBase(Device):
    """Base class for InfluxDB integration providing connection, writing, and querying."""

    def __init__(self, name: str, plant_index: int, unique: str, manufacturer: str, model: str, logger: logging.Logger):
        super().__init__(name, plant_index, unique, manufacturer, model, Protocol.N_A)

        self.logger = logger
        urllib3 = logging.getLogger("urllib3")
        urllib3.setLevel(logging.INFO)
        urllib3.propagate = True

        self.plant_index = plant_index

        # Enhanced connection pooling with retry strategy
        self._session = requests.Session()
        retry_strategy = Retry(
            total=Config.influxdb.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(
            pool_connections=Config.influxdb.pool_connections,
            pool_maxsize=Config.influxdb.pool_maxsize,
            max_retries=retry_strategy,
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Cache mapping state_topic -> {uom, object_id, unique_id}
        self._topic_cache: dict[str, dict[str, Any]] = {}

        # Batch write buffer
        self._write_buffer: list[str] = []
        self._batch_size: int = Config.influxdb.batch_size
        self._batch_lock = asyncio.Lock()
        self._last_flush: float = time.time()
        self._flush_interval: float = Config.influxdb.flush_interval

        # Rate limiting for queries
        self._rate_limit_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent queries
        self._query_interval: float = Config.influxdb.query_interval
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

    def _init_connection(self) -> None:
        """Determine InfluxDB version/method and ensure target database/bucket exists."""
        config = self.get_config_values()
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

    async def async_init(self) -> bool:
        """Perform asynchronous initialization of InfluxDB connection."""
        if Config.influxdb.enabled:
            try:
                await asyncio.to_thread(self._init_connection)
                return True
            except Exception as e:
                self.logger.error(f"{self.name} Initialization failed: {e}")
                return False
        return True

    def get_config_values(self):
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

    def to_line_protocol(self, measurement: str, tags: dict, fields: dict, timestamp: int) -> str:
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
            success = await self.execute_write(batch_data)
            elapsed = time.time() - start
            if success:
                await Metrics.influxdb_write(batch_size, elapsed)
            else:
                await Metrics.influxdb_write_error()
        except Exception as e:
            self.logger.error(f"InfluxDB batch write failed: {e} (type={self._writer_type} url={self._write_url} batch_size={batch_size})")
            await Metrics.influxdb_write_error()

    async def write_line(self, line: str) -> None:
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

    async def execute_write(self, data: bytes) -> bool:
        """Execute the HTTP write to InfluxDB. Returns True on success."""
        if not self.online:
            return False

        try:
            if self._writer_type == "v2_http" and self._write_url:
                r = await asyncio.to_thread(self._session.post, self._write_url, headers=self._write_headers or {}, data=data, timeout=Config.influxdb.write_timeout)
                if r.status_code in (204, 200):
                    return True
                else:
                    self.logger.error(f"InfluxDB v2 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url})")
                    return False
            elif self._writer_type == "v1_http" and self._write_url:
                r = await asyncio.to_thread(self._session.post, self._write_url, params={"db": Config.influxdb.database}, data=data, auth=self._write_auth, timeout=Config.influxdb.write_timeout)
                if r.status_code in (204, 200):
                    return True
                else:
                    self.logger.error(f"InfluxDB v1 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url})")
                    return False
        except Exception as e:
            self.logger.error(f"InfluxDB write failed: {e} (type={self._writer_type} url={self._write_url})")
        return False

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
                if not self.online:
                    return False, None
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

    async def query_v2(self, base: str, org: str | None, token: str, flux_query: str, timeout: int | float | None = None, max_retries: int | None = None) -> tuple[bool, Any]:
        """Execute a Flux query on v2 API with retry and rate limiting. Returns (success, response_text)."""
        if timeout is None:
            timeout = Config.influxdb.read_timeout
        if max_retries is None:
            max_retries = Config.influxdb.max_retries
        return await self._rate_limited_query(
            lambda: self.query_v2_internal(base, org, token, flux_query, timeout),
            "v2 query",
            max_retries,
        )

    async def query_v2_internal(self, base: str, org: str | None, token: str, flux_query: str, timeout: int | float) -> tuple[bool, Any]:
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

    async def query_v1(self, base: str, db: str, auth: tuple | None, query: str, epoch: str | None = None, timeout: int | float | None = None, max_retries: int | None = None) -> tuple[bool, Any]:
        """Execute an InfluxQL query on v1 API with retry and rate limiting. Returns (success, json_result)."""
        if timeout is None:
            timeout = Config.influxdb.read_timeout
        if max_retries is None:
            max_retries = Config.influxdb.max_retries
        return await self._rate_limited_query(
            lambda: self.query_v1_internal(base, db, auth, query, epoch, timeout),
            "v1 query",
            max_retries,
        )

    async def query_v1_internal(self, base: str, db: str, auth: tuple | None, query: str, epoch: str | None, timeout: int | float) -> tuple[bool, Any]:
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

    def parse_timestamp(self, time_str: str) -> int:
        """Parse ISO timestamp string to Unix timestamp in seconds."""
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return int(dt.timestamp())

    def build_tag_filters(self, tags: dict[str, str]) -> dict[str, str]:
        """Build tag filter strings for v1 and v2 queries."""
        v1_filter = " AND ".join([f"\"{k}\"='{v}'" for k, v in tags.items()]) if tags else ""
        return {"v1": v1_filter}
