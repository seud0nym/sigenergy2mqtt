import logging

from sigenergy2mqtt.common.outage import active_outages
from sigenergy2mqtt.config import active_config, configure_root_logger
from sigenergy2mqtt.metrics import Metrics

logger = logging.getLogger(__name__)

# Module-level singleton so configure_logging() is idempotent: the same filter
# object is reused on every call, and _add_filter_once() ensures it is never
# attached to the same logger/handler more than once.
_framer_skip_filter: "_FramerSkipFilter | None" = None
_frame_dump_filter: "_FrameDumpFilter | None" = None
_modbus_outage_filter: "_OutageDemotionFilter | None" = None
_mqtt_outage_filter: "_OutageDemotionFilter | None" = None

PYMODBUS_LOGGER = "pymodbus.logging"
MQTT_CLIENT_LOGGER = "sigenergy2mqtt.mqtt.client"


class _FramerSkipFilter(logging.Filter):
    """Suppress pymodbus "Skipping." error records (and their "Repeating...."
    duplicates) when the user has not opted in to skipped-error logging.

    pymodbus emits DEBUG-level transport-dump records ("send: …" / "recv: …
    extra data: …") between the initial Skipping error and the subsequent
    "Repeating…." record that represents a repeat of that same error.  Those
    transport records must not break the suppression chain, so they are treated
    as chain-transparent: they pass through without resetting ``_chain_active``.
    """

    # Prefixes used by pymodbus Log.build_frame_log_line() for transport dumps.
    _TRANSPORT_PREFIXES = ("send: ", "recv: ", "extra: ")

    def __init__(self) -> None:
        super().__init__()
        # True only while the immediately preceding *non-transport* record on
        # this logger was a Skipping match we suppressed (or a Repeating....
        # we suppressed as a continuation of that same chain).  Transport-dump
        # DEBUG records are transparent and do not alter this flag.
        self._chain_active = False

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        is_skip = "request ask for " in msg and "Skipping." in msg
        is_repeat = "Repeating...." in msg
        try:
            log_skipped = bool(active_config.modbus) and all(device.log_skipped for device in active_config.modbus)
        except AttributeError:
            log_skipped = False

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

        # Transport-dump records (send:/recv:/extra: DEBUG lines emitted by
        # Log.transport_dump) appear between a Skipping error and its
        # subsequent Repeating.... record.  They are not skip-related, so they
        # always pass through, but they must NOT reset the suppression chain.
        if self._chain_active and any(msg.startswith(pfx) for pfx in self._TRANSPORT_PREFIXES):
            return True

        # Anything else - including a "Repeating...." NOT chained to a
        # Skipping message we suppressed - ends the chain and passes through.
        self._chain_active = False
        return True


class _FrameDumpFilter(logging.Filter):
    """Strip the frame dump that pymodbus appends to ERROR/CRITICAL records.

    When its logger is not enabled for DEBUG, pymodbus appends the last 20
    send/recv frames to every error message, each on its own ``>>>>>`` line.
    Log collectors (Docker, syslog) split those into separate records, turning
    one timeout into ~20 lines of hex.  The dump is only useful when debugging
    the protocol, and at DEBUG level pymodbus logs the frames as they happen,
    so the appended copy is dropped here.
    """

    MARKER = "\n>>>>> "

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if self.MARKER in msg:
            record.msg = msg.split(self.MARKER, 1)[0]
            record.args = None
        return True


class _OutageDemotionFilter(logging.Filter):
    """Demote third-party connectivity errors to DEBUG while an outage is active.

    Libraries (pymodbus, paho) log their own error for every failed request.
    Once an :class:`~sigenergy2mqtt.common.outage.OutageTracker` has reported
    the outage, those records add nothing, so matching records are demoted to
    DEBUG (or dropped if the logger is not enabled for DEBUG) and counted as
    suppressed.

    Args:
        logger_name: The logger this filter is attached to.
        resource_prefix: Prefix of the outage tracker resources to consult,
            e.g. ``modbus://``.
        patterns: Substrings identifying connectivity-related messages.
    """

    def __init__(self, logger_name: str, resource_prefix: str, patterns: tuple[str, ...]) -> None:
        super().__init__()
        self._logger_name = logger_name
        self._prefix = resource_prefix
        self._patterns = patterns

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno <= logging.DEBUG:
            return True
        msg = record.getMessage()
        if not any(p in msg for p in self._patterns):
            return True
        outages = active_outages(self._prefix)
        if not outages:
            return True
        outages[0].suppress()
        if not logging.getLogger(self._logger_name).isEnabledFor(logging.DEBUG):
            return False
        record.levelno = logging.DEBUG
        record.levelname = logging.getLevelName(logging.DEBUG)
        return True


