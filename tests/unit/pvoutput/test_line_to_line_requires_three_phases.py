"""pvoutput.voltage = l/l-avg is a configuration error on a system that is not three-phase."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sigenergy2mqtt.__main__ as main_mod
from sigenergy2mqtt.common import VoltageSource
from sigenergy2mqtt.config import ConfigurationError, active_config
from sigenergy2mqtt.main.validation import (
    _validate_line_to_line_voltage,
    _validate_modbus_connections,
)
from sigenergy2mqtt.pvoutput import get_pvoutput_services
from sigenergy2mqtt.sensors.inverter.read_only import OutputType


def _plant(power_phases: int | None) -> MagicMock:
    plant = MagicMock()
    plant.name = "Sigenergy Plant"
    plant.plant_index = 0
    plant.power_phases = power_phases
    plant.get_all_sensors.return_value = {}
    return plant


def _configs(*devices) -> list:
    return [SimpleNamespace(devices=list(devices))]


@pytest.fixture
def pvoutput_enabled():
    with patch.object(active_config.pvoutput, "enabled", True):
        yield


@pytest.mark.parametrize("phases", [1, 2])
def test_services_reject_line_to_line_on_fewer_than_three_phases(pvoutput_enabled, phases):
    with patch.object(active_config.pvoutput, "voltage", VoltageSource.L_L_AVG):
        with pytest.raises(ConfigurationError) as exc:
            get_pvoutput_services(_configs(_plant(phases)))
    message = str(exc.value)
    assert "pvoutput.voltage" in message and "l/l-avg" in message
    assert "Sigenergy Plant" in message and "plant index 0" in message
    assert "three-phase" in message


def test_services_reject_if_any_plant_is_not_three_phase(pvoutput_enabled):
    with patch.object(active_config.pvoutput, "voltage", VoltageSource.L_L_AVG):
        with pytest.raises(ConfigurationError):
            get_pvoutput_services(_configs(_plant(3), _plant(1)))


@pytest.mark.parametrize("phases", [3, None])
def test_services_accept_line_to_line_on_three_phases(pvoutput_enabled, phases):
    with patch.object(active_config.pvoutput, "voltage", VoltageSource.L_L_AVG):
        assert len(get_pvoutput_services(_configs(_plant(phases)))) == 2


@pytest.mark.parametrize("voltage", [VoltageSource.L_N_AVG, VoltageSource.PHASE_A, VoltageSource.PV])
def test_other_voltage_sources_are_fine_on_single_phase(pvoutput_enabled, voltage):
    with patch.object(active_config.pvoutput, "voltage", voltage):
        assert len(get_pvoutput_services(_configs(_plant(1)))) == 2


def test_phase_voltage_topics_carry_their_phase(pvoutput_enabled):
    from sigenergy2mqtt.common import StatusField
    from sigenergy2mqtt.sensors.inverter.read_only import PhaseVoltage

    sensors = {}
    for phase in ("C", "A", "B"):
        sensor = MagicMock(spec=PhaseVoltage)
        sensor.publishable = True
        sensor.phase = phase
        sensor.scan_interval = 60
        sensor.state_topic = f"state/{phase}"
        sensor.raw_state_topic = f"raw/{phase}"
        sensors[phase] = sensor
    plant = _plant(3)
    plant.get_all_sensors.return_value = sensors
    with patch.object(active_config.pvoutput, "voltage", VoltageSource.L_L_AVG):
        status = get_pvoutput_services(_configs(plant))[0]
    topics = status._service_topics[StatusField.VOLTAGE]
    assert {t.topic: t.phase for t in topics.values()} == {"state/A": "A", "state/B": "B", "state/C": "C"}


# --------------------------------------------------------------------------- main()


def test_main_exits_1_without_traceback_on_runtime_configuration_error(monkeypatch, caplog):
    async def failing_async_main():
        raise ConfigurationError("pvoutput.voltage is 'l/l-avg' but the plant has 1 phase")

    monkeypatch.setattr(main_mod, "initialize", lambda: True)
    monkeypatch.setattr(main_mod, "active_config", SimpleNamespace(validate_only_mode=False, log_level=20))
    monkeypatch.setattr(main_mod, "async_main", failing_async_main)
    monkeypatch.setattr(main_mod.Metrics, "shutdown", MagicMock())

    with pytest.raises(SystemExit) as exc:
        main_mod.main()

    assert exc.value.code == 1
    main_mod.Metrics.shutdown.assert_called_once()
    records = [r for r in caplog.records if "Configuration error" in r.message]
    assert len(records) == 1
    assert records[0].levelname == "CRITICAL"
    assert records[0].exc_info is None
    assert "l/l-avg" in records[0].message


def test_main_returns_normally_on_clean_shutdown(monkeypatch):
    async def ok_async_main():
        return None

    monkeypatch.setattr(main_mod, "initialize", lambda: True)
    monkeypatch.setattr(main_mod, "active_config", SimpleNamespace(validate_only_mode=False, log_level=20))
    monkeypatch.setattr(main_mod, "async_main", ok_async_main)
    monkeypatch.setattr(main_mod.Metrics, "shutdown", MagicMock())
    assert main_mod.main() is None


# --------------------------------------------------------------------------- --validate


def _client(output_type: int | None = None, error: Exception | None = None) -> MagicMock:
    client = MagicMock()
    client.connect = AsyncMock()
    client.connected = True
    if error is not None:
        client.read_input_registers = AsyncMock(side_effect=error)
    else:
        response = MagicMock()
        response.isError.return_value = output_type is None
        response.registers = [] if output_type is None else [output_type]
        client.read_input_registers = AsyncMock(return_value=response)
    return client


@pytest.fixture
def ll_avg(pvoutput_enabled):
    with patch.object(active_config.pvoutput, "voltage", VoltageSource.L_L_AVG):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize("output_type", [0, 3, 4])  # L/N, L1/L2/N, L1/L2
async def test_validate_rejects_line_to_line_when_not_three_phase(ll_avg, output_type):
    client = _client(output_type)
    with pytest.raises(ConfigurationError, match="requires a three-phase system"):
        await _validate_line_to_line_voltage(client, 0, "1.2.3.4", 502, [1])
    client.read_input_registers.assert_awaited_once_with(OutputType.ADDRESS, count=1, device_id=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("output_type", [1, 2])  # L1/L2/L3, L1/L2/L3/N
async def test_validate_accepts_line_to_line_when_three_phase(ll_avg, output_type):
    await _validate_line_to_line_voltage(_client(output_type), 0, "1.2.3.4", 502, [1])


@pytest.mark.asyncio
@pytest.mark.parametrize("client", [_client(None), _client(error=TimeoutError("no reply")), _client(99)])
async def test_validate_warns_but_continues_when_output_type_unreadable(ll_avg, client, caplog):
    await _validate_line_to_line_voltage(client, 0, "1.2.3.4", 502, [1])
    assert "Unable to read the output type" in caplog.text


@pytest.mark.asyncio
async def test_validate_skips_the_read_unless_line_to_line_is_configured(pvoutput_enabled):
    client = _client(0)
    with patch.object(active_config.pvoutput, "voltage", VoltageSource.L_N_AVG):
        await _validate_line_to_line_voltage(client, 0, "1.2.3.4", 502, [1])
    with patch.object(active_config.pvoutput, "voltage", VoltageSource.L_L_AVG):
        await _validate_line_to_line_voltage(client, 0, "1.2.3.4", 502, [])
        with patch.object(active_config.pvoutput, "enabled", False):
            await _validate_line_to_line_voltage(client, 0, "1.2.3.4", 502, [1])
    client.read_input_registers.assert_not_called()


@pytest.mark.asyncio
async def test_validate_modbus_connections_runs_the_check_and_closes_the_client(ll_avg):
    modbus = MagicMock()
    modbus.host, modbus.port, modbus.timeout, modbus.retries, modbus.inverters = "1.2.3.4", 502, 1, 1, [1]
    client = _client(0)
    with patch("sigenergy2mqtt.config.active_config.modbus", [modbus]), patch("sigenergy2mqtt.main.validation.ModbusClient", return_value=client):
        with pytest.raises(ConfigurationError):
            await _validate_modbus_connections()
    client.close.assert_called_once()
