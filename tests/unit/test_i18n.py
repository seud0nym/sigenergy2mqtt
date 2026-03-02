from unittest.mock import patch

import pytest

from sigenergy2mqtt import i18n
from sigenergy2mqtt.common import DeviceClass, InputType, Protocol, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import AlarmSensor, ReadOnlySensor, Sensor


@pytest.fixture(autouse=True)
def ensure_sane_config():
    """Ensure active_config is sane and isolated."""
    cfg = Config()
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.device_name_prefix = ""
    cfg.modbus = []

    with _swap_active_config(cfg):
        yield cfg


class MockSensor(Sensor):
    def __init__(self, name="Test Sensor"):
        super().__init__(
            name=name,
            unique_id="sigenergy_0_001_30000",
            object_id="sigenergy_test_sensor",
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:test",
            gain=1.0,
            precision=2,
            protocol_version=Protocol.V2_4,
        )

    async def _update_internal_state(self, **kwargs):
        return True


class MockReadOnlySensor(ReadOnlySensor):
    def __init__(self, name="Test RO Sensor"):
        super().__init__(
            name=name,
            object_id="sigenergy_test_ro_sensor",
            input_type=InputType.INPUT,
            plant_index=0,
            device_address=1,
            address=30000,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=60,
            unit="V",
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:test",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_4,
        )


class MockAlarmSensor(AlarmSensor):
    def __init__(self):
        super().__init__(name="Test Alarm", object_id="sigenergy_test_alarm", plant_index=0, device_address=1, address=30001, protocol_version=Protocol.V2_4, alarm_type="TEST")

    def decode_alarm_bit(self, bit_position):
        if bit_position == 0:
            return "Test Bit 0"
        return None


class MockDevice(Device):
    def __init__(self):
        super().__init__(name="Test Device", plant_index=0, unique_id="test_device_unique_id", manufacturer="Sigenergy", model="Test Model", protocol_version=Protocol.V2_4)


@pytest.fixture(autouse=True)
def clear_ids():
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()
    yield


def test_translator_basic():
    i18n.set_translations("en", {"class": {"AlarmSensor": {"no_alarm": "No Alarm"}}})
    assert i18n._t("NonExistent.key", "Default") == "Default"
    assert i18n._t("AlarmSensor.no_alarm") == "No Alarm"


def test_translator_fallback():
    i18n.set_translations("fr", {"class": {"Inverter": {"name": "Onduleur"}, "AlarmSensor": {"no_alarm": "Pas d'alarme"}}})
    i18n.set_translations("en", {"class": {"Alarm1Sensor": {"alarm": {"1": "1002: Low insulation resistance"}}}})
    i18n.load("fr")
    # Exists in fr mock
    assert i18n._t("Inverter.name") == "Onduleur"
    # Not in fr mock, should fallback to en mock
    assert i18n._t("Alarm1Sensor.alarm.1") == "1002: Low insulation resistance"


def test_sensor_name_translation():
    i18n.set_translations("fr", {"class": {"InverterModel": {"name": "Modèle"}}})
    i18n.load("fr")

    # We need a concrete class that matches the translation key
    class InverterModel(MockSensor):
        pass

    sensor = InverterModel("Model")
    assert sensor["name"] == "Modèle"


def test_device_name_translation():
    i18n.set_translations("fr", {"class": {"Inverter": {"name": "Onduleur"}}})
    i18n.load("fr")

    class Inverter(MockDevice):
        pass

    device = Inverter()
    assert device["name"] == "Onduleur"


@pytest.mark.asyncio
async def test_alarm_bit_translation():
    i18n.set_translations("fr", {"class": {"Alarm1Sensor": {"alarm": {"0": "1001: Incompatibilité de version logicielle"}}}})
    i18n.load("fr")

    # Alarm1Sensor.alarm.0 is translated in fr mock
    class Alarm1Sensor(MockAlarmSensor):
        pass

    with patch.object(ReadOnlySensor, "_update_internal_state", return_value=True):
        sensor = Alarm1Sensor()
        sensor._states = [(0.0, 1)]
        state = await sensor.get_state()
        assert state == "1001: Incompatibilité de version logicielle"


def test_options_translation():
    i18n.set_translations("fr", {"class": {"RunningStateSensor": {"options": {"0": "Veille"}}}})
    i18n.load("fr")

    class RunningStateSensor(MockSensor):
        def __init__(self):
            super().__init__()
            self["options"] = ["Standby"]

    sensor = RunningStateSensor()
    discovery = sensor.get_discovery_components()
    assert discovery[sensor.unique_id]["options"][0] == "Veille"


def test_attributes_translation():
    i18n.set_translations("fr", {"class": {"ReadOnlySensor": {"attributes": {"source": "Registre Modbus {address}"}}}})
    i18n.load("fr")
    sensor = MockReadOnlySensor()
    attrs = sensor.get_attributes()
    assert attrs["source"] == "Registre Modbus 30000"


def test_get_available_translations():
    translations = i18n.get_available_translations()
    assert "en" in translations
    # Since we only have en.yaml in the repo, it should be at least ['en']
    assert len(translations) >= 1


@pytest.mark.no_language_mock
def test_get_default_language_fallback():
    # Test fallback to 'en' when system language is not available
    with patch("locale.getlocale", return_value=(None, None)):
        with patch("os.environ.get", return_value="xx_XX.UTF-8"):
            # xx.yaml does NOT exist, so should fall back to 'en'
            assert i18n.get_default_language() == "en"


@pytest.mark.no_language_mock
def test_get_default_language_system():
    # Test picking up system language if it exists
    # We'll mock the exists check for a fake language
    with patch("locale.getlocale", return_value=("fr_FR", "UTF-8")):
        with patch("sigenergy2mqtt.i18n.Path.exists", return_value=True):
            assert i18n.get_default_language() == "fr"


@pytest.mark.no_language_mock
def test_get_default_language_env():
    # Test picking up system language via LANG env var if getlocale() fails
    with patch("locale.getlocale", return_value=(None, None)):
        with patch("os.environ.get", return_value="de_DE.UTF-8"):
            with patch("sigenergy2mqtt.i18n.Path.exists", return_value=True):
                assert i18n.get_default_language() == "de"
