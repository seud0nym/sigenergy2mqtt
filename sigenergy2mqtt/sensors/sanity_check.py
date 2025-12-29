from .const import StateClass, UnitOfEnergy, UnitOfPower
from dataclasses import dataclass
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.modbus.client import ModbusClient


@dataclass
class SanityCheck:
    """
    A class to represent a sanity check for sensor data.

    Attributes:
        min_raw (float | int): The minimum acceptable value for the sensor. This value must be a RAW value read from BEFORE any gain is applied.
        max_raw (float | int): The maximum acceptable value for the sensor. This value must be a RAW value read from BEFORE any gain is applied.
        delta (bool): If True, the check will only consider the change in value rather than the absolute value.

    Raises:
        ValueError if the sensor value is outside the defined range.
    """

    min_raw: float | int = None
    max_raw: float | int = None
    delta: bool = False

    def init(self, unit: str, state_class: StateClass, gain: float, scan_interval: int, data_type: ModbusClient.DATATYPE) -> None:
        """Initialize the sanity check based on the sensor properties."""
        if self.min_raw is not None or self.max_raw is not None:
            # Already initialized
            return
        match data_type:
            case ModbusClient.DATATYPE.INT16:
                self.min_raw = -32768
                self.max_raw = 32767
            case ModbusClient.DATATYPE.UINT16:
                self.min_raw = 0
                self.max_raw = 65535
            case ModbusClient.DATATYPE.INT32:
                self.min_raw = -2147483648
                self.max_raw = 2147483647
            case ModbusClient.DATATYPE.UINT32:
                self.min_raw = 0
                self.max_raw = 4294967295
            case ModbusClient.DATATYPE.INT64:
                self.min_raw = -9223372036854775808
                self.max_raw = 9223372036854775807
            case ModbusClient.DATATYPE.UINT64:
                self.min_raw = 0
                self.max_raw = 18446744073709551615
        match unit:
            case UnitOfPower.WATT | UnitOfEnergy.WATT_HOUR | UnitOfPower.KILO_WATT | UnitOfEnergy.KILO_WATT_HOUR:
                self.max_raw = min(Config.sanity_check_default_kw * 1000, self.max_raw)
        if state_class == StateClass.TOTAL_INCREASING:
            self.delta = True
            self.min_raw = 0
        elif self.min_raw is not None and self.max_raw is not None:
            self.min_raw = max(self.max_raw * -1, self.min_raw)

    def check(self, state: float | int, previous_states: list[tuple[float, float | int]]) -> bool:
        """Check if the sensor value is within the acceptable range."""
        if not isinstance(state, (float, int)) or (self.min_raw is None and self.max_raw is None) or (self.delta and len(previous_states) == 0):
            return True
        if self.delta:
            if len(previous_states) > 0:
                previous_value = previous_states[-1][1]
                value = state - previous_value
            else:
                return True
        else:
            value = state
        if self.min_raw is None and self.max_raw is not None:
            if value > self.max_raw:
                raise ValueError(f"Raw {'delta' if self.delta else 'value'} {value} exceeds sanity check maximum {self.max_raw} ({state=} {previous_states=})")
        elif self.max_raw is None and self.min_raw is not None:
            if value < self.min_raw:
                raise ValueError(f"Raw {'delta' if self.delta else 'value'} {value} is below sanity check minimum {self.min_raw} ({state=} {previous_states=})")
        elif not (self.min_raw <= value <= self.max_raw):
            raise ValueError(f"Raw {'delta' if self.delta else 'value'} {value} is not within sanity check range {self.min_raw} to {self.max_raw} ({state=} {previous_states=})")
        return True
