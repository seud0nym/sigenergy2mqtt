import json

from sigenergy2mqtt.pvoutput.topic import Topic
from sigenergy2mqtt.pvoutput import get_gain
from sigenergy2mqtt.sensors.const import UnitOfEnergy, UnitOfPower


def test_topic_json_encoder_decoder_roundtrip():
    t = Topic("sensor/topic", scan_interval=30, gain=2.5, precision=2, state=3.14)
    encoded = Topic.json_encoder(t)
    assert isinstance(encoded, dict)
    # simulate json dump/load roundtrip
    s = json.dumps(encoded)
    loaded = json.loads(s, object_hook=Topic.json_decoder)
    assert isinstance(loaded, Topic)
    assert loaded.topic == t.topic
    assert loaded.gain == t.gain


def test_topic_json_decoder_leaves_non_topic():
    obj = {"foo": "bar"}
    assert Topic.json_decoder(obj) == obj


class FakeSensor:
    def __init__(self, gain, unit=None):
        self.gain = gain
        self.unit = unit


def test_get_gain_defaults_and_special_cases():
    s = FakeSensor(None)
    assert get_gain(s) == 1.0

    s = FakeSensor(100, unit=UnitOfEnergy.KILO_WATT_HOUR)
    assert get_gain(s) == 10.0

    s = FakeSensor(100, unit=UnitOfPower.KILO_WATT)
    assert get_gain(s) == 10.0

    s = FakeSensor(2.5)
    assert get_gain(s) == 2.5

    s = FakeSensor(2.5)
    assert get_gain(s, negate=True) == -2.5
