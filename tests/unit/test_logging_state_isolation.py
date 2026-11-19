"""Regression tests for the ``restore_logging_state`` fixture in tests/conftest.py.

The two tests are order-dependent by design: the first leaves state behind on a
logger that is created during the test, and the second verifies the autouse
fixture cleaned it up.
"""

import logging

NEW_LOGGER = "sigenergy2mqtt.test_isolation_new_logger"


def test_new_logger_is_modified():
    assert NEW_LOGGER not in logging.root.manager.loggerDict or not logging.getLogger(NEW_LOGGER).handlers
    lg = logging.getLogger(NEW_LOGGER)
    lg.setLevel(logging.ERROR)
    lg.propagate = False
    lg.addFilter(lambda record: False)
    lg.addHandler(logging.NullHandler())


def test_new_logger_state_is_reset():
    lg = logging.getLogger(NEW_LOGGER)
    assert lg.level == logging.NOTSET
    assert lg.propagate is True
    assert lg.filters == []
    assert lg.handlers == []
