import asyncio
import logging
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from sigenergy2mqtt.config import StatusField, active_config
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.pvoutput.topic import Topic


def make_status_service(topics=None, extended=None):
    logger = logging.getLogger("test-pvoutput-status")
    topics = {} if topics is None else topics
    extended = {} if extended is None else extended
    return PVOutputStatusService(logger, topics, extended)


class TestPVOutputStatus:
    """Tests for PVOutputStatusService."""

    def test_create_payload_includes_generation_power(self):
        # create a generation power topic
        now = time.mktime((2024, 6, 1, 12, 0, 0, 0, 0, -1))
        # ensure deterministic started time
        active_config.pvoutput.started = now - 3600
        t = Topic("g/topic", gain=1.0, state=10.5, timestamp=time.localtime(now))
        # simulate a previous energy value an hour earlier so DIFFERENCE calculation can produce a value
        t.previous_state = 8.5
        t.previous_timestamp = time.localtime(now - 3600)
        svc = make_status_service(topics={StatusField.GENERATION_POWER: [t]}, extended={})
        payload, snapshot = svc._create_payload(time.localtime(now))
        # 'v2' is the value for GENERATION_POWER; difference (10.5-8.5)=2.0 converted to watts over 1h -> 2.0
        assert StatusField.GENERATION_POWER.value in payload
        assert pytest.approx(payload[StatusField.GENERATION_POWER.value], rel=1e-3) == 2.0
        # snapshot should contain previous state entries for enabled topics
        assert isinstance(snapshot, dict)

    @pytest.mark.asyncio
    async def test_create_payload_basic(self):
        """Test payload creation with some sample topics."""
        svc = make_status_service()
        now = time.strptime("2024-06-01 12:00:00", "%Y-%m-%d %H:%M:%S")

        # Enable some topics
        st_gen = ServiceTopics(svc, True, svc.logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.SUM)
        svc._service_topics[StatusField.GENERATION_POWER] = st_gen
        t = Topic("gen", gain=1.0)
        st_gen.register(t)

        # Properly update state via handle_update to ensure it's included in aggregation
        await st_gen.handle_update(None, MagicMock(), 500.0, "gen", MagicMock())

        payload, snapshot = svc._create_payload(now)

        assert payload["d"] == time.strftime("%Y%m%d", now)
        assert payload["t"] == time.strftime("%H:%M", now)
        assert StatusField.GENERATION_POWER.value in payload
        assert payload[StatusField.GENERATION_POWER.value] == 500.0

    def test_create_payload_requires_donation_skips_when_not_donator(self):
        """Test that donation-required topics are skipped for non-donators."""
        svc = make_status_service()
        now = time.strptime("2024-06-01 12:00:00", "%Y-%m-%d %H:%M:%S")

        # v7 requires donation
        st_v7 = ServiceTopics(svc, True, svc.logger, value_key=StatusField.V7, donation=True)
        svc._service_topics[StatusField.V7] = st_v7
        st_v7.register(Topic("v7", gain=1.0, state=100.0))

        with patch("sigenergy2mqtt.pvoutput.service.Service._donator", False):
            payload, _ = svc._create_payload(now)
            assert StatusField.V7.value not in payload

    def test_create_payload_includes_donation_when_donator_true(self):
        # mark extended V7 present so it's enabled and donation-flagged
        active_config.pvoutput.extended[StatusField.V7] = "energy"
        # force service donator state
        with patch("sigenergy2mqtt.pvoutput.service.Service._donator", True):
            now = time.mktime((2024, 6, 1, 12, 0, 0, 0, 0, -1))
            # ensure started flag so updating checks pass
            active_config.pvoutput.started = now - 3600
            t = Topic("v7/topic", gain=1.0, state=2.0, timestamp=time.localtime(now))
            # pass empty extended to avoid forcing SUM/DIFFERENCE calculation in constructor
            svc = make_status_service(topics={StatusField.V7: [t]}, extended={})
            payload, snapshot = svc._create_payload(time.localtime(now))
            assert StatusField.V7.value in payload

    @pytest.mark.asyncio
    async def test_seconds_until_status_upload_testing_mode(self):
        # ensure testing mode returns seconds == 60
        active_config.pvoutput.testing = True
        svc = make_status_service()
        seconds, next_time = await svc.seconds_until_status_upload(1, 2)
        # in testing mode seconds should be 60 (per Service.seconds_until_status_upload)
        assert seconds == 60 or seconds == 60.0

    @pytest.mark.asyncio
    async def test_schedule_loop_upload(self):
        """Test that schedule loop calls upload_payload."""
        svc = make_status_service()
        svc.online = asyncio.Future()

        # Mock payload with mandatory fields (v2)
        payload = {StatusField.GENERATION_POWER.value: 500}

        with (
            patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time()), (10, time.time() + 10)]),
            patch.object(svc, "_create_payload", return_value=(payload, {})),
            patch.object(svc, "upload_payload", return_value=True) as mock_upload,
        ):

            async def sleep_se(s):
                svc.online = False
                return None

            with patch("asyncio.sleep", side_effect=sleep_se):
                tasks = svc.schedule(None, None)
                await tasks[0]

            mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_skips_upload_if_no_main_fields(self, caplog):
        """Test that upload is skipped if no v1-v4 fields are present."""
        svc = make_status_service()
        svc.online = asyncio.Future()

        # Mock payload with NO v1, v2, v3, v4
        payload = {StatusField.TEMPERATURE.value: 25}

        with (
            patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]),
            patch.object(svc, "_create_payload", return_value=(payload, {})),
            patch.object(svc, "upload_payload") as mock_upload,
        ):

            async def sleep_se(s):
                svc.online = False
                return None

            with patch("asyncio.sleep", side_effect=sleep_se):
                tasks = svc.schedule(None, None)
                await tasks[0]

            mock_upload.assert_not_called()
            assert "skipping..." in caplog.text

    @pytest.mark.asyncio
    async def test_schedule_c1_logic(self):
        """Test c1 flag logic in schedule loop."""
        svc = make_status_service()

        async def run_c1_test(p_input):
            svc.online = asyncio.Future()
            mock_upload = MagicMock(return_value=True)
            with (
                patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]),
                patch.object(svc, "_create_payload", return_value=(p_input.copy(), {})),
                patch.object(svc, "upload_payload", mock_upload),
                patch("asyncio.sleep", side_effect=lambda s: setattr(svc, "online", False)),
            ):
                tasks = svc.schedule(None, None)
                await tasks[0]
                return mock_upload.call_args[0][1].get("c1")

        # Case 1: Gen + Con -> c1=1
        p1 = {StatusField.GENERATION_ENERGY.value: 100, StatusField.CONSUMPTION_ENERGY.value: 50}
        assert await run_c1_test(p1) == 1

        # Case 2: Gen only -> c1=2
        p2 = {StatusField.GENERATION_ENERGY.value: 100}
        assert await run_c1_test(p2) == 2

        # Case 3: Con only -> c1=3
        p3 = {StatusField.CONSUMPTION_ENERGY.value: 100}
        assert await run_c1_test(p3) == 3

    @pytest.mark.asyncio
    async def test_schedule_adjusts_negative_consumption(self, caplog):
        """Test that negative consumption power is adjusted to 0."""
        svc = make_status_service()
        svc.online = asyncio.Future()

        payload = {StatusField.GENERATION_POWER.value: 500, StatusField.CONSUMPTION_POWER.value: -100}

        # Mock consumption_enabled to True using PropertyMock on the configuration object
        with patch.object(type(active_config.pvoutput), "consumption_enabled", new_callable=PropertyMock) as mock_ce:
            mock_ce.return_value = True

            with (
                patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]),
                patch.object(svc, "_create_payload", return_value=(payload, {})),
                patch.object(svc, "upload_payload", return_value=True) as mock_upload,
                patch("asyncio.sleep", side_effect=lambda s: setattr(svc, "online", False)),
            ):
                tasks = svc.schedule(None, None)
                await tasks[0]

                sent_payload = mock_upload.call_args[0][1]
                assert sent_payload[StatusField.CONSUMPTION_POWER.value] == 0
                assert "Adjusted" in caplog.text

    @pytest.mark.asyncio
    async def test_schedule_failed_upload_restores_state(self):
        """Test that topic state is restored if upload fails."""
        svc = make_status_service()
        svc.online = asyncio.Future()

        topic = Topic("test", gain=1.0)
        topic.previous_state = 100.0
        topic.previous_timestamp = None

        st_dict = ServiceTopics(svc, True, None, value_key=StatusField.GENERATION_POWER)
        svc._service_topics[StatusField.GENERATION_POWER] = st_dict
        st_dict["test"] = topic

        snapshot = {StatusField.GENERATION_POWER: {"test": (100.0, None)}}
        payload = {StatusField.GENERATION_POWER.value: 500}

        with (
            patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]),
            patch.object(svc, "_create_payload", return_value=(payload, snapshot)),
            patch.object(svc, "upload_payload", return_value=False),
            patch("asyncio.sleep", side_effect=lambda s: setattr(svc, "online", False)),
        ):
            # Simulate state update before "failed" upload restores it
            topic.previous_state = 200.0

            tasks = svc.schedule(None, None)
            await tasks[0]

            assert topic.previous_state == 100.0

    def test_subscribe_registers_topics(self):
        """Test topic subscription registers topics with mqtt client."""
        svc = make_status_service()
        mock_client = MagicMock()
        mock_handler = MagicMock()

        mock_st = MagicMock(spec=ServiceTopics)
        svc._service_topics[StatusField.GENERATION_POWER] = mock_st

        svc.subscribe(mock_client, mock_handler)

        mock_st.subscribe.assert_called_with(mock_client, mock_handler)

    def test_status_ignored_field(self, caplog):
        """Hits status.py unrecognized field logic."""
        caplog.set_level(logging.DEBUG)
        PVOutputStatusService(logging.getLogger("test-status"), {"FAKE": []}, {})
        assert "IGNORED unrecognized FAKE" in caplog.text

    @pytest.mark.asyncio
    async def test_refresh_home_assistant_extended_fields_uses_supervisor_api(self):
        svc = make_status_service()
        svc._ha_extended_entities = {StatusField.V7: "sensor.grid_power"}
        svc._service_topics[StatusField.V7].enabled = True
        svc._service_topics[StatusField.V7].register(Topic("__ha_sensor__:sensor.grid_power", gain=1.0))

        class Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"state": "123.4"}

        with patch.dict("os.environ", {"SUPERVISOR_TOKEN": "token"}, clear=False), patch("requests.get", return_value=Resp()):
            await svc._refresh_home_assistant_extended_fields()

        assert svc._service_topics[StatusField.V7]["__ha_sensor__:sensor.grid_power"].state == 123.4

    @pytest.mark.asyncio
    async def test_refresh_home_assistant_temperature_uses_supervisor_api(self):
        svc = make_status_service()
        svc._ha_extended_entities = {StatusField.TEMPERATURE: "sensor.outdoor_temp"}
        svc._service_topics[StatusField.TEMPERATURE].enabled = True
        svc._service_topics[StatusField.TEMPERATURE].register(Topic("__ha_sensor__:sensor.outdoor_temp", gain=1.0))

        class Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"state": "21.5"}

        with patch.dict("os.environ", {"SUPERVISOR_TOKEN": "token"}, clear=False), patch("requests.get", return_value=Resp()):
            await svc._refresh_home_assistant_extended_fields()

        assert svc._service_topics[StatusField.TEMPERATURE]["__ha_sensor__:sensor.outdoor_temp"].state == 21.5

    def test_extended_data_energy_sets_sum_difference_calculation(self):
        """Line 90: extended_data[field] == 'energy' forces SUM|DIFFERENCE calculation."""
        from sigenergy2mqtt.pvoutput.service_topics import Calculation

        t = Topic("v7/topic", gain=1.0)
        svc = make_status_service(
            topics={StatusField.V7: [t]},
            extended={StatusField.V7: "energy"},
        )
        calc = svc._service_topics[StatusField.V7].calculation
        assert Calculation.SUM in calc
        assert Calculation.DIFFERENCE in calc

    @pytest.mark.asyncio
    async def test_refresh_ha_no_supervisor_token_emits_warning_once(self, caplog):
        """Lines 105-108: missing SUPERVISOR_TOKEN emits warning only once."""
        import logging

        caplog.set_level(logging.WARNING)
        svc = make_status_service()
        svc._ha_extended_entities = {StatusField.V7: "sensor.something"}

        with patch.dict("os.environ", {}, clear=True):
            # Remove SUPERVISOR_TOKEN if present
            import os

            os.environ.pop("SUPERVISOR_TOKEN", None)

            # First call should emit warning
            await svc._refresh_home_assistant_extended_fields()
            assert "SUPERVISOR_TOKEN is not available" in caplog.text
            assert svc._ha_supervisor_warning_emitted is True

            # Second call should NOT emit another warning (idempotent)
            caplog.clear()
            await svc._refresh_home_assistant_extended_fields()
            assert "SUPERVISOR_TOKEN is not available" not in caplog.text

    @pytest.mark.asyncio
    async def test_refresh_ha_non_200_response_logs_warning(self, caplog):
        """Lines 118-119: non-200 HA API response logs a warning and continues."""
        import logging

        caplog.set_level(logging.WARNING)
        svc = make_status_service()
        svc._ha_extended_entities = {StatusField.V7: "sensor.grid_power"}

        class BadResp:
            status_code = 500

        with patch.dict("os.environ", {"SUPERVISOR_TOKEN": "tok"}, clear=False), patch("requests.get", return_value=BadResp()):
            await svc._refresh_home_assistant_extended_fields()

        assert "Failed to read Home Assistant sensor" in caplog.text
        assert "status_code=500" in caplog.text

    @pytest.mark.asyncio
    async def test_refresh_ha_unavailable_state_is_ignored(self, caplog):
        """Lines 122-123: 'unavailable' or 'unknown' state is ignored with debug log."""
        import logging

        caplog.set_level(logging.DEBUG)
        svc = make_status_service()
        svc._ha_extended_entities = {StatusField.V7: "sensor.grid_power"}

        for bad_state in ("unavailable", "unknown", None):

            class Resp:
                status_code = 200

                @staticmethod
                def json():
                    return {"state": bad_state}

            caplog.clear()
            with patch.dict("os.environ", {"SUPERVISOR_TOKEN": "tok"}, clear=False), patch("requests.get", return_value=Resp()):
                await svc._refresh_home_assistant_extended_fields()

            assert "Ignoring Home Assistant sensor" in caplog.text

    @pytest.mark.asyncio
    async def test_refresh_ha_non_numeric_state_logs_warning(self, caplog):
        """Lines 127-128: non-numeric state raises ValueError → logged as warning."""
        import logging

        caplog.set_level(logging.WARNING)
        svc = make_status_service()
        svc._ha_extended_entities = {StatusField.V7: "sensor.grid_power"}
        svc._service_topics[StatusField.V7].enabled = True
        svc._service_topics[StatusField.V7].register(Topic("__ha_sensor__:sensor.grid_power", gain=1.0))

        class Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"state": "not-a-number"}

        with patch.dict("os.environ", {"SUPERVISOR_TOKEN": "tok"}, clear=False), patch("requests.get", return_value=Resp()):
            await svc._refresh_home_assistant_extended_fields()

        assert "non-numeric state" in caplog.text

    @pytest.mark.asyncio
    async def test_refresh_ha_generic_exception_logs_warning(self, caplog):
        """Lines 129-130: generic exception from requests.get is caught and logged."""
        import logging

        caplog.set_level(logging.WARNING)
        svc = make_status_service()
        svc._ha_extended_entities = {StatusField.V7: "sensor.grid_power"}

        with patch.dict("os.environ", {"SUPERVISOR_TOKEN": "tok"}, clear=False), patch(
            "requests.get", side_effect=ConnectionError("network error")
        ):
            await svc._refresh_home_assistant_extended_fields()

        assert "Failed reading Home Assistant sensor" in caplog.text

    @pytest.mark.asyncio
    async def test_schedule_lock_timeout_logs_warning(self, caplog):
        """Line 218: asyncio.TimeoutError while acquiring lock is caught and logged."""
        import logging
        from contextlib import asynccontextmanager

        caplog.set_level(logging.WARNING)
        svc = make_status_service()
        svc.online = asyncio.Future()

        call_count = 0

        async def fake_seconds_until(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 0, 0
            # Second call: set online=False so the loop exits
            svc.online = False
            return 60, 0

        @asynccontextmanager
        async def raising_lock(*args, **kwargs):
            svc.online = False
            raise asyncio.TimeoutError
            yield  # noqa: unreachable - needed to make this an async generator

        with (
            patch.object(svc, "seconds_until_status_upload", side_effect=fake_seconds_until),
            patch.object(svc, "_refresh_home_assistant_extended_fields", return_value=None),
            patch.object(svc, "lock", raising_lock),
        ):
            tasks = svc.schedule(None, None)
            await tasks[0]

        assert "Failed to acquire lock within timeout" in caplog.text
