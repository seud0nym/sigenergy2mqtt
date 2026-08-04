from typing import Any

from sigenergy2mqtt.config import ConsumptionSource, active_config
from sigenergy2mqtt.metrics.metrics import Metrics

from .registry import diagnostics_registry


class DiagnosticsCollectors:
    @classmethod
    def collect_metrics(cls) -> None:
        """Register diagnostics collectors for metrics components."""
        diagnostics_registry.register("modbus", cls._diagnostics_collect_modbus_metrics)
        diagnostics_registry.register("mqtt", cls._diagnostics_collect_mqtt_metrics)
        diagnostics_registry.register("persistence", cls._diagnostics_collect_state_store_metrics)
        if active_config.influxdb.enabled:
            diagnostics_registry.register("influxdb", cls._diagnostics_collect_influxdb_metrics)
        if active_config.pvoutput.enabled:
            diagnostics_registry.register("pvoutput", cls._diagnostics_collect_pvoutput_metrics)

    @classmethod
    async def _diagnostics_collect_modbus_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest Modbus metric."""
        async with Metrics.lock(timeout=1.0):
            return {
                "physical_reads_pct": Metrics.sigenergy2mqtt_modbus_physical_read_percentage,
                "cache_hits_pct": Metrics.sigenergy2mqtt_modbus_cache_hit_percentage,
                "read_max_ms": Metrics.sigenergy2mqtt_modbus_read_max,
                "read_mean_ms": Metrics.sigenergy2mqtt_modbus_read_mean,
                "read_min_ms": Metrics.sigenergy2mqtt_modbus_read_min if Metrics.sigenergy2mqtt_modbus_read_min != float("inf") else 0.0,
                "read_errors": Metrics.sigenergy2mqtt_modbus_read_errors,
                "write_max_ms": Metrics.sigenergy2mqtt_modbus_write_max,
                "write_mean_ms": Metrics.sigenergy2mqtt_modbus_write_mean,
                "write_min_ms": Metrics.sigenergy2mqtt_modbus_write_min if Metrics.sigenergy2mqtt_modbus_write_min != float("inf") else 0.0,
                "write_errors": Metrics.sigenergy2mqtt_modbus_write_errors,
                "skipped_errors": Metrics.sigenergy2mqtt_modbus_skipped_errors,
                "config": {
                    "chunking": "no" if active_config.modbus[0].disable_chunking else "yes",
                    "timeout_0_secs": active_config.modbus[0].timeout,
                    "max_retries_0": active_config.modbus[0].retries,
                },
            }

    @classmethod
    async def _diagnostics_collect_mqtt_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest MQTT metrics."""
        async with Metrics.lock(timeout=1.0):
            return {
                "physical_publishes_pct": Metrics.sigenergy2mqtt_mqtt_physical_publish_percentage,
                "publish_errors": Metrics.sigenergy2mqtt_mqtt_publish_failures,
                "config": {
                    "simplified_topics": "yes" if active_config.home_assistant.enabled or active_config.home_assistant.use_simplified_topics else "no",
                    "repeated_state_publish_interval_secs": active_config.repeated_state_publish_interval,
                    "keepalive_secs": active_config.mqtt.keepalive,
                    "retry_delay_secs": active_config.mqtt.retry_delay,
                    "tls": "yes" if active_config.mqtt.tls else "no",
                    "tls_insecure": "yes" if active_config.mqtt.tls_insecure else "no",
                },
            }

    @classmethod
    async def _diagnostics_collect_influxdb_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest InfluxDB metrics."""
        async with Metrics.lock(timeout=1.0):
            return {
                "write_errors": Metrics.sigenergy2mqtt_influxdb_write_errors,
                "write_max_ms": Metrics.sigenergy2mqtt_influxdb_write_max,
                "write_mean_ms": Metrics.sigenergy2mqtt_influxdb_write_mean,
                "write_min_ms": Metrics.sigenergy2mqtt_influxdb_write_min if Metrics.sigenergy2mqtt_influxdb_write_min != float("inf") else 0.0,
                "query_errors": Metrics.sigenergy2mqtt_influxdb_query_errors,
                "retried": Metrics.sigenergy2mqtt_influxdb_retries,
                "rate_limit_waits": Metrics.sigenergy2mqtt_influxdb_rate_limit_waits,
                "config": {
                    "write_timeout_secs": active_config.influxdb.write_timeout,
                    "batch_size": active_config.influxdb.batch_size,
                    "flush_interval_secs": active_config.influxdb.flush_interval,
                },
            }

    @classmethod
    async def _diagnostics_collect_state_store_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest StateStore metrics."""
        async with Metrics.lock(timeout=1.0):
            return {
                "save_max_ms": Metrics.sigenergy2mqtt_state_store_save_max,
                "save_mean_ms": Metrics.sigenergy2mqtt_state_store_save_mean,
                "save_min_ms": Metrics.sigenergy2mqtt_state_store_save_min if Metrics.sigenergy2mqtt_state_store_save_min != float("inf") else 0.0,
                "load_hits_pct": Metrics.sigenergy2mqtt_state_store_load_hit_percentage,
                "save_errors": Metrics.sigenergy2mqtt_state_store_save_errors,
                "load_errors": Metrics.sigenergy2mqtt_state_store_load_errors,
                "delete_errors": Metrics.sigenergy2mqtt_state_store_delete_errors,
                "config": {
                    "mqtt_redundancy": "yes" if active_config.persistence.mqtt_redundancy else "no",
                    "disk_primary": "yes" if active_config.persistence.disk_primary else "no",
                    "sync_timeout_secs": active_config.persistence.sync_timeout,
                },
            }

    @classmethod
    async def _diagnostics_collect_pvoutput_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest PVOutput metrics."""
        from sigenergy2mqtt.pvoutput import PVOutputSettings

        async with Metrics.lock(timeout=1.0):
            return {
                "upload_errors": Metrics.sigenergy2mqtt_pvoutput_upload_errors,
                "upload_skipped": Metrics.sigenergy2mqtt_pvoutput_upload_skipped,
                "upload_max_ms": Metrics.sigenergy2mqtt_pvoutput_upload_max,
                "upload_mean_ms": Metrics.sigenergy2mqtt_pvoutput_upload_mean,
                "upload_min_ms": Metrics.sigenergy2mqtt_pvoutput_upload_min if Metrics.sigenergy2mqtt_pvoutput_upload_min != float("inf") else 0.0,
                "config": {
                    "donator": "yes" if PVOutputSettings.donator else "no",
                    "status_interval_secs": PVOutputSettings.interval * 60,
                    "exports": "yes" if active_config.pvoutput.exports else "no",
                    "imports": "yes" if active_config.pvoutput.imports else "no",
                    "consumption": "yes" if active_config.pvoutput.consumption == ConsumptionSource.CONSUMPTION.value else active_config.pvoutput.consumption.value,
                    "voltage": active_config.pvoutput.voltage.value,
                    "end_of_day": "@ status interval" if active_config.pvoutput.output_hour == -1 else f"{active_config.pvoutput.output_hour}:00",
                },
            }
