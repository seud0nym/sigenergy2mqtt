"""Tests designed specifically to boost coverage in sigenergy2mqtt/pvoutput."""

import logging
import math
import time
from unittest.mock import MagicMock, PropertyMock, mock_open, patch

import pytest

from sigenergy2mqtt.config import Config, ConsumptionSource, OutputField, StatusField, VoltageSource
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, TimePeriodServiceTopics, Topic
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.sensors.base import TypedSensorMixin
from sigenergy2mqtt.sensors.const import UnitOfEnergy
from sigenergy2mqtt.sensors.inverter_read_only import DailyChargeEnergy, DailyDischargeEnergy, PhaseVoltage, PVVoltageSensor
from sigenergy2mqtt.sensors.plant_derived import GridSensorDailyExportEnergy, GridSensorDailyImportEnergy, TotalDailyPVEnergy, TotalLifetimePVEnergy, TotalPVPower
from sigenergy2mqtt.sensors.plant_read_only import (
    ESSTotalChargedEnergy,
    ESSTotalDischargedEnergy,
    PlantBatterySoC,
    PlantPVPower,
    PlantRatedEnergyCapacity,
    PlantTotalImportedEnergy,
    TotalLoadConsumption,
    TotalLoadDailyConsumption,
)

# region topic.py coverage


def test_topic_json_encoding_decoding():
    """Hits topic.py:25, 33."""
    ts = list(time.localtime())
    t_dict = {"topic": "test", "gain": 1.0, "state": 10.0, "timestamp": ts, "previous_state": 5.0, "previous_timestamp": ts}

    decoded = Topic.json_decoder(t_dict)
    assert isinstance(decoded.previous_timestamp, time.struct_time)

    with pytest.raises(TypeError):
        Topic.json_encoder(object())


# endregion


# region service_topics.py coverage


@pytest.mark.asyncio
async def test_calculation_complex_logic():
    """Hits DIFFERENCE, CONVERT_TO_WATTS, and calc_debug_logging paths in service_topics.py."""
    logger = logging.getLogger("test-coverage")
    svc = MagicMock()
    Config.pvoutput.calc_debug_logging = True

    st = ServiceTopics(svc, True, logger, value_key=OutputField.GENERATION, calc=Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS, decimals=4)
    # Mock persistent state to avoid unwanted side effects
    with patch("pathlib.Path.is_file", return_value=False):
        t = Topic("t1", gain=2.0)
        st.register(t)

    t1_struct = time.struct_time((2025, 1, 1, 12, 0, 0, 0, 1, 0))
    t2_struct = time.struct_time((2025, 1, 1, 13, 0, 0, 0, 1, 0))

    with patch("time.localtime") as mock_local:
        mock_local.return_value = t1_struct
        await st.handle_update(None, MagicMock(), 10.0, "t1", MagicMock())
        st.aggregate(exclude_zero=False)

        mock_local.return_value = t2_struct
        await st.handle_update(None, MagicMock(), 20.0, "t1", MagicMock())

    val, at, count = st.aggregate(exclude_zero=False)
    # diff = 10. hours = 1. watts = 10. gain = 2. -> 20.0
    assert val == 20.0


def test_average_and_squared_root():
    """Hits AVERAGE and L_L_AVG paths."""
    svc = MagicMock()
    logger = logging.getLogger("test-coverage")

    # AVERAGE
    st1 = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.AVERAGE, decimals=2)
    st1.register(Topic("t_avg_1", state=10.0, timestamp=time.localtime()))
    st1.register(Topic("t_avg_2", state=20.0, timestamp=time.localtime()))
    p1 = {}
    st1.add_to_payload(p1, 5, time.localtime())
    assert p1["v2"] == 15.0

    # L_L_AVG
    st2 = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.L_L_AVG, decimals=4)
    st2.register(Topic("t_sq_1", state=3.0, timestamp=time.localtime()))
    st2.register(Topic("t_sq_2", state=4.0, timestamp=time.localtime()))
    p2 = {}
    st2.add_to_payload(p2, 5, time.localtime())
    # Formula in code is math.sqrt(sum(V^2 * gain)) / math.sqrt(3)
    # sqrt(3^2 + 4^2) / sqrt(3) = 5 / 1.732... = 2.88675...
    expected = 5.0 / math.sqrt(3)
    assert p2["v2"] == pytest.approx(expected, abs=1e-4)


