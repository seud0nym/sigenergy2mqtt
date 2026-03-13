import asyncio
import logging
import time
from typing import Any, cast

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.influxdb.influx_base import InfluxConfigValues

from .influx_base import InfluxBase


class HassHistorySync(InfluxBase):
    """Backfill helper that copies historical sensor data from a Home Assistant InfluxDB database.

    This class is created by :class:`~.influx_service.InfluxService` and shares
    its already-initialised HTTP session and writer state via
    :meth:`~InfluxBase.copy_connection_from`.  It does **not** call
    :meth:`~InfluxBase.async_init` itself.

    The sync workflow is:

    1. Detect whether a ``homeassistant`` database/bucket exists on the same
       server (:meth:`detect_homeassistant_db`).
    2. For each known sensor, find the earliest timestamp already present in the
       target database (:meth:`get_earliest_timestamp`).
    3. Copy all records from Home Assistant that pre-date that timestamp
       (:meth:`copy_records_from_homeassistant`).
    """

    def __init__(self, logger: logging.Logger, plant_index: int = -1) -> None:
        """Initialise the history sync helper.

        Args:
            logger: Pre-configured logger, typically inherited from the parent
                :class:`~.influx_service.InfluxService`.
            plant_index: Zero-based index of the Modbus plant being synced.
        """
        name = f"Sigenergy InfluxDB History Sync (Plant {plant_index})"
        unique = f"influxdb_history_sync_{plant_index}"
        super().__init__(name, plant_index, unique, "sigenergy2mqtt", "InfluxDB.HistorySync", logger)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    async def detect_homeassistant_db(self) -> bool:
        """Check whether a ``homeassistant`` database or bucket exists on the InfluxDB server.

        Tries the v2 bucket list API first (if a token is available), then
        falls back to the v1 ``SHOW DATABASES`` query.

        Returns:
            ``True`` if a ``homeassistant`` database or bucket was found.
        """
        try:
            config = self.get_config_values()
            self.logger.debug(
                f"{self.name} detect_homeassistant_db: base={config['base']} db={config['db']} "
                f"token={'set' if config['token'] else 'unset'} org={config['org']} bucket={config['bucket']}"
            )

            # Try v2 API first (if token available)
            if config["token"]:
                try:
                    headers = {"Authorization": f"Token {config['token']}"}
                    url = f"{config['base']}/api/v2/buckets"
                    r = await asyncio.to_thread(self._session.get, url, headers=headers, timeout=5)
                    self.logger.debug(f"{self.name} v2 bucket probe status={r.status_code} url={url}")
                    if r.status_code == 200:
                        buckets = r.json()
                        self.logger.debug(
                            f"{self.name} v2 bucket probe payload keys={list(buckets.keys()) if isinstance(buckets, dict) else type(buckets).__name__}"
                        )
                        if isinstance(buckets, dict) and "buckets" in buckets:
                            for bucket in buckets["buckets"]:
                                if bucket.get("name") == "homeassistant":
                                    self.logger.info(f"{self.name} Found 'homeassistant' bucket in InfluxDB v2")
                                    return True
                except Exception as e:
                    self.logger.debug(f"{self.name} v2 bucket detection failed: {e}")

            # Try v1 API.  Prefer generic /query call (without db=...) for
            # SHOW DATABASES because requiring a specific database parameter can
            # fail on startup when that target DB has not been created yet.
            async def check_v1_databases(db_name: str | None) -> bool:
                if db_name:
                    self.logger.debug(f"{self.name} v1 SHOW DATABASES via query_v1 db={db_name}")
                    success, result = await self.query_v1(config["base"], db_name, config["auth"], "SHOW DATABASES", timeout=5)
                else:
                    url = f"{config['base']}/query"
                    params = {"q": "SHOW DATABASES"}
                    r = await asyncio.to_thread(self._session.get, url, params=params, auth=config["auth"], timeout=5)
                    self.logger.debug(f"{self.name} v1 SHOW DATABASES generic probe status={r.status_code} url={url} params={params}")
                    success = r.status_code == 200
                    result = r.json() if success else None
                    if not success:
                        self.logger.debug(f"{self.name} v1 generic SHOW DATABASES non-200 body={r.text[:300]}")

                if not success or not result:
                    self.logger.debug(f"{self.name} v1 SHOW DATABASES probe returned success={success} has_result={bool(result)} db_name={db_name}")
                    return False

                if "results" not in result or not result["results"]:
                    self.logger.debug(f"{self.name} v1 SHOW DATABASES payload missing results db_name={db_name} payload={str(result)[:300]}")
                    return False

                series = result["results"][0].get("series", [])
                if not series or "values" not in series[0]:
                    self.logger.debug(f"{self.name} v1 SHOW DATABASES payload missing series/values db_name={db_name} payload={str(result)[:300]}")
                    return False

                databases = [row[0] for row in series[0]["values"]]
                self.logger.debug(f"{self.name} v1 SHOW DATABASES db_name={db_name} databases={databases}")
                if "homeassistant" in databases:
                    self.logger.info(f"{self.name} Found 'homeassistant' database in InfluxDB v1")
                    return True

                return False

            async def probe_homeassistant_v1() -> bool:
                """Probe direct access to the homeassistant DB when SHOW DATABASES is unavailable.

                Some InfluxDB v1 setups use non-admin users that can read/write
                specific databases but cannot execute SHOW DATABASES. In that
                case, a direct query against the target DB is a better signal.
                """
                self.logger.debug(f"{self.name} v1 direct probe db=homeassistant query=SHOW MEASUREMENTS LIMIT 1")
                success, result = await self.query_v1(config["base"], "homeassistant", config["auth"], "SHOW MEASUREMENTS LIMIT 1", timeout=5)
                if not success or not isinstance(result, dict):
                    self.logger.debug(
                        f"{self.name} v1 direct probe failed success={success} result_type={type(result).__name__}"
                    )
                    return False
                query_results = result.get("results")
                if not isinstance(query_results, list) or not query_results:
                    self.logger.debug(f"{self.name} v1 direct probe payload missing results payload={str(result)[:300]}")
                    return False

                first_result = query_results[0]
                if isinstance(first_result, dict) and "error" in first_result:
                    # Distinguish between "db missing" and query/permission
                    # responses. If query executed without "database not found",
                    # we consider the DB present.
                    error_text = str(first_result["error"]).lower()
                    if "database not found" in error_text:
                        return False
                    self.logger.debug(f"{self.name} homeassistant v1 probe returned error but DB appears reachable: {first_result['error']}")

                self.logger.info(f"{self.name} Found 'homeassistant' database in InfluxDB v1 (direct probe)")
                return True

            if await check_v1_databases(None):
                return True

            if config["db"] and await check_v1_databases(config["db"]):
                return True

            if await probe_homeassistant_v1():
                return True

            self.logger.info(f"{self.name} 'homeassistant' database/bucket not found")
            self.logger.debug(f"{self.name} detect_homeassistant_db exhausted all probes")
            return False

        except Exception as e:
            self.logger.error(f"{self.name} Error detecting homeassistant database: {e}")
            return False

    # ------------------------------------------------------------------
    # Timestamp utilities
    # ------------------------------------------------------------------

    async def get_earliest_timestamp(self, measurement: str, tags: dict[str, str]) -> int:
        """Find the earliest recorded timestamp for a measurement/tag combination in the target database.

        Used to determine the cut-off point for backfill: only records older
        than this timestamp need to be copied from Home Assistant.

        Args:
            measurement: InfluxDB measurement name.
            tags: Tag key/value pairs that uniquely identify the sensor.

        Returns:
            Unix timestamp in seconds of the earliest existing record, or the
            current time if no records exist yet (indicating a full backfill is
            needed).
        """
        try:
            config = self.get_config_values()
            self.logger.debug(
                f"{self.name} detect_homeassistant_db: base={config['base']} db={config['db']} "
                f"token={'set' if config['token'] else 'unset'} org={config['org']} bucket={config['bucket']}"
            )

            # Try v2 API (Flux query)
            if config["token"]:
                flux_query = f'from(bucket: "{config["bucket"]}")\n  |> range(start: 0)\n  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
                for k, v in tags.items():
                    flux_query += f'  |> filter(fn: (r) => r.{k} == "{v}")\n'
                flux_query += '  |> first()\n  |> yield(name: "earliest")\n'

                success, response_text = await self.query_v2(config["base"], config["org"], config["token"], flux_query)
                if success and response_text:
                    for line in response_text.strip().split("\n"):
                        if line.startswith("_") or not line.strip():
                            continue
                        parts = line.split(",")
                        if len(parts) > 5:
                            time_str = parts[5].strip()
                            if time_str and time_str != "_time":
                                timestamp = self.parse_timestamp(time_str)
                                self.logger.debug(f"{self.name} Found earliest timestamp {timestamp} for {measurement} with tags {tags}")
                                return timestamp
                    return int(time.time())

            # Try v1 API (InfluxQL)
            v1_filter = self.build_v1_tag_filter(tags)
            where_clause = f"WHERE {v1_filter}" if v1_filter else ""
            query = f'SELECT * FROM "{measurement}" {where_clause} ORDER BY time ASC LIMIT 1'
            success, result = await self.query_v1(config["base"], config["db"], config["auth"], query)
            if success and result:
                if "results" in result and result["results"]:
                    series = result["results"][0].get("series", [])
                    if series and "values" in series[0] and series[0]["values"]:
                        time_str = series[0]["values"][0][0]
                        timestamp = self.parse_timestamp(time_str)
                        self.logger.debug(f"{self.name} Found earliest timestamp {timestamp} for {measurement} with tags {tags}")
                        return timestamp

            return int(time.time())

        except Exception as e:
            self.logger.error(f"{self.name} Error getting earliest timestamp: {e}")
            return int(time.time())

    # ------------------------------------------------------------------
    # Record copying
    # ------------------------------------------------------------------

    async def copy_records_v2(
        self,
        config: InfluxConfigValues,
        measurement: str,
        tags: dict[str, str],
        before_timestamp: int | None,
    ) -> int:
        """Copy records from the Home Assistant bucket using the v2 Flux API.

        Paginates from most-recent to oldest in chunks of
        ``influxdb.sync_chunk_size``, stopping when a chunk is smaller than
        the page size (indicating the start of history has been reached).

        Args:
            config: Resolved config dict from :meth:`~InfluxBase.get_config_values`.
            measurement: Measurement name to query.
            tags: Tag filters identifying the target sensor.
            before_timestamp: Copy records with timestamps strictly before this
                Unix second value.  ``None`` copies all records.

        Returns:
            Total number of line-protocol records written.
        """
        records_copied = 0
        chunk_size = active_config.influxdb.sync_chunk_size
        current_before = before_timestamp

        while self.online:
            # Build time range: always anchor the end; always anchor the start
            # at Unix epoch so Flux doesn't scan unbounded history on each page.
            if current_before:
                time_filter = f"start: 0, stop: time(v: {current_before})"
            else:
                time_filter = "start: 0"

            flux_query = f'from(bucket: "homeassistant")\n  |> range({time_filter})\n  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
            for k, v in tags.items():
                flux_query += f'  |> filter(fn: (r) => r.{k} == "{v}")\n'
            flux_query += f'  |> sort(columns: ["_time"], desc: true)\n  |> limit(n: {chunk_size})\n  |> yield(name: "records")\n'

            success, response_text = await self.query_v2(config["base"], config["org"], cast(str, config["token"]), flux_query)
            if not success or not response_text:
                break

            # Parse CSV response and convert to line protocol.
            lines = response_text.strip().split("\n")
            header_indices: dict[str, int] = {}
            chunk_records = 0
            earliest_timestamp: int | None = None

            for line in lines:
                if not line.strip():
                    continue

                # Detect and parse the header row.
                if not header_indices:
                    if "_time" in line and "_value" in line:
                        parts = line.split(",")
                        header_indices = {part.strip(): i for i, part in enumerate(parts)}
                    continue

                parts = line.split(",")
                if len(parts) <= 1:
                    continue

                # Require both _time and _value to be present in the header;
                # skip rather than guess if either index is missing.
                time_idx = header_indices.get("_time")
                value_idx = header_indices.get("_value")
                if time_idx is None or value_idx is None:
                    continue

                time_str = parts[time_idx].strip() if time_idx < len(parts) else None
                field_value = parts[value_idx].strip() if value_idx < len(parts) else None

                if not time_str or field_value is None:
                    continue

                timestamp = self.parse_timestamp(time_str)
                earliest_timestamp = timestamp

                fields: dict[str, float | str] = {}
                try:
                    fields["value"] = float(field_value)
                except (ValueError, TypeError):
                    fields["value_str"] = str(field_value)

                line_protocol = self.to_line_protocol(measurement, tags, fields, timestamp)
                await self.write_line(line_protocol)
                chunk_records += 1

            records_copied += chunk_records
            self.logger.debug(f"{self.name} Copied {chunk_records} records in chunk (total: {records_copied}) for {tags.get('entity_id', 'unknown')} [{measurement}]")

            if earliest_timestamp is None or chunk_records < chunk_size:
                break

            current_before = earliest_timestamp

        return records_copied

    async def copy_records_v1(
        self,
        config: InfluxConfigValues,
        measurement: str,
        tags: dict[str, str],
        before_timestamp: int | None,
    ) -> int:
        """Copy records from the Home Assistant database using the v1 InfluxQL API.

        Paginates from most-recent to oldest in chunks of
        ``influxdb.sync_chunk_size``, stopping when a partial chunk is returned.

        Args:
            config: Resolved config dict from :meth:`~InfluxBase.get_config_values`.
            measurement: Measurement name to query.
            tags: Tag filters identifying the target sensor.
            before_timestamp: Copy records with timestamps strictly before this
                Unix second value.  ``None`` copies all records.

        Returns:
            Total number of line-protocol records written.
        """
        records_copied = 0
        v1_filter = self.build_v1_tag_filter(tags)
        chunk_size = active_config.influxdb.sync_chunk_size
        current_before = before_timestamp

        while self.online:
            where_parts: list[str] = []
            if v1_filter:
                where_parts.append(v1_filter)
            if current_before:
                where_parts.append(f"time < {current_before}s")

            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            query = f'SELECT * FROM "{measurement}" {where_clause} ORDER BY time DESC LIMIT {chunk_size}'

            success, result = await self.query_v1(config["base"], "homeassistant", config["auth"], query, epoch="s")
            if not success or not result:
                break

            chunk_records = 0
            last_timestamp: int | None = None

            if "results" in result and result["results"]:
                series = result["results"][0].get("series", [])
                for s in series:
                    if "values" not in s or "columns" not in s:
                        continue

                    columns: list[str] = s["columns"]
                    time_idx = columns.index("time") if "time" in columns else 0

                    for row in s["values"]:
                        timestamp = int(row[time_idx])
                        last_timestamp = timestamp

                        # Build fields from non-time, non-tag columns
                        fields: dict[str, float | str] = {}
                        for i, col in enumerate(columns):
                            if col == "time" or col in tags:
                                continue
                            if row[i] is not None:
                                val: Any = row[i]
                                if isinstance(val, (int, float)):
                                    fields["value"] = float(val)
                                else:
                                    fields["value_str"] = str(val)

                        if not fields:
                            continue

                        line_protocol = self.to_line_protocol(measurement, tags, fields, timestamp)
                        await self.write_line(line_protocol)
                        chunk_records += 1

            if chunk_records == 0:
                break

            records_copied += chunk_records
            self.logger.debug(f"{self.name} Copied {chunk_records} records in chunk (total: {records_copied}) for {tags.get('entity_id', 'unknown')} [{measurement}]")

            if last_timestamp is None or chunk_records < chunk_size:
                break

            current_before = last_timestamp

        return records_copied

    async def copy_records_from_homeassistant(
        self,
        measurement: str,
        tags: dict[str, str],
        before_timestamp: int | None = None,
    ) -> int:
        """Copy records from the Home Assistant InfluxDB database into the target database.

        Tries the v2 API first; falls back to v1 if no token is configured or
        if v2 returns no records.

        Args:
            measurement: Measurement name to copy.
            tags: Tag key/value pairs that identify the sensor in both databases.
            before_timestamp: Upper bound (exclusive) on the record timestamps to
                copy, in Unix seconds.  Pass ``None`` to copy all records.

        Returns:
            Total number of records written, or ``0`` on error.
        """
        try:
            config = self.get_config_values()
            self.logger.debug(
                f"{self.name} detect_homeassistant_db: base={config['base']} db={config['db']} "
                f"token={'set' if config['token'] else 'unset'} org={config['org']} bucket={config['bucket']}"
            )

            # Try v2 API first
            if config["token"]:
                records_copied = await self.copy_records_v2(config, measurement, tags, before_timestamp)
                if records_copied > 0:
                    self.logger.info(f"{self.name} Copied {records_copied} records from homeassistant (v2) for {measurement} with tags {tags}")
                    return records_copied

            # Fall back to v1 API
            records_copied = await self.copy_records_v1(config, measurement, tags, before_timestamp)
            if records_copied > 0:
                self.logger.info(f"{self.name} Copied {records_copied} records from homeassistant (v1) for {measurement} with tags {tags}")

            return records_copied

        except Exception as e:
            self.logger.error(f"{self.name} Error copying records from homeassistant: {e}")
            return 0

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    async def sync_from_homeassistant(self, topic_cache: dict) -> dict[str, int]:
        """Detect and backfill all cached sensor measurements from Home Assistant.

        For each unique measurement/tag combination found in *topic_cache*:

        1. Determine the earliest timestamp already in the target database.
        2. Copy any older records from the Home Assistant database.

        Sensors are processed in parallel, bounded by
        ``influxdb.max_sync_workers`` concurrent coroutines.

        Args:
            topic_cache: The :attr:`~InfluxBase._topic_cache` dict from the
                parent :class:`~.influx_service.InfluxService`, mapping MQTT
                state topics to sensor metadata dicts.

        Returns:
            Mapping of ``"measurement[tag=value,...]"`` keys to the number of
            records copied for each sensor.  Empty if the Home Assistant
            database was not found or no sensors were cached.
        """
        results: dict[str, int] = {}

        if not await self.detect_homeassistant_db():
            self.logger.info(f"{self.name} No homeassistant database found, skipping sync")
            return results

        self.logger.info(f"{self.name} Starting parallel sync from homeassistant database")

        seen_combinations: set[tuple] = set()
        sync_tasks = []
        semaphore = asyncio.Semaphore(active_config.influxdb.max_sync_workers)

        async def sync_sensor(measurement: str, tags: dict[str, str]) -> tuple[str, dict[str, str], int]:
            """Sync a single measurement/tag combination under the shared semaphore."""
            async with semaphore:
                if not self.online:
                    return measurement, tags, 0
                try:
                    earliest_ts = await self.get_earliest_timestamp(measurement, tags)
                    self.logger.info(f"{self.name} Starting sync for {tags.get('entity_id', 'unknown')} [{measurement}] (earliest existing: {earliest_ts})")
                    count = await self.copy_records_from_homeassistant(measurement, tags, before_timestamp=earliest_ts)
                    return measurement, tags, count
                except Exception as e:
                    self.logger.error(f"{self.name} Error syncing {tags.get('entity_id', 'unknown')} [{measurement}]: {e}")
                    return measurement, tags, 0

        for sensor in topic_cache.values():
            measurement = cast(str, sensor.get("uom", active_config.influxdb.default_measurement)).replace("/", "_")
            tags = {"entity_id": cast(str, sensor.get("object_id"))}

            combo_key = (measurement, tuple(sorted(tags.items())))
            if combo_key in seen_combinations:
                continue
            seen_combinations.add(combo_key)

            sync_tasks.append(sync_sensor(measurement, tags))

        if not sync_tasks:
            return results

        sync_results = await asyncio.gather(*sync_tasks)

        for measurement, tags, count in sync_results:
            result_key = f"{measurement}[{','.join(f'{k}={v}' for k, v in tags.items())}]"
            results[result_key] = count

        total_copied = sum(results.values())
        self.logger.info(f"{self.name} Parallel sync complete: copied {total_copied} total records across {len(results)} entities")

        return results
