import asyncio
import pytest
from unittest.mock import MagicMock, patch

from sigenergy2mqtt.influxdb.service import InfluxService
from sigenergy2mqtt.config import Config


class DummyMqtt:
    def publish(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_influx_handle_mqtt_includes_excludes(tmp_path, mocker):
    logger = MagicMock()
    svc = InfluxService(logger)

    # Create a fake sensor
    class FakeSensor(dict):
        def __init__(self):
            super().__init__()
            self['object_id'] = 'sensor.test_1'
            self['unique_id'] = 'uid_test_1'
            self['state_topic'] = 'sigenergy2mqtt/sensor.test_1/state'
            self['raw_state_topic'] = 'sigenergy2mqtt/sensor.test_1/raw'

    fake_sensor = FakeSensor()

    # Patch DeviceRegistry to return a device containing the fake sensor
    fake_device = MagicMock()
    fake_device.get_all_sensors.return_value = {'uid_test_1': fake_sensor}

    with patch('sigenergy2mqtt.devices.device.DeviceRegistry.get', return_value=(fake_device,)):
        # No include/exclude -> should write (we patch _write_line to capture)
        wrote = {}

        def fake_write(line):
            wrote['line'] = line

        svc._write_line = fake_write
        await svc.handle_mqtt(None, None, '123.45', 'sigenergy2mqtt/sensor.test_1/state', None)
        assert 'value' in wrote['line'] or '123.45' in wrote['line']

        # Exclude the sensor -> should skip
        Config.influxdb.exclude = ['test_1']
        wrote.clear()
        await svc.handle_mqtt(None, None, '123.45', 'sigenergy2mqtt/sensor.test_1/state', None)
        assert wrote == {}

        # Include list that doesn't match -> skip
        Config.influxdb.exclude = []
        Config.influxdb.include = ['other']
        wrote.clear()
        await svc.handle_mqtt(None, None, '123.45', 'sigenergy2mqtt/sensor.test_1/state', None)
        assert wrote == {}

        # Matching include -> write
        Config.influxdb.include = ['test_1']
        wrote.clear()
        await svc.handle_mqtt(None, None, '123.45', 'sigenergy2mqtt/sensor.test_1/state', None)
        assert 'line' in wrote
