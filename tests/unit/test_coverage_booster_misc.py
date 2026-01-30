import logging
from unittest.mock import MagicMock, patch

import sigenergy2mqtt.__main__ as main_module
from sigenergy2mqtt.common.protocol import Protocol, ProtocolApplies
from sigenergy2mqtt.influxdb import get_influxdb_services


def test_protocol_applies_coverage():
    assert ProtocolApplies(Protocol.V1_8) == "2024-08-05"
    assert ProtocolApplies(Protocol.V2_0) == "2024-10-14"
    assert ProtocolApplies(Protocol.V2_4) == "2025-02-05"
    assert ProtocolApplies(Protocol.V2_5) == "2025-02-19"
    assert ProtocolApplies(Protocol.V2_6) == "2025-03-31"
    assert ProtocolApplies(Protocol.V2_7) == "2025-05-23"
    assert ProtocolApplies(Protocol.V2_8) == "2025-11-28"
    # Coverage for default case
    assert ProtocolApplies(Protocol.N_A) is not None


def test_get_influxdb_services_coverage():
    with patch("sigenergy2mqtt.influxdb.Config") as MockConfig:
        MockConfig.modbus = [MagicMock(), MagicMock()]  # 2 plants
        MockConfig.influxdb.log_level = logging.INFO

        services = get_influxdb_services([])
        assert len(services) == 2
        for svc in services:
            from sigenergy2mqtt.influxdb.influx_service import InfluxService

            assert isinstance(svc, InfluxService)


def test_main_wrapper_coverage():
    with patch("sigenergy2mqtt.__main__.asyncio.run") as mock_run, patch("sigenergy2mqtt.__main__.async_main") as mock_async_main, patch("sigenergy2mqtt.__main__.initialize"):
        main_module.main()
        mock_run.assert_called_once()
