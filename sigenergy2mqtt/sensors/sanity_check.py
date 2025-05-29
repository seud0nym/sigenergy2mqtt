from dataclasses import dataclass


@dataclass
class SanityCheck:
    """
    A class to represent a sanity check for sensor data.

    Attributes:
        min_value (float | int): The minimum acceptable value for the sensor.
        max_value (float | int): The maximum acceptable value for the sensor.

    Raises:
        ValueError if the sensor value is outside the defined range.
    """

    min_value: float | int = None
    max_value: float | int = None

    def check(self, state: float | int, previous_states: list[tuple[float, float | int]]) -> bool:
        """Check if the sensor value is within the acceptable range."""
        if not isinstance(state, (float, int)) or (self.min_value is None and self.max_value is None):
            return True
        elif self.min_value is None and self.max_value is not None:
            if state > self.max_value:
                raise ValueError(f"Value {state} exceeds sanity check maximum {self.max_value}")
        elif self.max_value is None and self.min_value is not None:
            if state < self.min_value:
                raise ValueError(f"Value {state} is below sanity check minimum {self.min_value}")
        elif not (self.min_value <= state <= self.max_value):
            raise ValueError(f"Value {state} is not within sanity check range {self.min_value} - {self.max_value}")
        return True
