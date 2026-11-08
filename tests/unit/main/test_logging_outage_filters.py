import logging
from unittest.mock import PropertyMock, patch

from pymodbus.logging import Log

from sigenergy2mqtt.common.outage import outage_tracker
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.main.logging_setup import (
    MQTT_CLIENT_LOGGER,
    PYMODBUS_LOGGER,
    _FrameDumpFilter,
    _OutageDemotionFilter,
    configure_logging,
)


def _record(msg, level=logging.ERROR, name=PYMODBUS_LOGGER, args=None):
    return logging.LogRecord(name, level, "pathname", 1, msg, args, None)


class TestFrameDumpFilter:
    def test_strips_appended_frames(self):
        record = _record("No response received after 3 retries, continue with next request\n>>>>> send: 0x1 0x2\n>>>>> recv: 0x3 extra data:\n>>>>> None")
        assert _FrameDumpFilter().filter(record) is True
        assert record.getMessage() == "No response received after 3 retries, continue with next request"

    def test_strips_frames_from_repeating_marker(self):
        record = _record("Repeating....\n>>>>> send: 0x1")
        _FrameDumpFilter().filter(record)
        assert record.getMessage() == "Repeating...."

    def test_formats_args_before_stripping(self):
        record = _record("Connection to (%s, %s) failed\n>>>>> send: 0x1", args=("h", 502))
        _FrameDumpFilter().filter(record)
        assert record.getMessage() == "Connection to (h, 502) failed"
        assert record.args is None

    def test_leaves_other_messages_untouched(self):
        record = _record("plain %s", args=("message",))
        _FrameDumpFilter().filter(record)
        assert record.msg == "plain %s"
        assert record.getMessage() == "plain message"


class TestOutageDemotionFilter:
    def _filter(self):
        return _OutageDemotionFilter(PYMODBUS_LOGGER, "modbus://", ("No response received",))

    def test_passes_through_without_outage(self):
        record = _record("No response received after 3 retries")
        assert self._filter().filter(record) is True
        assert record.levelno == logging.ERROR

    def test_drops_matching_record_during_outage_when_debug_disabled(self):
        tracker = outage_tracker("modbus://h:502")
        tracker.failure("down")
        logging.getLogger(PYMODBUS_LOGGER).setLevel(logging.INFO)
        assert self._filter().filter(_record("No response received after 3 retries")) is False
        assert tracker.suppressed == 1

    def test_demotes_matching_record_during_outage_when_debug_enabled(self):
        outage_tracker("modbus://h:502").failure("down")
        logging.getLogger(PYMODBUS_LOGGER).setLevel(logging.DEBUG)
        try:
            record = _record("No response received after 3 retries")
            assert self._filter().filter(record) is True
            assert record.levelno == logging.DEBUG
            assert record.levelname == "DEBUG"
        finally:
            logging.getLogger(PYMODBUS_LOGGER).setLevel(logging.NOTSET)

    def test_non_matching_record_passes_during_outage(self):
        outage_tracker("modbus://h:502").failure("down")
        record = _record("ERROR: request ask for id=1 but got id=2, Skipping.")
        assert self._filter().filter(record) is True
        assert record.levelno == logging.ERROR

    def test_ignores_outages_of_other_resources(self):
        outage_tracker("mqtt://b:1883").failure("down")
        assert self._filter().filter(_record("No response received")) is True

    def test_debug_records_untouched(self):
        outage_tracker("modbus://h:502").failure("down")
        record = _record("No response received", level=logging.DEBUG)
        assert self._filter().filter(record) is True


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


def _capture(logger_name):
    """Attach a handler directly to *logger_name* (configure_logging() replaces root handlers, so caplog cannot be used)."""
    handler = _ListHandler()
    logging.getLogger(logger_name).addHandler(handler)
    return handler


class TestConfigureLoggingPymodbus:
    def _configure(self):
        with patch.object(type(active_config), "modbus_log_level", new_callable=PropertyMock, return_value=logging.WARNING):
            configure_logging()

    def test_no_pymodbus_stream_handler_added(self):
        pymodbus_logger = logging.getLogger(PYMODBUS_LOGGER)
        before = list(pymodbus_logger.handlers)
        self._configure()
        self._configure()
        assert pymodbus_logger.handlers == before
        assert pymodbus_logger.level == logging.WARNING
        assert pymodbus_logger.propagate is True

    def test_filters_attached_once(self):
        self._configure()
        self._configure()
        pymodbus_filters = [type(f).__name__ for f in logging.getLogger(PYMODBUS_LOGGER).filters]
        assert pymodbus_filters.count("_FrameDumpFilter") == 1
        assert pymodbus_filters.count("_OutageDemotionFilter") == 1
        mqtt_filters = [type(f).__name__ for f in logging.getLogger(MQTT_CLIENT_LOGGER).filters]
        assert mqtt_filters.count("_OutageDemotionFilter") == 1

    def test_pymodbus_error_logged_once_without_frame_dump(self):
        self._configure()
        handler = _capture(PYMODBUS_LOGGER)
        try:
            Log.frame_dump = [(Log.SEND_DATA, b"\x01\x02", b""), (Log.RECV_DATA, b"\x03", b"")]
            Log.last_log_text = ""
            Log.error("No response received after 3 retries, continue with next request")
        finally:
            logging.getLogger(PYMODBUS_LOGGER).removeHandler(handler)
        assert [r.getMessage() for r in handler.records] == ["No response received after 3 retries, continue with next request"]

    def test_pymodbus_connectivity_errors_suppressed_during_outage(self):
        self._configure()
        handler = _capture(PYMODBUS_LOGGER)
        try:
            outage_tracker("modbus://h:502").failure("down")
            Log.last_log_text = ""
            Log.error("Cancel send, because not connected!")
        finally:
            logging.getLogger(PYMODBUS_LOGGER).removeHandler(handler)
        assert handler.records == []

    def test_paho_not_connected_suppressed_during_mqtt_outage(self):
        self._configure()
        mqtt_logger = logging.getLogger(MQTT_CLIENT_LOGGER)
        handler = _capture(MQTT_CLIENT_LOGGER)
        try:
            mqtt_logger.error("Client is not connected. Socket: None). Last known Connection State: MQTT_CS_CONNECTING")
            outage_tracker("mqtt://b:1883").failure("Unspecified error")
            mqtt_logger.error("Client is not connected. Socket: None). Last known Connection State: MQTT_CS_CONNECTING")
        finally:
            mqtt_logger.removeHandler(handler)
        assert len([r for r in handler.records if r.levelno >= logging.WARNING]) == 1