@pytest.mark.asyncio
async def test_service_topics_misc(caplog):
    """Hits property, logging, and state saving/restoring paths."""
    svc = MagicMock()
    # Mock the async context manager for self._service.lock(timeout=1)
    svc.lock.return_value.__aenter__.return_value = MagicMock()

    st = ServiceTopics(svc, True, logging.getLogger("test-coverage"), value_key=OutputField.GENERATION, donation=True)

    assert st.requires_donation is True

    Config.pvoutput.started = time.time()
    Config.pvoutput.update_debug_logging = True
    assert st.check_is_updating(5, time.localtime()) is True

    Config.pvoutput.started = time.time() - 3600
    st.register(Topic("t_misc_1"))
    st.check_is_updating(5, time.localtime())
    assert "has never been updated" in caplog.text

    # Save/Restore state mocks
    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.stat") as mock_stat,
        patch(
            "pathlib.Path.open", mock_open(read_data='{"t_misc_1": {"topic": "t_misc_1", "gain": 1.0, "state": 10.0, "timestamp": [2025,1,1,12,0,0,0,1,0], "previous_state": 0.0, "previous_timestamp": null}}')
        ),
    ):
        mock_stat.return_value.st_mtime = time.time()  # Current day
        st.restore_state(st["t_misc_1"])
        assert st["t_misc_1"].state == 10.0

    # Inline save via handle_update
    st._always_persist = True
    with patch("pathlib.Path.open", mock_open()) as m:
        # Trigger handle_update which calls inline save if persist=True and state changed
        await st.handle_update(None, MagicMock(), 20.0, "t_misc_1", MagicMock())
        m.assert_called_with("w")

    with patch("pathlib.Path.open", side_effect=ValueError("Save Error")):
        # Trigger save via handle_update with another change
        # Code doesn't catch it, so it bubbles up.
        with pytest.raises(ValueError, match="Save Error"):
            await st.handle_update(None, MagicMock(), 30.0, "t_misc_1", MagicMock())


@pytest.mark.asyncio
async def test_time_period_service_topics_coverage():
    """Hits TimePeriodServiceTopics lines and parent time period update loop."""
    svc = MagicMock()
    logger = logging.getLogger("test-coverage")

    with patch.object(Config.pvoutput, "update_debug_logging", True), patch("sigenergy2mqtt.config.pvoutput_config.PVOutputConfiguration.current_time_period", new_callable=PropertyMock) as mock_cp:
        mock_cp.return_value = [OutputField.GENERATION]
        tp = TimePeriodServiceTopics(svc, True, logger, value_key=OutputField.GENERATION)
        st = ServiceTopics(svc, True, logger, value_key=OutputField.GENERATION, periods=[tp])

        # Register a topic to trigger restore_state
        with patch("pathlib.Path.is_file", return_value=False):
            st.register(Topic("t_tp_st"))

        # Trigger handle_update on parent, which hits time period children loop (334, 337)
        await st.handle_update(None, MagicMock(), 10.0, "t_tp_st", MagicMock())
        # TimePeriodServiceTopics.handle_update should have updated its internal state
        assert tp.aggregate(True, never_return_none=True)[0] == 10.0


@pytest.mark.asyncio
async def test_handle_update_peak_debug():
    """Hits the peak calculation debug logging path I fixed."""
    logger = logging.getLogger("test-coverage")
    svc = MagicMock()
    st = ServiceTopics(svc, True, logger, value_key=OutputField.PEAK_POWER, calc=Calculation.PEAK)

    with patch("pathlib.Path.is_file", return_value=False), patch.object(Config.pvoutput, "update_debug_logging", True):
        t = Topic("t_peak")
        st.register(t)

        # 1st update: sets peak
        await st.handle_update(None, MagicMock(), 100.0, "t_peak", MagicMock())

        # Manually backdate timestamp and NEWER restore_timestamp to hit line 317 in service_topics.py
        t.timestamp = time.localtime(time.time() - 7200)
        t.restore_timestamp = time.localtime(time.time() - 3600)

        # 2nd update: lower value, triggers debug if %60==0
        # mktime(localtime) - mktime(ts) should be multiple of 60
        now = time.localtime()
        with patch("time.localtime", return_value=now), patch("time.mktime", return_value=1234560.0):  # multiple of 60
            await st.handle_update(None, MagicMock(), 50.0, "t_peak", MagicMock())

    assert t.state == 100.0


