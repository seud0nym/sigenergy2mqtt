from enum import StrEnum

# Source: https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/const.py#L527


class StateClass(StrEnum):
    """State class for sensors."""

    MEASUREMENT = "measurement"
    """The state represents a measurement in present time."""

    MEASUREMENT_ANGLE = "measurement_angle"
    """The state represents a angle measurement in present time. Currently only degrees are supported."""

    TOTAL = "total"
    """The state represents a total amount.

    For example: net energy consumption"""

    TOTAL_INCREASING = "total_increasing"
    """The state represents a monotonically increasing total.

    For example: an amount of consumed gas"""
