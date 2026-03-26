import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, TypedDict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.metrics import Metrics

# Suppress verbose urllib3 connection logs at module level rather than per-instance,
# since the logger is a global singleton and mutating it in __init__ has side-effects.
logging.getLogger("urllib3").setLevel(logging.INFO)


class InfluxConfigValues(TypedDict):
    """Typed dictionary for resolved InfluxDB configuration values."""

    host: str
    port: int
    db: str
    user: str | None
    pwd: str | None
    token: str | None
    org: str | None
    bucket: str
    base: str
    auth: tuple[str, str] | None


class InfluxBase(Device):
    """Base class for InfluxDB integration.

    Provides HTTP connection management, line-protocol serialisation, batched
    writes, and rate-limited querying for both InfluxDB v1 (InfluxQL) and v2
    (Flux) APIs.  Subclasses are expected to call :meth:`async_init` before
    issuing any write or query calls.
    """

    def __init__(
        self,
        name: str,
        plant_index: int,
        unique: str,
        manufacturer: str,
        model: str,
        logger: logging.Logger,
    ) -> None:
        """Initialise shared state, HTTP session, and write/query buffers.

        No network I/O is performed here; call :meth:`async_init` to establish
        the InfluxDB connection asynchronously.

        Args:
            name: Human-readable service name used in log messages.
            plant_index: Zero-based index of the Modbus plant this instance serves.
            unique: Unique identifier string passed to the parent :class:`Device`.
            manufacturer: Manufacturer string for device registration.
            model: Model string for device registration.
            logger: Pre-configured logger to use for all output.
        """
        super().__init__(name, plant_index, unique, manufacturer, model, Protocol.N_A)

        self.logger = logger
        self.plant_index = plant_index

        # Enhanced connection pooling with retry strategy
        self._session = requests.Session()
        retry_strategy = Retry(
            total=active_config.influxdb.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(
            pool_connections=active_config.influxdb.pool_connections,
            pool_maxsize=active_config.influxdb.pool_maxsize,
            max_retries=retry_strategy,
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Cache mapping state_topic -> {uom, object_id, unique_id}
        self._topic_cache: dict[str, dict[str, Any]] = {}

        # Batch write buffer
        self._write_buffer: list[str] = []
        self._batch_size: int = active_config.influxdb.batch_size
        self._batch_lock = asyncio.Lock()
        self._last_flush: float = time.time()
        self._flush_interval: float = active_config.influxdb.flush_interval

        # Rate limiting for queries
        self._rate_limit_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent queries
        self._query_interval: float = active_config.influxdb.query_interval
        self._last_query_time: float = 0.0
        self._query_lock = asyncio.Lock()

        # Writer state — populated by _init_connection; kept as None so that
        # unit tests can instantiate without a live InfluxDB server.
        self._writer_type: str | None = None
        self._write_url: str | None = None
        self._write_headers: dict[str, str] | None = None
        self._write_auth: tuple[str, str] | None = None
        self._writer_obj_bucket: str | None = None
        self._writer_obj_org: str | None = None

    # ------------------------------------------------------------------
    # Connection initialisation helpers
    # ------------------------------------------------------------------

    def _create_v2_bucket(self, base: str, bucket: str, token: str) -> bool:
        """Create an InfluxDB v2 bucket, using the first available organisation.

        Args:
            base: Base URL of the InfluxDB server (e.g. ``http://host:8086``).
            bucket: Name of the bucket to create.
            token: API token with write access.

        Returns:
            ``True`` if the bucket was created successfully, ``False`` otherwise.
        """
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
                    r2 = self._session.post(
                        f"{base}/api/v2/buckets",
                        headers=headers_create,
                        data=json.dumps(create_bucket),
                        timeout=5,
                    )
                    return r2.status_code in (201, 200)
        except Exception as e:
            self.logger.debug(f"{self.log_identity} v2 bucket creation failed: {e}")
        return False

    def _try_v2_write(
        self,
        base: str,
        bucket: str,
        org: str | None,
        token: str | None,
        test_line: bytes,
    ) -> bool:
        """Probe the v2 HTTP write endpoint and configure the writer if reachable.

        If the target bucket does not exist and a token is available, an attempt
        is made to create it before retrying the write.

        Args:
            base: Base URL of the InfluxDB server.
            bucket: Target bucket name.
            org: Organisation name or ID (optional for single-org setups).
            token: API token; omit for token-less setups.
            test_line: A minimal valid line-protocol payload used for probing.

        Returns:
            ``True`` if the endpoint is writable and writer state has been set.
        """
        try:
            # precision=s matches the seconds-precision timestamps emitted by
            # to_line_protocol; the two must always stay in sync.
            url_v2 = f"{base}/api/v2/write?bucket={bucket}&precision=s"
            if org:
                url_v2 += f"&org={org}"
            headers = {"Authorization": f"Token {token}"} if token else {}

            r = self._session.post(url_v2, headers=headers or None, data=test_line, timeout=5)
            if r.status_code in (204, 200):
                self._writer_type = "v2_http"
                self._write_url = url_v2
                self._write_headers = headers or {}
                self.logger.info(f"{self.log_identity} Using v2 HTTP write endpoint to {url_v2}")
                return True

            # If bucket not found and token provided, attempt to create it
            if r.status_code in (400, 404) and token:
                if self._create_v2_bucket(base, bucket, token):
                    r3 = self._session.post(url_v2, headers=headers or None, data=test_line, timeout=5)
                    if r3.status_code in (204, 200):
                        self._writer_type = "v2_http"
                        self._write_url = url_v2
                        self._write_headers = headers or {}
                        self.logger.info(f"{self.log_identity} Created v2 bucket and will use v2 HTTP write to {url_v2}")
                        return True
        except Exception as e:
            self.logger.debug(f"{self.log_identity} v2 HTTP detection failed: {e}")

        return False

    def _create_v1_database(self, base: str, db: str, auth: tuple | None) -> bool:
        """Create an InfluxDB v1 database via the query endpoint.

        Args:
            base: Base URL of the InfluxDB server.
            db: Name of the database to create.
            auth: Optional ``(username, password)`` tuple.

        Returns:
            ``True`` if the database was created successfully, ``False`` otherwise.
        """
        try:
            create_url = f"{base}/query"
            q = {"q": f"CREATE DATABASE {db}"}
            r2 = self._session.post(create_url, params=q, auth=auth, timeout=5)
            return r2.status_code == 200
        except Exception as e:
            self.logger.debug(f"{self.log_identity} v1 database creation failed: {e}")
        return False

    def _try_v1_write(
        self,
        base: str,
        db: str,
        auth: tuple | None,
        test_line: bytes,
    ) -> bool:
        """Probe the v1 HTTP write endpoint and configure the writer if reachable.

        If the target database does not exist, an attempt is made to create it
        before retrying the write.

        Args:
            base: Base URL of the InfluxDB server.
            db: Target database name.
            auth: Optional ``(username, password)`` tuple.
            test_line: A minimal valid line-protocol payload used for probing.

        Returns:
            ``True`` if the endpoint is writable and writer state has been set.
        """
        try:
            url_v1 = f"{base}/write"
            # precision=s keeps v1 consistent with to_line_protocol's seconds output.
            r = self._session.post(url_v1, params={"db": db, "precision": "s"}, data=test_line, auth=auth, timeout=5)
            if r.status_code in (204, 200):
                self._writer_type = "v1_http"
                self._write_url = url_v1
                self._write_auth = auth
                self.logger.info(f"{self.log_identity} Using v1 HTTP write endpoint to {url_v1}")
                return True

            # Attempt to create database and retry
            if r.status_code in (404, 400) or (r.status_code >= 400 and r.content and b"database" in r.content.lower()):
                if self._create_v1_database(base, db, auth):
                    r3 = self._session.post(url_v1, params={"db": db, "precision": "s"}, data=test_line, auth=auth, timeout=5)
                    if r3.status_code in (204, 200):
                        self._writer_type = "v1_http"
                        self._write_url = url_v1
                        self._write_auth = auth
                        self.logger.info(f"{self.log_identity} Created v1 database and will use v1 HTTP write to {url_v1}")
                        return True
        except Exception as e:
            self.logger.debug(f"{self.log_identity} v1 HTTP detection failed: {e}")

        return False

    def _init_connection(self) -> None:
        """Determine the InfluxDB API version and writable endpoint.

        Probes the server in preference order: v2 with token → v1 with
        credentials → v2 without token → v1 without auth.  The first
        successful probe sets :attr:`_writer_type`, :attr:`_write_url`, and
        related writer attributes.

        Raises:
            RuntimeError: If no writable endpoint could be found or created.
        """
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

        raise RuntimeError(f"{self.name} Initialization failed: could not determine writable endpoint or create database/bucket")

    async def async_init(self) -> bool:
        """Asynchronously initialise the InfluxDB connection.

        Runs :meth:`_init_connection` in a thread to avoid blocking the event
        loop.  If InfluxDB is disabled in config this is a no-op.

        Returns:
            ``True`` if initialisation succeeded (or InfluxDB is disabled),
            ``False`` on any connection error.
        """
        if active_config.influxdb.enabled:
            try:
                await asyncio.to_thread(self._init_connection)
                return True
            except Exception as e:
                self.logger.error(f"{self.log_identity} Initialization failed: {e}")
                return False
        return True

    def copy_connection_from(self, source: "InfluxBase") -> None:
        """Copy established connection state from another :class:`InfluxBase` instance.

        Use this to share a single initialised connection across helper objects
        (e.g. :class:`~.hass_history_sync.HassHistorySync`) without repeating
        the probe handshake.

        Args:
            source: An already-initialised :class:`InfluxBase` whose writer
                attributes will be copied onto this instance.
        """
        self._session = source._session
        self._writer_type = source._writer_type
        self._write_url = source._write_url
        self._write_headers = source._write_headers
        self._write_auth = source._write_auth
        self._writer_obj_bucket = source._writer_obj_bucket
        self._writer_obj_org = source._writer_obj_org

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config_values(self) -> InfluxConfigValues:
        """Resolve and return InfluxDB configuration values with backwards-compatibility handling.

        If no explicit token is configured but a password is provided without a
        username, the password is treated as a v2 API token (legacy behaviour).

        Returns:
            A :class:`InfluxConfigValues` dict containing all resolved connection
            parameters.
        """
        host = active_config.influxdb.host
        port = active_config.influxdb.port
        db = active_config.influxdb.database
        user = active_config.influxdb.username
        pwd = active_config.influxdb.password
        token = active_config.influxdb.token
        org = active_config.influxdb.org
        bucket = active_config.influxdb.bucket or db

        # Backwards-compat: if no explicit token provided but a password is
        # supplied and no username, treat the password as a v2 token.
        if not token and pwd and not user:
            token = pwd

        base = f"http://{host}:{port}"
        auth = (user, pwd) if user or pwd else None

        return {
            "host": host,
            "port": port,
            "db": db,
            "user": user,
            "pwd": pwd,
            "token": token,
            "org": org,
            "bucket": bucket,
            "base": base,
            "auth": auth,
        }

    # ------------------------------------------------------------------
    # Line protocol serialisation
    # ------------------------------------------------------------------

    def to_line_protocol(self, measurement: str, tags: dict, fields: dict, timestamp: int) -> str:
        """Serialise a data point to InfluxDB line protocol with second-precision timestamps.

        Both the v1 write endpoint (with ``precision=s``) and the v2 write URL
        (with ``precision=s`` in the query string) expect second-precision
        timestamps, so no conversion is applied beyond truncating to an integer.

        Args:
            measurement: Measurement name (slashes are replaced by the caller
                before passing here; spaces and commas are escaped internally).
            tags: Mapping of tag keys to string values.
            fields: Mapping of field keys to ``int``, ``float``, or ``str`` values.
                Integers are written with the ``i`` suffix; strings are quoted.
            timestamp: Unix timestamp in **seconds**.

        Returns:
            A single line-protocol string ready to be written to InfluxDB.
        """

        def esc(s: str) -> str:
            """Escape spaces and commas in measurement names, tag keys, and tag values."""
            return str(s).replace(" ", "\\ ").replace(",", "\\,")

        def fmt_val(v: Any) -> str:
            """Format a field value according to line-protocol type rules."""
            if isinstance(v, int):
                return f"{v}i"
            if isinstance(v, float):
                return f"{v}"
            return f'"{str(v).replace(chr(34), chr(92) + chr(34))}"'

        tags_part = ",".join(f"{esc(k)}={esc(v)}" for k, v in tags.items()) if tags else ""
        fields_part = ",".join(f"{esc(k)}={fmt_val(v)}" for k, v in fields.items())

        # Emit seconds — must stay consistent with precision=s on both write URLs.
        ts_s = int(timestamp)
        return f"{esc(measurement)}{',' + tags_part if tags_part else ''} {fields_part} {ts_s}"

    # ------------------------------------------------------------------
    # Buffered writes
    # ------------------------------------------------------------------

    async def _flush_buffer_internal(self) -> None:
        """Flush the write buffer to InfluxDB in a single batched request.

        Must be called while holding :attr:`_batch_lock`.  Clears the buffer
        before issuing the network call so that new lines can be accepted
        immediately even if the write fails.
        """
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
        """Append a line-protocol string to the write buffer.

        The buffer is flushed immediately if it has reached :attr:`_batch_size`
        or if more than :attr:`_flush_interval` seconds have elapsed since the
        last flush.

        Args:
            line: A single line-protocol string as returned by
                :meth:`to_line_protocol`.
        """
        async with self._batch_lock:
            self._write_buffer.append(line)
            should_flush = len(self._write_buffer) >= self._batch_size or (time.time() - self._last_flush) >= self._flush_interval
            if should_flush:
                await self._flush_buffer_internal()

    async def flush_buffer(self) -> None:
        """Flush any pending buffered writes to InfluxDB immediately."""
        async with self._batch_lock:
            await self._flush_buffer_internal()

    async def execute_write(self, data: bytes) -> bool:
        """Send a pre-encoded line-protocol payload to InfluxDB over HTTP.

        Dispatches to either the v2 or v1 write endpoint depending on
        :attr:`_writer_type`.  Returns ``False`` without raising if the service
        is offline or the writer has not been initialised.

        Args:
            data: UTF-8 encoded line-protocol payload (one or more lines).

        Returns:
            ``True`` if InfluxDB accepted the payload (HTTP 200 or 204).
        """
        if not self.online:
            return False

        try:
            if self._writer_type == "v2_http" and self._write_url:
                r = await asyncio.to_thread(
                    self._session.post,
                    self._write_url,
                    headers=self._write_headers or {},
                    data=data,
                    timeout=active_config.influxdb.write_timeout,
                )
                if r.status_code in (204, 200):
                    return True
                self.logger.error(f"InfluxDB v2 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url})")
                return False

            elif self._writer_type == "v1_http" and self._write_url:
                r = await asyncio.to_thread(
                    self._session.post,
                    self._write_url,
                    params={"db": active_config.influxdb.database, "precision": "s"},
                    data=data,
                    auth=self._write_auth,
                    timeout=active_config.influxdb.write_timeout,
                )
                if r.status_code in (204, 200):
                    return True
                self.logger.error(f"InfluxDB v1 HTTP write failed: {r.status_code=} {r.text=} (url={self._write_url})")
                return False

        except Exception as e:
            self.logger.error(f"InfluxDB write failed: {e} (type={self._writer_type} url={self._write_url})")
        return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def _rate_limited_query(
        self,
        query_func,
        operation_name: str,
        max_retries: int = 3,
        base_delay: float = 0.5,
    ) -> tuple[bool, Any]:
        """Execute a query coroutine with rate limiting and exponential-backoff retries.

        A semaphore caps concurrency at 10 simultaneous queries.  Within that
        limit a per-query lock enforces the minimum interval between successive
        requests defined by :attr:`_query_interval`.

        Args:
            query_func: Zero-argument async callable that performs the query and
                returns ``(True, result)`` on success, or raises on failure.
            operation_name: Short description used in log and metric labels.
            max_retries: Maximum number of additional attempts after the first
                failure.  A value of 3 means up to 4 total attempts.
            base_delay: Initial retry delay in seconds; doubles on each attempt.

        Returns:
            ``(True, result)`` on success, or ``(False, None)`` after exhausting
            retries or if the service goes offline.
        """
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
                        self.logger.debug(f"{self.log_identity} {operation_name} failed after {max_retries + 1} attempts: {e}")
                        await Metrics.influxdb_query_error()
                        return False, None
                    delay = base_delay * (2**attempt)
                    self.logger.debug(f"{self.log_identity} {operation_name} attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await Metrics.influxdb_retry()
                    await asyncio.sleep(delay)

        # All paths inside the loop return explicitly; this is unreachable but
        # satisfies type checkers that require a return on all code paths.
        return False, None  # pragma: no cover

    async def query_v2(
        self,
        base: str,
        org: str | None,
        token: str,
        flux_query: str,
        timeout: int | float | None = None,
        max_retries: int | None = None,
    ) -> tuple[bool, Any]:
        """Execute a Flux query against the v2 API with rate limiting and retries.

        Args:
            base: Base URL of the InfluxDB server.
            org: Organisation name or ID (optional for single-org setups).
            token: API token with read access.
            flux_query: Full Flux query string.
            timeout: Request timeout in seconds; defaults to ``influxdb.read_timeout``.
            max_retries: Override for the number of retries; defaults to
                ``influxdb.max_retries``.

        Returns:
            ``(True, response_text)`` on success, ``(False, None)`` on failure.
        """
        return await self._rate_limited_query(
            lambda: self.query_v2_internal(
                base,
                org,
                token,
                flux_query,
                timeout if timeout is not None else active_config.influxdb.read_timeout,
            ),
            "v2 query",
            max_retries if max_retries is not None else active_config.influxdb.max_retries,
        )

    async def query_v2_internal(
        self,
        base: str,
        org: str | None,
        token: str,
        flux_query: str,
        timeout: int | float,
    ) -> tuple[bool, Any]:
        """Perform a single Flux query HTTP request without retry logic.

        Intended to be wrapped by :meth:`query_v2` rather than called directly.

        Args:
            base: Base URL of the InfluxDB server.
            org: Organisation name or ID.
            token: API token with read access.
            flux_query: Full Flux query string.
            timeout: Request timeout in seconds.

        Returns:
            ``(True, response_text)`` on HTTP 200.

        Raises:
            Exception: On any non-200 HTTP status or network error.
        """
        headers = {"Authorization": f"Token {token}", "Content-Type": "application/vnd.flux"}
        url = f"{base}/api/v2/query"
        params = {"org": org} if org else {}
        r = await asyncio.to_thread(self._session.post, url, headers=headers, params=params, data=flux_query, timeout=timeout)
        if r.status_code == 200:
            await Metrics.influxdb_query()
            return True, r.text
        raise Exception(f"HTTP {r.status_code}: {r.text}")

    async def query_v1(
        self,
        base: str,
        db: str,
        auth: tuple | None,
        query: str,
        epoch: str | None = None,
        timeout: int | float | None = None,
        max_retries: int | None = None,
    ) -> tuple[bool, Any]:
        """Execute an InfluxQL query against the v1 API with rate limiting and retries.

        Args:
            base: Base URL of the InfluxDB server.
            db: Target database name.
            auth: Optional ``(username, password)`` tuple.
            query: InfluxQL query string.
            epoch: Timestamp precision for results (e.g. ``"s"`` for seconds).
            timeout: Request timeout in seconds; defaults to ``influxdb.read_timeout``.
            max_retries: Override for the number of retries; defaults to
                ``influxdb.max_retries``.

        Returns:
            ``(True, json_result)`` on success, ``(False, None)`` on failure.
        """
        return await self._rate_limited_query(
            lambda: self.query_v1_internal(
                base,
                db,
                auth,
                query,
                epoch,
                timeout if timeout is not None else active_config.influxdb.read_timeout,
            ),
            "v1 query",
            max_retries if max_retries is not None else active_config.influxdb.max_retries,
        )

    async def query_v1_internal(
        self,
        base: str,
        db: str,
        auth: tuple | None,
        query: str,
        epoch: str | None,
        timeout: int | float,
    ) -> tuple[bool, Any]:
        """Perform a single InfluxQL query HTTP request without retry logic.

        Intended to be wrapped by :meth:`query_v1` rather than called directly.

        Args:
            base: Base URL of the InfluxDB server.
            db: Target database name.
            auth: Optional ``(username, password)`` tuple.
            query: InfluxQL query string.
            epoch: Timestamp precision for results, or ``None`` for the default.
            timeout: Request timeout in seconds.

        Returns:
            ``(True, json_result)`` on HTTP 200.

        Raises:
            Exception: On any non-200 HTTP status or network error.
        """
        url = f"{base}/query"
        params: dict[str, str] = {"db": db, "q": query}
        if epoch:
            params["epoch"] = epoch
        r = await asyncio.to_thread(self._session.get, url, params=params, auth=auth, timeout=timeout)
        if r.status_code == 200:
            await Metrics.influxdb_query()
            return True, r.json()
        raise Exception(f"HTTP {r.status_code}: {r.text}")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def parse_timestamp(self, time_str: str) -> int:
        """Parse an ISO 8601 timestamp string to a Unix timestamp in seconds.

        Handles both ``Z`` and ``+00:00`` UTC suffixes.

        Args:
            time_str: ISO 8601 timestamp string (e.g. ``"2024-01-01T12:00:00Z"``).

        Returns:
            Unix timestamp as an integer number of seconds since the epoch.
        """
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return int(dt.timestamp())

    def build_v1_tag_filter(self, tags: dict[str, str]) -> str:
        """Build an InfluxQL WHERE-clause fragment from a tag dictionary.

        Args:
            tags: Mapping of tag key to value to filter on.

        Returns:
            An InfluxQL AND-joined filter string such as
            ``'"entity_id"=\'sensor.power\''``, or an empty string if *tags*
            is empty.
        """
        return " AND ".join(f"\"{k}\"='{v}'" for k, v in tags.items()) if tags else ""