# endregion


# region service.py coverage


@pytest.mark.asyncio
async def test_service_upload_exception(caplog):
    """Hits service.py upload_payload exception path."""
    svc = Service("Test", "id", "model", logging.getLogger("test-coverage"))
    with patch("sigenergy2mqtt.config.Config.pvoutput.testing", False), patch("requests.post", side_effect=Exception("Upload Crash")), patch("asyncio.sleep", return_value=None):
        res = await svc.upload_payload("http://url", {})
        assert res is False
        assert "Upload Crash" in caplog.text


@pytest.mark.asyncio
async def test_service_seconds_until_upload_full_path():
    """Hits service.py seconds_until_status_upload with request."""
    svc = Service("Test", "id", "model", logging.getLogger("test-coverage"))
    Service._interval = None
    Service._interval_updated = None

    with (
        patch("requests.get") as mock_get,
        patch("sigenergy2mqtt.config.Config.pvoutput.api_key", "k"),
        patch("sigenergy2mqtt.config.Config.pvoutput.system_id", "s"),
        patch("sigenergy2mqtt.config.Config.pvoutput.testing", False),
    ):
        resp = MagicMock()
        resp.__enter__.return_value.status_code = 200
        resp.__enter__.return_value.text = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,5;Don;1"
        resp.__enter__.return_value.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 3600)}
        mock_get.return_value = resp

        sec, next_t = await svc.seconds_until_status_upload()
        assert Service._interval == 5
        assert Service._donator is True


# endregion


# region services loop/verify coverage


@pytest.mark.asyncio
async def test_output_verify_exception(caplog):
    """Hits output.py verify exception path."""
    svc = PVOutputOutputService(logging.getLogger("test-coverage"), {})
    with patch("requests.get", side_effect=Exception("Verify Crash")):
        res = await svc._verify({"d": "2025"})
        assert res is False
        assert "Verify Crash" in caplog.text


def test_status_ignored_field(caplog):
    """Hits status.py line 67."""
    caplog.set_level(logging.DEBUG)
    PVOutputStatusService(logging.getLogger("test-coverage"), {"FAKE": []}, {})
    assert "IGNORED unrecognized FAKE" in caplog.text


# endregion


# region init coverage


def test_get_pvoutput_services_empty():
    from sigenergy2mqtt.pvoutput import get_pvoutput_services

    # Config is global, many tests might set it to True.
    with patch.object(Config.pvoutput, "enabled", False):
        res = get_pvoutput_services([])
        assert res == []


def make_mini_sensor(cls, topic="t", gain=1.0, unit=None, **kwargs):
    s = MagicMock(spec=cls)
    s.__class__ = cls
    s.publishable = True
    s.raw_state_topic = topic
    s.state_topic = topic + "_state"
    s.scan_interval = 300
    s.gain = gain
    s.unit = unit
    s.precision = 2
    s.device_class = "power"
    s.object_id = "myextendedsensor"
    for k, v in kwargs.items():
        setattr(s, k, v)
    s.__getitem__.side_effect = lambda k: getattr(s, k)
    return s


