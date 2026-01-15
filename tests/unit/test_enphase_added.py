import time
from typing import Any, cast

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.smartport.enphase import (
    EnphaseCurrent,
    EnphaseFrequency,
    EnphaseLifetimePVEnergy,
    EnphasePowerFactor,
    EnphasePVPower,
    EnphaseReactivePower,
    EnphaseVoltage,
)
from sigenergy2mqtt.sensors.base import Sensor


def make_values(val_dict):
    return [(time.time(), 0, val_dict)]


def test_enphase_lifetime_set_source_values_rejects_wrong_sensor():
    derived = EnphaseLifetimePVEnergy(0, "SN")

    class NotPV:
        pass

    assert derived.set_source_values(cast(Sensor, NotPV()), make_values({"actEnergyDlvd": 1})) is False


def test_enphase_lifetime_set_source_values_accepts_and_sets_state():
    derived = EnphaseLifetimePVEnergy(0, "SN")
    # create a PV-like object without full init
    pv = EnphasePVPower.__new__(EnphasePVPower)
    vals = make_values({"actEnergyDlvd": 123.45})
    assert derived.set_source_values(pv, vals) is True
    assert derived._states[-1][1] == 123.45


@pytest.mark.parametrize(
    "cls,key",
    [
        (EnphaseCurrent, "current"),
        (EnphaseFrequency, "freq"),
        (EnphasePowerFactor, "pwrFactor"),
        (EnphaseReactivePower, "reactivePower"),
        (EnphaseVoltage, "voltage"),
    ],
)
def test_enphase_derived_setters(cls, key):
    derived = cls(0, "SN")
    pv = EnphasePVPower.__new__(EnphasePVPower)
    vals = make_values({key: 42})
    assert derived.set_source_values(pv, vals) is True
    assert derived._states[-1][1] == 42


def test_enphase_pvpower_get_attributes_minimal_init(tmp_path, monkeypatch):
    # Ensure Config.modbus[0].scan_interval.realtime available for ReadableSensorMixin
    conf = cast(Any, Config)
    orig_devices = conf.modbus

    class SI:
        realtime = 1

    class D:
        scan_interval = SI()

    conf.modbus = [D()]

    pv = EnphasePVPower(0, "SN", "host", "user", "pass")
    attrs = pv.get_attributes()
    assert attrs["source"] == "Enphase Envoy API"

    conf.modbus = orig_devices