# Connectivity messages logged by pymodbus for each failed request.
_PYMODBUS_OUTAGE_PATTERNS = (
    "No response received",
    "Cancel send, because not connected",
    "Not connected, trying to connect",
    "Failed to connect",
    "Connection to (",
)

# Logged by paho's network loop while the socket is gone.
_PAHO_OUTAGE_PATTERNS = ("Client is not connected",)


def configure_logging() -> None:
    """Configure the runtime logging environment."""
    global _framer_skip_filter, _frame_dump_filter, _modbus_outage_filter, _mqtt_outage_filter

    # Configure root logger format/level via shared helper so logic is unified
    # with configure_root_logger() performed at import time.
    configure_root_logger(active_config.log_level, active_config.log_fmt)

    _configure_logger("sigenergy2mqtt", active_config.log_level)
    _configure_logger("sigenergy2mqtt.cloud", active_config.cloud.log_level)
    _configure_logger("sigenergy2mqtt.diagnostics", active_config.diagnostics.log_level)
    _configure_logger("sigenergy2mqtt.influxdb", active_config.influxdb.log_level)
    _configure_logger("sigenergy2mqtt.pvoutput", active_config.pvoutput.log_level)
    _configure_logger("sigenergy2mqtt.mqtt.client", active_config.mqtt.log_level)

    _configure_logger("paho.mqtt", active_config.mqtt.log_level)

    # Only the level of the pymodbus logger is set. pymodbus_apply_logging_config()
    # is deliberately NOT used: it adds its own StreamHandler to the pymodbus
    # logger, while records still propagate to the root handler, so every
    # pymodbus message would be written twice (once in each format).
    _configure_logger(PYMODBUS_LOGGER, active_config.modbus_log_level)

    logger.debug("Applying skipped error logging filter to pymodbus.logging logger (modbus.log_skipped evaluated at message time)")
    if _framer_skip_filter is None:
        _framer_skip_filter = _FramerSkipFilter()
    # Attach to the exact logger pymodbus.Log uses, AND to each of its handlers.
    # The logger-level filter is the primary gate: it prevents callHandlers() from
    # ever being reached, so no handler — present or future — can emit the record.
    _pymodbus_logging_logger = logging.getLogger(PYMODBUS_LOGGER)
    _add_filter_once(_pymodbus_logging_logger, _framer_skip_filter)
    for handler in _pymodbus_logging_logger.handlers:
        _add_filter_once(handler, _framer_skip_filter)
    # Belt-and-suspenders: also cover root handlers in case propagation fires
    # before the logger-level filter takes effect on the first call.
    for handler in logging.getLogger().handlers:
        _add_filter_once(handler, _framer_skip_filter)

    if _frame_dump_filter is None:
        _frame_dump_filter = _FrameDumpFilter()
    if _modbus_outage_filter is None:
        _modbus_outage_filter = _OutageDemotionFilter(PYMODBUS_LOGGER, "modbus://", _PYMODBUS_OUTAGE_PATTERNS)
    if _mqtt_outage_filter is None:
        _mqtt_outage_filter = _OutageDemotionFilter(MQTT_CLIENT_LOGGER, "mqtt://", _PAHO_OUTAGE_PATTERNS)
    _add_filter_once(_pymodbus_logging_logger, _frame_dump_filter)
    _add_filter_once(_pymodbus_logging_logger, _modbus_outage_filter)
    _add_filter_once(logging.getLogger(MQTT_CLIENT_LOGGER), _mqtt_outage_filter)


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
