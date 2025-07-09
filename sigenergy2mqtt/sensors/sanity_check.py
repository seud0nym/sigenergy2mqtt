from .const import StateClass, UnitOfEnergy, UnitOfPower
from dataclasses import dataclass
from sigenergy2mqtt.config import Config


@dataclass
class SanityCheck:
    """
    A class to represent a sanity check for sensor data.

    Attributes:
        min_value (float | int): The minimum acceptable value for the sensor. This value must be a RAW value read from BEFORE any gain is applied.
        max_value (float | int): The maximum acceptable value for the sensor. This value must be a RAW value read from BEFORE any gain is applied.
        delta (bool): If True, the check will only consider the change in value rather than the absolute value.

    Raises:
        ValueError if the sensor value is outside the defined range.
    """

    min_value: float | int = None
    max_value: float | int = None
    delta: bool = False

    def init(self, unit: str, state_class: StateClass, gain: float, scan_interval: int) -> None:
        """Initialize the sanity check based on the sensor properties."""
        if self.min_value is not None or self.max_value is not None:
            # Already initialized
            return
        if gain is None or gain <= 0:
            gain = 1
        if state_class == StateClass.TOTAL_INCREASING:
            self.delta = True
            self.min_value = 0
        match unit:
            case UnitOfEnergy.WATT_HOUR:
                self.max_value = Config.sanity_check_default_kw * 1000 * scan_interval
            case UnitOfEnergy.KILO_WATT_HOUR:
                self.max_value = Config.sanity_check_default_kw * gain * scan_interval
            case UnitOfPower.WATT:
                self.max_value = Config.sanity_check_default_kw * 1000 * scan_interval
                self.min_value = self.max_value * -1
            case UnitOfPower.KILO_WATT:
                self.max_value = Config.sanity_check_default_kw * gain * scan_interval
                self.min_value = self.max_value * -1

    def check(self, state: float | int, previous_states: list[tuple[float, float | int]]) -> bool:
        """Check if the sensor value is within the acceptable range."""
        if not isinstance(state, (float, int)) or (self.min_value is None and self.max_value is None) or (self.delta and len(previous_states) == 0):
            return True
        if self.delta:
            if len(previous_states) > 0:
                previous_value = previous_states[-1][1]
                value = state - previous_value
            else:
                return True
        else:
            value = state
        if self.min_value is None and self.max_value is not None:
            if value > self.max_value:
                raise ValueError(f"{'Delta' if self.delta else 'Value'} {value} exceeds sanity check maximum {self.max_value} ({state=} {previous_states=})")
        elif self.max_value is None and self.min_value is not None:
            if value < self.min_value:
                raise ValueError(f"{'Delta' if self.delta else 'Value'} {value} is below sanity check minimum {self.min_value} ({state=} {previous_states=})")
        elif not (self.min_value <= value <= self.max_value):
            raise ValueError(f"{'Delta' if self.delta else 'Value'} {value} is not within sanity check range {self.min_value} - {self.max_value} ({state=} {previous_states=})")
        return True
