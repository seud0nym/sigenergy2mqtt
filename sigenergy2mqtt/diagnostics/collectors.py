from typing import TYPE_CHECKING, Any, cast

from sigenergy2mqtt.config import ConsumptionSource, active_config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.sensors.base.constants import DiscoveryKeys
from sigenergy2mqtt.sensors.base.writeable import NumericSensorMixin, SelectSensorMixin, SwitchSensorMixin

from .registry import diagnostics_registry

if TYPE_CHECKING:
    from sigenergy2mqtt.config.sensors import SettingsSensor


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
        diagnostics_registry.register("runtime_configuration", cls._diagnostics_collect_runtime_config)
        diagnostics_registry.register("sensor_debug_logging", cls._diagnostics_collect_sensor_debug)

    @classmethod
    async def _diagnostics_collect_runtime_config(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes live SettingsService sensor values as editable controls."""
        from sigenergy2mqtt.config.sensors import SettingsSensor
        from sigenergy2mqtt.devices.base.registry import DeviceRegistry

        controls: dict[str, Any] = {}

        # Find the SettingsService device (registered at plant_index=-1)
        for device in DeviceRegistry.get(-1):
            for sensor in device.sensors.values():
                if not isinstance(sensor, SettingsSensor):
                    continue
                settings_sensor = cast("SettingsSensor", sensor)

                # Derive a URL-safe endpoint key from the unique_id
                # e.g. "sigenergy2mqtt_config_log_level" -> "log_level"
                endpoint = settings_sensor.unique_id.removeprefix("sigenergy2mqtt_config_")

                # Read the current display value via get_value()
                value = settings_sensor.get_value()

                # Build the descriptor based on the sensor's mixin type
                descriptor: dict[str, Any] = {
                    "label": settings_sensor.name,
                    "comment": settings_sensor.get_attributes().get("comment", ""),
                    "endpoint": endpoint,
                }

                if isinstance(settings_sensor, SelectSensorMixin):
                    options = cast(list[str], settings_sensor[DiscoveryKeys.OPTIONS])
                    # Filter out empty placeholder slots (log-level list has empty strings)
                    visible_options = [o for o in options if o]
                    descriptor.update({
                        "type": "select",
                        "value": str(value) if value is not None else "",
                        "options": visible_options,
                    })
                elif isinstance(settings_sensor, NumericSensorMixin):
                    descriptor.update({
                        "type": "number",
                        "value": value,
                        "min": settings_sensor.get(DiscoveryKeys.MIN),
                        "max": settings_sensor.get(DiscoveryKeys.MAX),
                        "unit": settings_sensor.unit or "",
                    })
                elif isinstance(settings_sensor, SwitchSensorMixin):
                    descriptor.update({
                        "type": "switch",
                        "value": bool(value),
                    })
                else:
                    # Fallback: surface as a read-only string
                    descriptor.update({"type": "readonly", "value": str(value)})

                controls[endpoint] = descriptor

        return {"controls": controls}

    @classmethod
    async def _diagnostics_collect_sensor_debug(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes all sensor debug_logging flags, grouped by device."""
        from sigenergy2mqtt.config.sensors import SettingsSensor
        from sigenergy2mqtt.devices.base.registry import DeviceRegistry

        devices_data: dict[str, Any] = {}

        for plant_index, device_list in sorted(DeviceRegistry._devices.items()):
            if plant_index < 0:
                continue
            for device in device_list:
                sensors_data: dict[str, Any] = {}
                for sensor in device.sensors.values():
                    if isinstance(sensor, SettingsSensor) or not sensor.publishable:
                        continue
                    sensors_data[sensor.unique_id] = {
                        "label": sensor.name,
                        "type": "switch",
                        "value": sensor.debug_logging,
                    }
                if sensors_data:
                    devices_data[device.unique_id] = {
                        "device_name": device.name,
                        "sensors": sensors_data,
                    }

        return devices_data

    @classmethod
    async def _diagnostics_collect_influxdb_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest InfluxDB metrics."""
        async with Metrics.lock(timeout=1.0):
            return {
                f"{_t('InfluxDBWriteErrors.name')}": Metrics.sigenergy2mqtt_influxdb_write_errors,
                f"{_t('InfluxDBWriteMax.name')}_ms": Metrics.sigenergy2mqtt_influxdb_write_max,
                f"{_t('InfluxDBWriteMean.name')}_ms": Metrics.sigenergy2mqtt_influxdb_write_mean,
                f"{_t('InfluxDBWriteMin.name')}_ms": Metrics.sigenergy2mqtt_influxdb_write_min if Metrics.sigenergy2mqtt_influxdb_write_min != float("inf") else 0.0,
                f"{_t('InfluxDBQueryErrors.name')}": Metrics.sigenergy2mqtt_influxdb_query_errors,
                f"{_t('InfluxDBRetries.name')}": Metrics.sigenergy2mqtt_influxdb_retries,
                f"{_t('InfluxDBRateLimitWaits.name')}": Metrics.sigenergy2mqtt_influxdb_rate_limit_waits,
                "config": {
                    "write_timeout_secs": active_config.influxdb.write_timeout,
                    "batch_size": active_config.influxdb.batch_size,
                    "flush_interval_secs": active_config.influxdb.flush_interval,
                },
            }

    @classmethod
    async def _diagnostics_collect_modbus_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest Modbus metric."""
        async with Metrics.lock(timeout=1.0):
            return {
                f"{_t('ModbusPhysicalReads.name')}_pct": Metrics.sigenergy2mqtt_modbus_physical_read_percentage,
                f"{_t('ModbusCacheHits.name')}_pct": Metrics.sigenergy2mqtt_modbus_cache_hit_percentage,
                f"{_t('ModbusReadMax.name')}_ms": Metrics.sigenergy2mqtt_modbus_read_max,
                f"{_t('ModbusReadMean.name')}_ms": Metrics.sigenergy2mqtt_modbus_read_mean,
                f"{_t('ModbusReadMin.name')}_ms": Metrics.sigenergy2mqtt_modbus_read_min if Metrics.sigenergy2mqtt_modbus_read_min != float("inf") else 0.0,
                f"{_t('ModbusReadErrors.name')}": Metrics.sigenergy2mqtt_modbus_read_errors,
                f"{_t('ModbusWriteMax.name')}_ms": Metrics.sigenergy2mqtt_modbus_write_max,
                f"{_t('ModbusWriteMean.name')}_ms": Metrics.sigenergy2mqtt_modbus_write_mean,
                f"{_t('ModbusWriteMin.name')}_ms": Metrics.sigenergy2mqtt_modbus_write_min if Metrics.sigenergy2mqtt_modbus_write_min != float("inf") else 0.0,
                f"{_t('ModbusWriteErrors.name')}": Metrics.sigenergy2mqtt_modbus_write_errors,
                f"{_t('ModbusSkippedErrors.name')}": Metrics.sigenergy2mqtt_modbus_skipped_errors,
                "config": {
                    "disable_chunking": "yes" if active_config.modbus[0].disable_chunking else "no",
                    "timeout_0_secs": active_config.modbus[0].timeout,
                    "max_retries_0": active_config.modbus[0].retries,
                },
            }

    @classmethod
    async def _diagnostics_collect_mqtt_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest MQTT metrics."""
        async with Metrics.lock(timeout=1.0):
            return {
                f"{_t('MQTTPhysicalPublishes.name')}_pct": Metrics.sigenergy2mqtt_mqtt_physical_publish_percentage,
                f"{_t('MQTTPublishFailures.name')}": Metrics.sigenergy2mqtt_mqtt_publish_failures,
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
    async def _diagnostics_collect_pvoutput_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest PVOutput metrics."""
        from sigenergy2mqtt.pvoutput import PVOutputSettings

        async with Metrics.lock(timeout=1.0):
            return {
                f"{_t('PVOutputUploadErrors.name')}": Metrics.sigenergy2mqtt_pvoutput_upload_errors,
                f"{_t('PVOutputUploadSkipped.name')}": Metrics.sigenergy2mqtt_pvoutput_upload_skipped,
                f"{_t('PVOutputUploadMax.name')}_ms": Metrics.sigenergy2mqtt_pvoutput_upload_max,
                f"{_t('PVOutputUploadMean.name')}_ms": Metrics.sigenergy2mqtt_pvoutput_upload_mean,
                f"{_t('PVOutputUploadMin.name')}_ms": Metrics.sigenergy2mqtt_pvoutput_upload_min if Metrics.sigenergy2mqtt_pvoutput_upload_min != float("inf") else 0.0,
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

    @classmethod
    async def _diagnostics_collect_state_store_metrics(cls) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest StateStore metrics."""
        async with Metrics.lock(timeout=1.0):
            return {
                f"{_t('StateStoreSaveMax.name')}_ms": Metrics.sigenergy2mqtt_state_store_save_max,
                f"{_t('StateStoreSaveMean.name')}_ms": Metrics.sigenergy2mqtt_state_store_save_mean,
                f"{_t('StateStoreSaveMin.name')}_ms": Metrics.sigenergy2mqtt_state_store_save_min if Metrics.sigenergy2mqtt_state_store_save_min != float("inf") else 0.0,
                f"{_t('StateStoreLoadHitPercentage.name')}": Metrics.sigenergy2mqtt_state_store_load_hit_percentage,
                f"{_t('StateStoreSaveErrors.name')}": Metrics.sigenergy2mqtt_state_store_save_errors,
                f"{_t('StateStoreLoadErrors.name')}": Metrics.sigenergy2mqtt_state_store_load_errors,
                f"{_t('StateStoreDeleteErrors.name')}": Metrics.sigenergy2mqtt_state_store_delete_errors,
                "config": {
                    "mqtt_redundancy": "yes" if active_config.persistence.mqtt_redundancy else "no",
                    "disk_primary": "yes" if active_config.persistence.disk_primary else "no",
                    "sync_timeout_secs": active_config.persistence.sync_timeout,
                },
            }
