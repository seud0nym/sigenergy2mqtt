import logging

from pymodbus import pymodbus_apply_logging_config

from sigenergy2mqtt.config import active_config, configure_root_logger
from sigenergy2mqtt.metrics import Metrics

logger = logging.getLogger(__name__)


class _FramerSkipFilter(logging.Filter):
    """Suppress dev-id / transaction-id mismatch noise from pymodbus framer.

    The check against ``active_config.modbus`` is intentionally deferred to
    filter-call time (not setup time) so that the correct ``log_skipped``
    values are used even when this filter is installed before
    ``initialize_async()`` has finished loading the YAML configuration.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # Suppress unless every configured device has explicitly opted in
        # to seeing these messages (log_skipped=True).  When no devices are
        # configured yet (early startup), apply the default suppression.
        if "request ask for " in msg and "Skipping." in msg and (not active_config.modbus or any(not device.log_skipped for device in active_config.modbus)):
            Metrics.modbus_skipped_error()
            return False
        return True


def configure_logging() -> None:
    """Configure the runtime logging environment."""
    # Configure root logger format/level via shared helper so logic is unified
    # with configure_root_logger() performed at import time.
    configure_root_logger(active_config.log_level, active_config.log_fmt)

    _configure_logger("sigenergy2mqtt", active_config.log_level)
    _configure_logger("sigenergy2mqtt.diagnostics", active_config.diagnostics.log_level)
    _configure_logger("sigenergy2mqtt.influxdb", active_config.influxdb.log_level)
    _configure_logger("sigenergy2mqtt.pvoutput", active_config.pvoutput.log_level)
    _configure_logger("sigenergy2mqtt.mqtt.client", active_config.mqtt.log_level)
    _configure_logger("sigenergy2mqtt.sensors.cloud", active_config.cloud.log_level)

    _configure_logger("paho.mqtt", active_config.mqtt.log_level)

    # We have to configure root logging before pymodbus so basicConfig wins the handler race
    modbus_log_level = active_config.modbus_log_level
    pymodbus_apply_logging_config(modbus_log_level)

    logger.debug("Applying skipped error logging filter to pymodbus.logging logger (modbus.log_skipped evaluated at message time)")
    _framer_skip_filter = _FramerSkipFilter()
    # Attach to the exact logger pymodbus.Log uses, AND to each of its handlers.
    # The logger-level filter is the primary gate: it prevents callHandlers() from
    # ever being reached, so no handler — present or future — can emit the record.
    _pymodbus_logging_logger = logging.getLogger("pymodbus.logging")
    _pymodbus_logging_logger.addFilter(_framer_skip_filter)
    for handler in _pymodbus_logging_logger.handlers:
        handler.addFilter(_framer_skip_filter)
    # Belt-and-suspenders: also cover root handlers in case propagation fires
    # before the logger-level filter takes effect on the first call.
    for handler in logging.getLogger().handlers:
        handler.addFilter(_framer_skip_filter)


def _configure_logger(name: str, level: int, *, propagate: bool = True) -> None:
    """Set an individual logger level/propagation and emit transition diagnostics.

    Side effects:

    - Mutates the named logger's effective level.
    - Optionally changes ``logger.propagate`` to control record bubbling.
    - Emits a log entry at the previous level when changing from a non-default level.
    """
    logger = logging.getLogger(name)
    if logger.level != level:
        if logger.level not in (logging.NOTSET, level):
            logger.log(logger.level, f"{name} log-level changed to {logging.getLevelName(level)}")
        logger.setLevel(level)
    logger.propagate = propagate
