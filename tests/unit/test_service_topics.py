import pytest
import time
import logging
import math
from unittest.mock import MagicMock, patch
from sigenergy2mqtt.pvoutput.service_topics import ServiceTopics, Calculation
from sigenergy2mqtt.pvoutput.topic import Topic
from sigenergy2mqtt.config import OutputField, StatusField


@pytest.fixture
def mock_logger():
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def mock_service():
    service = MagicMock()
    service.unique_id = "test_service"
    service.lock = MagicMock()

    # Mocking the async context manager for self.lock
    @patch("sigenergy2mqtt.pvoutput.service.Service.lock")
    async def mock_lock(*args, **kwargs):
        pass

    service.lock.return_value.__aenter__.return_value = None
    return service


def test_calculation_sum(mock_service, mock_logger):
    service_topics = ServiceTopics(service=mock_service, enabled=True, logger=mock_logger, value_key=OutputField.GENERATION, calc=Calculation.SUM)

    t1 = Topic("topic1", gain=1.0)
    t1.state = 100.0
    t1.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    t2 = Topic("topic2", gain=2.0)
    t2.state = 50.0
    t2.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    service_topics.register(t1)
    service_topics.register(t2)

    total, at, count = service_topics.aggregate(exclude_zero=False)

    # 100*1.0 + 50*2.0 = 200.0
    assert total == 200.0
    assert count == 2
    assert at == "12:00"


def test_calculation_average(mock_service, mock_logger):
    service_topics = ServiceTopics(service=mock_service, enabled=True, logger=mock_logger, value_key=StatusField.VOLTAGE, calc=Calculation.AVERAGE, decimals=1)

    t1 = Topic("v1", gain=1.0)
    t1.state = 230.0
    t1.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    t2 = Topic("v2", gain=1.0)
    t2.state = 240.0
    t2.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    service_topics.register(t1)
    service_topics.register(t2)

    payload = {}
    service_topics.add_to_payload(payload, interval_minutes=5, now=time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S"))

    # (230 + 240) / 2 = 235.0
    assert payload["v6"] == 235.0


def test_calculation_difference(mock_service, mock_logger):
    service_topics = ServiceTopics(service=mock_service, enabled=True, logger=mock_logger, value_key=StatusField.GENERATION_ENERGY, calc=Calculation.DIFFERENCE)

    t1 = Topic("energy", gain=1.0)
    service_topics.register(t1)

    # First update: set previous state
    t1.previous_state = 1000.0
    t1.previous_timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    # Second update: current state
    t1.state = 1050.0
    t1.timestamp = time.strptime("2023-10-27 12:05:00", "%Y-%m-%d %H:%M:%S")

    total, at, count = service_topics.aggregate(exclude_zero=False)

    # 1050 - 1000 = 50.0
    assert total == 50.0
    assert count == 1


def test_calculation_difference_convert_to_watts(mock_service, mock_logger):
    service_topics = ServiceTopics(service=mock_service, enabled=True, logger=mock_logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)

    t1 = Topic("energy", gain=1.0)
    service_topics.register(t1)

    # energy is in Wh
    t1.previous_state = 1000.0
    t1.previous_timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    # 5 minutes later, 50Wh consumed
    t1.state = 1050.0
    t1.timestamp = time.strptime("2023-10-27 12:05:00", "%Y-%m-%d %H:%M:%S")

    total, at, count = service_topics.aggregate(exclude_zero=False)

    # Difference = 50Wh
    # Hours = 5 / 60 = 0.08333
    # Power = 50 / (5/60) = 50 * 12 = 600W
    assert pytest.approx(total) == 600.0


def test_calculation_sum_difference_convert_to_watts(mock_service, mock_logger):
    # Testing Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS
    # (SUM is the default if not AVERAGE or L_L_AVG)
    service_topics = ServiceTopics(service=mock_service, enabled=True, logger=mock_logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)

    t1 = Topic("energy1", gain=1.0)
    t2 = Topic("energy2", gain=1.0)
    service_topics.register(t1)
    service_topics.register(t2)

    t1.previous_state = 1000.0
    t1.previous_timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")
    t1.state = 1050.0
    t1.timestamp = time.strptime("2023-10-27 12:05:00", "%Y-%m-%d %H:%M:%S")

    t2.previous_state = 2000.0
    t2.previous_timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")
    t2.state = 2100.0
    t2.timestamp = time.strptime("2023-10-27 12:05:00", "%Y-%m-%d %H:%M:%S")

    total, at, count = service_topics.aggregate(exclude_zero=False)

    # t1: (1050-1000) / (5/60) = 600W
    # t2: (2100-2000) / (5/60) = 1200W
    # Total = 600 + 1200 = 1800W
    assert pytest.approx(total) == 1800.0


def test_calculation_l_l_avg(mock_service, mock_logger):
    service_topics = ServiceTopics(service=mock_service, enabled=True, logger=mock_logger, value_key=StatusField.VOLTAGE, calc=Calculation.L_L_AVG, decimals=1)

    t1 = Topic("v1", gain=1.0)
    t1.state = 230.0
    t1.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    t2 = Topic("v2", gain=1.0)
    t2.state = 230.0
    t2.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

    service_topics.register(t1)
    service_topics.register(t2)

    # Formula: sqrt(sum(states^2)) / sqrt(3)
    # sqrt(230^2 + 230^2) / sqrt(3)
    # sqrt(52900 + 52900) / sqrt(3)
    # sqrt(105800) / sqrt(3) = 325.269... / 1.732... = 187.8
    # Wait, let me check the code:
    # payload[value_key.value] = round(math.sqrt(total) / math.sqrt(3), self._decimals if self._decimals > 0 else None)
    # where total = sum(state^2 * gain)

    payload = {}
    service_topics.add_to_payload(payload, interval_minutes=5, now=time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S"))

    expected = round(math.sqrt(230**2 + 230**2) / math.sqrt(3), 1)
    assert payload["v6"] == expected
