import logging

from pymodbus import pymodbus_apply_logging_config

from sigenergy2mqtt.config import active_config, configure_root_logger
from sigenergy2mqtt.metrics import Metrics

logger = logging.getLogger(__name__)

# Module-level singleton so configure_logging() is idempotent: the same filter
# object is reused on every call, and _add_filter_once() ensures it is never
# attached to the same logger/handler more than once.
_framer_skip_filter: "_FramerSkipFilter | None" = None


class _FramerSkipFilter(logging.Filter):
    """..."""  # (docstring unchanged)

    def __init__(self) -> None:
        super().__init__()
        # True only while the immediately preceding record on this logger
        # was a Skipping match we suppressed (or a Repeating.... we suppressed
        # as a continuation of that same chain). Reset by any other record.
        self._chain_active = False

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        is_skip = "request ask for " in msg and "Skipping." in msg
        is_repeat = "Repeating...." in msg
        log_skipped = active_config.modbus and all(device.log_skipped for device in active_config.modbus)

        if is_skip:
            if log_skipped:
                self._chain_active = False
                return True
            Metrics.modbus_skipped_error()
            self._chain_active = True
            return False

        if is_repeat and self._chain_active:
            # pymodbus's Log de-dup (see pymodbus/logging.py: Log.build_msg)
            # substituted this literal text for a repeat of the immediately
            # preceding Skipping message we just suppressed above.
            if log_skipped:
                self._chain_active = False
                return True
            Metrics.modbus_skipped_error()
            return False  # chain stays open, in case of a further repeat

        # Anything else - including a "Repeating...." NOT chained to a
        # Skipping message we suppressed - ends the chain and passes through.
        self._chain_active = False
        return True


def configure_logging() -> None:
    """Configure the runtime logging environment."""
    global _framer_skip_filter

    # Configure root logger format/level via shared helper so logic is unified
    # with configure_root_logger() performed at import time.
    configure_root_logger(active_config.log_level, active_config.log_fmt)

    _configure_logger("sigenergy2mqtt", active_config.log_level)
    _configure_logger("sigenergy2mqtt.diagnostics", active_config.diagnostics.log_level)
    _configure_logger("sigenergy2mqtt.influxdb", active_config.influxdb.log_level)
    _configure_logger("sigenergy2mqtt.pvoutput", active_config.pvoutput.log_level)
    _configure_logger("sigenergy2mqtt.mqtt.client", active_config.mqtt.log_level)

    _configure_logger("paho.mqtt", active_config.mqtt.log_level)

    # We have to configure root logging before pymodbus so basicConfig wins the handler race
    modbus_log_level = active_config.modbus_log_level
    pymodbus_apply_logging_config(modbus_log_level)

    logger.debug("Applying skipped error logging filter to pymodbus.logging logger (modbus.log_skipped evaluated at message time)")
    if _framer_skip_filter is None:
        _framer_skip_filter = _FramerSkipFilter()
    # Attach to the exact logger pymodbus.Log uses, AND to each of its handlers.
    # The logger-level filter is the primary gate: it prevents callHandlers() from
    # ever being reached, so no handler — present or future — can emit the record.
    _pymodbus_logging_logger = logging.getLogger("pymodbus.logging")
    _add_filter_once(_pymodbus_logging_logger, _framer_skip_filter)
    for handler in _pymodbus_logging_logger.handlers:
        _add_filter_once(handler, _framer_skip_filter)
    # Belt-and-suspenders: also cover root handlers in case propagation fires
    # before the logger-level filter takes effect on the first call.
    for handler in logging.getLogger().handlers:
        _add_filter_once(handler, _framer_skip_filter)


def _add_filter_once(target: logging.Logger | logging.Handler, f: logging.Filter) -> None:
    """Add *f* to *target* only if it is not already present."""
    if f not in target.filters:
        target.addFilter(f)


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
