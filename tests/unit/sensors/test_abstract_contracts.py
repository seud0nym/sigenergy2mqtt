"""Regression tests for intentional abstract and concrete framework types."""

import inspect
from typing import Protocol

from sigenergy2mqtt.devices.base.device import Device, ModbusDevice
from sigenergy2mqtt.devices.base.ha_publisher import HaPublisherMixin
from sigenergy2mqtt.sensors.base import (
    AlarmSensor,
    DerivedSensor,
    ObservableMixin,
    Sensor,
    WriteableSensorMixin,
)
from sigenergy2mqtt.sensors.plant.ess_preheating_read_write import ESSPreHeatingTOUTime
from sigenergy2mqtt.sensors.plant.read_write import RemoteEMSLimit


def test_framework_contracts_have_intentional_abstract_status() -> None:
    """Only bases with required subclass behavior should be abstract."""
    assert inspect.isabstract(HaPublisherMixin)
    assert inspect.isabstract(Sensor)
    assert inspect.isabstract(DerivedSensor)
    assert inspect.isabstract(WriteableSensorMixin)
    assert inspect.isabstract(ObservableMixin)
    assert inspect.isabstract(AlarmSensor)

    assert not inspect.isabstract(Device)
    assert not inspect.isabstract(ModbusDevice)
    assert not inspect.isabstract(RemoteEMSLimit)
    assert not inspect.isabstract(ESSPreHeatingTOUTime)


def test_sensor_does_not_inherit_from_protocol() -> None:
    """Sensor is an implementation hierarchy, not a structural interface."""
    assert Protocol not in Sensor.__mro__
