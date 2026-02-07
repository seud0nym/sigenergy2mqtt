import asyncio
import logging
from typing import cast

from sigenergy2mqtt.config import Config

from .influx_base import InfluxBase


class HassHistorySync(InfluxBase):
    """Handles synchronization of historical data from Home Assistant InfluxDB database."""

    def __init__(self, logger: logging.Logger, plant_index: int = -1):
        name = f"Sigenergy InfluxDB History Sync (Plant {plant_index})"
        unique = f"influxdb_history_sync_{plant_index}"
        super().__init__(name, plant_index, unique, "sigenergy2mqtt", "InfluxDB.HistorySync", logger)

    async def detect_homeassistant_db(self) -> bool:
        """
        Detect if a 'homeassistant' database exists on the same InfluxDB server.
        Returns True if found, False otherwise.
        """
        try:
            config = self.get_config_values()

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
            success, result = await self.query_v1(config["base"], config["db"], config["auth"], "SHOW DATABASES", timeout=5)
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

    async def get_earliest_timestamp(self, measurement: str, tags: dict[str, str]) -> int:
        """
        Get the earliest timestamp for a given measurement and tag combination in the target database.
        Returns timestamp in seconds, or current time if no records exist.
        """
        import time

        try:
            config = self.get_config_values()
            tag_filters = self.build_tag_filters(tags)

            # Try v2 API (Flux query)
            if config["token"]:
                flux_query = f'from(bucket: "{config["bucket"]}")\n  |> range(start: 0)\n  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
                for k, v in tags.items():
                    flux_query += f'  |> filter(fn: (r) => r.{k} == "{v}")\n'
                flux_query += '  |> first()\n  |> yield(name: "earliest")\n'

                success, response_text = await self.query_v2(config["base"], config["org"], config["token"], flux_query)
                if success and response_text:
                    lines = response_text.strip().split("\n")
                    for line in lines:
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
            where_clause = f"WHERE {tag_filters['v1']}" if tag_filters["v1"] else ""
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

    async def copy_records_v2(self, config: dict, measurement: str, tags: dict[str, str], before_timestamp: int | None) -> int:
        """Copy records using v2 API with chunking (latest to earliest)."""
        records_copied = 0
        chunk_size = Config.influxdb.sync_chunk_size
        current_before = before_timestamp

        while self.online:
            time_filter = f"stop: time(v: {current_before})" if current_before else "start: 0"
            flux_query = f'from(bucket: "homeassistant")\n  |> range({time_filter})\n  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
            for k, v in tags.items():
                flux_query += f'  |> filter(fn: (r) => r.{k} == "{v}")\n'
            flux_query += f'  |> sort(columns: ["_time"], desc: true)\n  |> limit(n: {chunk_size})\n  |> yield(name: "records")\n'

            success, response_text = await self.query_v2(config["base"], config["org"], config["token"], flux_query)
            if not success or not response_text:
                break

            # Parse CSV response and convert to line protocol
            lines = response_text.strip().split("\n")
            headers_parsed = False
            header_indices = {}
            chunk_records = 0
            earliest_timestamp = None

            for line in lines:
                if not line.strip():
                    continue

                if not headers_parsed:
                    if "_time" in line and "_value" in line:
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

                timestamp = self.parse_timestamp(time_str)
                earliest_timestamp = timestamp

                # Extract field and value
                value_idx = header_indices.get("_value", 7)
                field_value = parts[value_idx].strip() if value_idx < len(parts) else None

                if field_value is None:
                    continue

                # Build fields dict
                fields: dict[str, float | str] = {}
                try:
                    fields["value"] = float(field_value)
                except Exception:
                    fields["value_str"] = str(field_value)

                # Write the record
                line_protocol = self.to_line_protocol(measurement, tags, fields, timestamp)
                await self.write_line(line_protocol)
                chunk_records += 1

            if chunk_records == 0:
                break

            records_copied += chunk_records
            self.logger.debug(f"{self.name} Copied {chunk_records} records in chunk (total: {records_copied}) for {tags.get('entity_id', 'unknown')} [{measurement}]")

            if earliest_timestamp is None or chunk_records < chunk_size:
                break

            current_before = earliest_timestamp

        return records_copied

    async def copy_records_v1(self, config: dict, measurement: str, tags: dict[str, str], before_timestamp: int | None) -> int:
        """Copy records using v1 API with chunking (latest to earliest)."""
        records_copied = 0
        tag_filters = self.build_tag_filters(tags)
        chunk_size = Config.influxdb.sync_chunk_size
        current_before = before_timestamp

        while self.online:
            where_parts = []
            if tag_filters["v1"]:
                where_parts.append(tag_filters["v1"])
            if current_before:
                where_parts.append(f"time < {current_before}s")

            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            query = f'SELECT * FROM "{measurement}" {where_clause} ORDER BY time DESC LIMIT {chunk_size}'

            success, result = await self.query_v1(config["base"], "homeassistant", config["auth"], query, epoch="s")
            if not success or not result:
                break

            chunk_records = 0
            last_timestamp = None

            if "results" in result and result["results"]:
                series = result["results"][0].get("series", [])
                for s in series:
                    if "values" not in s or "columns" not in s:
                        continue

                    columns = s["columns"]
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
                                val = row[i]
                                if isinstance(val, (int, float)):
                                    fields["value"] = float(val)
                                else:
                                    fields["value_str"] = str(val)

                        if not fields:
                            continue

                        # Write the record
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

    async def copy_records_from_homeassistant(self, measurement: str, tags: dict[str, str], before_timestamp: int | None = None) -> int:
        """
        Copy records from 'homeassistant' database with the same measurement and tags.
        If before_timestamp is provided, only copy records with timestamps earlier than it.
        If before_timestamp is None, copy all records for that measurement/tag combination.
        Returns the number of records copied.
        """
        try:
            config = self.get_config_values()
            records_copied = 0

            # Try v2 API first
            if config["token"]:
                records_copied = await self.copy_records_v2(config, measurement, tags, before_timestamp)
                if records_copied > 0:
                    self.logger.info(f"{self.name} Copied {records_copied} records from homeassistant (v2) for {measurement} with tags {tags}")
                    return records_copied

            # Try v1 API
            records_copied = await self.copy_records_v1(config, measurement, tags, before_timestamp)
            if records_copied > 0:
                self.logger.info(f"{self.name} Copied {records_copied} records from homeassistant (v1) for {measurement} with tags {tags}")

            return records_copied

        except Exception as e:
            self.logger.error(f"{self.name} Error copying records from homeassistant: {e}")
            return 0

    async def sync_from_homeassistant(self, topic_cache: dict) -> dict[str, int]:
        """
        Main method to detect homeassistant database and sync all cached measurements.
        Returns a dict mapping measurement/tag combinations to number of records copied.

        Args:
            topic_cache: The topic cache from InfluxService containing sensor metadata.
        """
        results = {}

        # First check if homeassistant database exists
        if not await self.detect_homeassistant_db():
            self.logger.info(f"{self.name} No homeassistant database found, skipping sync")
            return results

        self.logger.info(f"{self.name} Starting parallel sync from homeassistant database")

        # Iterate through cached topics to get unique measurement/tag combinations
        seen_combinations = set()
        sync_tasks = []
        semaphore = asyncio.Semaphore(Config.influxdb.max_sync_workers)

        async def sync_sensor(measurement: str, tags: dict[str, str]):
            async with semaphore:
                if not self.online:
                    return measurement, tags, 0
                try:
                    # Get earliest timestamp in target database
                    earliest_ts = await self.get_earliest_timestamp(measurement, tags)

                    # Copy records from homeassistant that are older than our earliest record
                    self.logger.info(f"{self.name} Starting sync for {tags.get('entity_id', 'unknown')} [{measurement}] (earliest existing: {earliest_ts})")
                    count = await self.copy_records_from_homeassistant(measurement, tags, before_timestamp=earliest_ts)
                    return measurement, tags, count
                except Exception as e:
                    self.logger.error(f"{self.name} Error syncing {tags.get('entity_id', 'unknown')} [{measurement}]: {e}")
                    return measurement, tags, 0

        for topic, sensor in topic_cache.items():
            measurement = cast(str, sensor.get("uom", Config.influxdb.default_measurement)).replace("/", "_")
            tags = {"entity_id": cast(str, sensor.get("object_id"))}

            # Create a hashable key for this combination
            combo_key = (measurement, tuple(sorted(tags.items())))
            if combo_key in seen_combinations:
                continue
            seen_combinations.add(combo_key)

            sync_tasks.append(sync_sensor(measurement, tags))

        if not sync_tasks:
            return results

        # Execute all tasks in parallel with semaphore limit
        sync_results = await asyncio.gather(*sync_tasks)

        for measurement, tags, count in sync_results:
            result_key = f"{measurement}[{','.join(f'{k}={v}' for k, v in tags.items())}]"
            results[result_key] = count

        total_copied = sum(results.values())
        self.logger.info(f"{self.name} Parallel sync complete: copied {total_copied} total records across {len(results)} entities")

        return results