def test_get_pvoutput_services_comprehensive():
    """Hits many sensor match cases and get_gain branches in __init__.py."""
    from sigenergy2mqtt.main.thread_config import ThreadConfig
    from sigenergy2mqtt.pvoutput import get_pvoutput_services

    with (
        patch.object(Config.pvoutput, "enabled", True),
        patch.object(Config.pvoutput, "consumption", ConsumptionSource.NET_OF_BATTERY),
        patch.object(Config.pvoutput, "voltage", VoltageSource.PV),
        patch.object(Config.pvoutput, "temperature_topic", "temp/topic"),
        patch.object(Config.pvoutput, "extended", {StatusField.V7: "ExtendedMock", StatusField.V8: "StringSensor", StatusField.V9: "", StatusField.V10: "", StatusField.V11: "", StatusField.V12: ""}),
    ):
        sensors = [
            make_mini_sensor(DailyChargeEnergy),
            make_mini_sensor(DailyDischargeEnergy),
            make_mini_sensor(ESSTotalChargedEnergy),
            make_mini_sensor(ESSTotalDischargedEnergy),
            make_mini_sensor(GridSensorDailyExportEnergy),
            make_mini_sensor(GridSensorDailyImportEnergy),
            make_mini_sensor(PhaseVoltage, phase="A"),
            make_mini_sensor(PlantPVPower),
            make_mini_sensor(PlantRatedEnergyCapacity, gain=100, unit=UnitOfEnergy.KILO_WATT_HOUR),
            make_mini_sensor(PlantTotalImportedEnergy),
            make_mini_sensor(PVVoltageSensor),
            make_mini_sensor(TotalDailyPVEnergy),
            make_mini_sensor(TotalLifetimePVEnergy, gain=None),
            make_mini_sensor(TotalLoadConsumption),
            make_mini_sensor(TotalLoadDailyConsumption),
        ]

        # Ensure PlantBatterySoC matches
        pbs = MagicMock()
        pbs.__class__ = PlantBatterySoC
        pbs.publishable = True
        pbs.raw_state_topic = "raw_pbs"
        pbs.state_topic = "t_pbs"
        pbs.scan_interval = 300
        sensors.append(pbs)

        # Add a sensor that hits the extended field logic
        class ExtendedMock(TotalPVPower, TypedSensorMixin):
            pass

        ext_s = make_mini_sensor(ExtendedMock)
        ext_s.__class__ = ExtendedMock
        ext_s.data_type = ModbusDataType.INT32
        sensors.append(ext_s)

        # String sensor for warning
        class StringSensor(TotalPVPower, TypedSensorMixin):
            pass

        ext_string = make_mini_sensor(StringSensor)
        ext_string.__class__ = StringSensor
        ext_string.data_type = ModbusDataType.STRING
        sensors.append(ext_string)

        device = MagicMock()
        device.get_all_sensors.return_value = {str(i): s for i, s in enumerate(sensors)}

        config = MagicMock(spec=ThreadConfig)
        config.devices = [device]

        services = get_pvoutput_services([config])
        status_svc = services[0]
        # Verify topic was registered to V7
        assert len(status_svc._service_topics[StatusField.V7]) > 0
        # Verify Battery SoC topic registered
        assert len(status_svc._service_topics[StatusField.BATTERY_SOC]) > 0


def test_get_pvoutput_services_more_branches():
    """Hits remaining branches in __init__.py including line 91 (VoltageSource.L_L_AVG + PhaseVoltage) and 138-139 (fall back to plant_pv_power)."""
    from sigenergy2mqtt.main.thread_config import ThreadConfig
    from sigenergy2mqtt.pvoutput import get_pvoutput_services

    with (
        patch.object(Config.pvoutput, "enabled", True),
        patch.object(Config.pvoutput, "consumption", ConsumptionSource.IMPORTED),
        patch.object(Config.pvoutput, "voltage", VoltageSource.L_L_AVG),
        patch.object(Config.pvoutput, "extended", {StatusField.V7: "", StatusField.V8: "", StatusField.V9: "", StatusField.V10: "", StatusField.V11: "", StatusField.V12: ""}),
    ):
        sensors = [
            make_mini_sensor(GridSensorDailyImportEnergy),
            make_mini_sensor(PlantTotalImportedEnergy),
            make_mini_sensor(TotalLoadConsumption),
            make_mini_sensor(PlantPVPower),  # Hits 138-139 since TotalPVPower is missing
            make_mini_sensor(PhaseVoltage, phase="A"),  # Hits line 91 with L_L_AVG
        ]

        device = MagicMock()
        device.get_all_sensors.return_value = {str(i): s for i, s in enumerate(sensors)}
        config = MagicMock(spec=ThreadConfig)
        config.devices = [device]

        get_pvoutput_services([config])


# endregion
