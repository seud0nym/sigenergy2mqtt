import logging
from unittest.mock import MagicMock, patch

import pytest

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


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_influxdb_services_coverage():
    from sigenergy2mqtt.config import Config
    from sigenergy2mqtt.config.config import _swap_active_config

    with _swap_active_config(Config()) as cfg:
        cfg.modbus = [MagicMock(), MagicMock()]  # 2 plants
        cfg.influxdb.log_level = logging.INFO

        services = get_influxdb_services()
        assert len(services) == 2
        for svc in services:
            from sigenergy2mqtt.influxdb.influx_service import InfluxService

            assert isinstance(svc, InfluxService)


def test_main_wrapper_coverage():
    with (
        patch("sigenergy2mqtt.__main__.asyncio.run") as mock_run,
        patch("sigenergy2mqtt.__main__.async_main", new_callable=MagicMock, return_value=None) as mock_async_main,  # noqa: F841
        patch("sigenergy2mqtt.__main__.initialize"),
    ):
        main_module.main()
        mock_run.assert_called_once()


def test_main_validate_path_coverage(monkeypatch):
    monkeypatch.setattr(main_module, "initialize", lambda: True)
    main_module.active_config.validate_only_mode = "standard"
    main_module.active_config.validate_show_credentials = True

    with (
        patch("sigenergy2mqtt.__main__.asyncio.run") as mock_run,
        patch("sigenergy2mqtt.__main__.validate_connections", new_callable=MagicMock, return_value=None),
        patch("sigenergy2mqtt.__main__.async_main", new_callable=MagicMock, return_value=None),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main_module.main()
        assert exc_info.value.code == 0
        mock_run.assert_called_once()


def test_validate_connections_invokes_smartport_validation(monkeypatch):
    calls: list[str] = []

    async def _modbus():
        calls.append("modbus")

    def _smartport(show_credentials: bool):
        calls.append(f"smartport:{show_credentials}")

    def _mqtt(show_credentials: bool):
        calls.append(f"mqtt:{show_credentials}")

    def _influx(show_credentials: bool):
        calls.append(f"influx:{show_credentials}")

    def _pvoutput(show_credentials: bool):
        calls.append(f"pvoutput:{show_credentials}")

    monkeypatch.setattr("sigenergy2mqtt.main.main._validate_modbus_connections", _modbus)
    monkeypatch.setattr("sigenergy2mqtt.main.main._validate_smartport_connections", _smartport)
    monkeypatch.setattr("sigenergy2mqtt.main.main._validate_mqtt_connection", _mqtt)
    monkeypatch.setattr("sigenergy2mqtt.main.main._validate_influxdb_connection", _influx)
    monkeypatch.setattr("sigenergy2mqtt.main.main._validate_pvoutput_connection", _pvoutput)

    import asyncio

    asyncio.run(main_module.validate_connections(show_credentials=True))

    assert calls == ["modbus", "smartport:True", "mqtt:True", "influx:True", "pvoutput:True"]


def test_main_validate_reinstalls_default_sigint(monkeypatch):
    monkeypatch.setattr(main_module, "initialize", lambda: True)
    main_module.active_config.validate_only_mode = "standard"
    main_module.active_config.validate_show_credentials = False

    with (
        patch("sigenergy2mqtt.__main__.signal.signal") as mock_signal,
        patch("sigenergy2mqtt.__main__.asyncio.run"),
        patch("sigenergy2mqtt.__main__.validate_connections", new_callable=MagicMock),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main_module.main()

    assert exc_info.value.code == 0
    assert (main_module.signal.SIGINT, main_module.signal.default_int_handler) in [c.args for c in mock_signal.call_args_list]


def test_validate_pvoutput_connection_skips_when_testing(monkeypatch):
    from sigenergy2mqtt.main import main as main_mod

    monkeypatch.setattr(main_mod.active_config.pvoutput, "enabled", True, raising=False)
    monkeypatch.setattr(main_mod.active_config.pvoutput, "testing", True, raising=False)

    with patch("sigenergy2mqtt.main.main.requests.get") as mock_get:
        main_mod._validate_pvoutput_connection(show_credentials=False)

    mock_get.assert_not_called()


def test_main_validate_logs_config_yaml(monkeypatch):
    monkeypatch.setattr(main_module, "initialize", lambda: True)
    main_module.active_config.validate_only_mode = "standard"
    main_module.active_config.validate_show_credentials = False

    with (
        patch("sigenergy2mqtt.__main__.logging.info") as mock_info,
        patch("sigenergy2mqtt.__main__.asyncio.run"),
        patch("sigenergy2mqtt.__main__.validate_connections", new_callable=MagicMock),
    ):
        with pytest.raises(SystemExit):
            main_module.main()

    assert any(call.args and call.args[0] == "Validation configuration:\n%s" for call in mock_info.call_args_list)
