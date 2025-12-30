import pytest
import time
import logging
from unittest.mock import MagicMock, patch
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.config import OutputField, StatusField
from sigenergy2mqtt.pvoutput.topic import Topic


@pytest.fixture
def mock_logger():
    return MagicMock(spec=logging.Logger)


def test_pvoutput_output_service_create_payload(mock_logger):
    # Setup Config mocks
    with patch("sigenergy2mqtt.pvoutput.service.Config") as mock_config:
        mock_config.pvoutput.exports = False
        mock_config.pvoutput.imports = False

        service = PVOutputOutputService(mock_logger, {})

        # Manually enable and register topic
        service_topic = service._service_topics[OutputField.GENERATION]
        service_topic.enabled = True
        topic = Topic("gen_topic", gain=1.0)
        service_topic.register(topic)

        # Set a state and timestamp for the topic
        topic.state = 5000.0
        topic.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

        now_struct = time.strptime("2023-10-27 12:05:00", "%Y-%m-%d %H:%M:%S")
        payload = service._create_payload(now_struct, interval=5)

        assert payload["d"] == "20231027"
        assert payload["g"] == 5000


def test_pvoutput_status_service_create_payload(mock_logger):
    # Setup Config mocks
    with patch("sigenergy2mqtt.pvoutput.service.Config"), patch("sigenergy2mqtt.pvoutput.status.Config") as mock_status_config:
        mock_status_config.pvoutput.consumption_enabled = True
        mock_status_config.pvoutput.temperature_topic = None
        mock_status_config.pvoutput.extended = {f: False for f in StatusField}

        service = PVOutputStatusService(mock_logger, {}, {})

        # Manually enable and register topic
        service_topic = service._service_topics[StatusField.GENERATION_ENERGY]
        service_topic.enabled = True
        topic = Topic("gen_energy_topic", gain=1.0)
        service_topic.register(topic)

        # Set a state and timestamp
        topic.state = 12345.0
        topic.timestamp = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")

        now_struct = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")
        payload, snapshot = service._create_payload(now_struct)

        assert payload["d"] == "20231027"
        assert payload["t"] == "12:00"
        assert payload["v1"] == 12345
