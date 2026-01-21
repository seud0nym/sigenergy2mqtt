from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.modbus.types import ModbusDataType

from . import const


class SanityCheckException(ValueError):
    pass


@dataclass
class SanityCheck:
    """
    A class to represent a sanity check for sensor data.

    Attributes:
        min_raw (float | int): The minimum acceptable value for the sensor. This value must be a RAW value read from BEFORE any gain is applied.
        max_raw (float | int): The maximum acceptable value for the sensor. This value must be a RAW value read from BEFORE any gain is applied.
        delta (bool): If True, the check will only consider the change in value rather than the absolute value.

    Raises:
        SanityCheckException if the sensor value is outside the defined range.
    """

    min_raw: float | int | None = None
    max_raw: float | int | None = None
    delta: bool = False
    gain: float | None = None
    precision: int | None = None

    def __init__(
        self,
        unit: str | None = None,
        device_class: const.DeviceClass | None = None,
        state_class: const.StateClass | None = None,
        data_type: ModbusDataType | None = None,
        gain: float | None = None,
        min_raw: float | int | None = None,
        max_raw: float | int | None = None,
        delta: bool | None = None,
        precision: int | None = None,
    ) -> None:
        self.min_raw = min_raw
        self.max_raw = max_raw
        self.gain = gain
        self.precision = precision
        if delta is None:
            if state_class == const.StateClass.TOTAL_INCREASING:
                self.delta = True
                self.min_raw = 0
            elif device_class == const.DeviceClass.ENERGY:
                self.delta = True
            else:
                self.delta = False
        else:
            self.delta = delta

        if self.min_raw is not None or self.max_raw is not None:
            # Already initialized via parameters
            return

        match data_type:
            case ModbusDataType.INT16:
                self.min_raw = -32768
                self.max_raw = 32767
            case ModbusDataType.UINT16:
                self.min_raw = 0
                self.max_raw = 65535
            case ModbusDataType.INT32:
                self.min_raw = -2147483648
                self.max_raw = 2147483647
            case ModbusDataType.UINT32:
                self.min_raw = 0
                self.max_raw = 4294967295
            case ModbusDataType.INT64:
                self.min_raw = -9223372036854775808
                self.max_raw = 9223372036854775807
            case ModbusDataType.UINT64:
                self.min_raw = 0
                self.max_raw = 18446744073709551615
        match unit:
            case const.UnitOfPower.WATT | const.UnitOfEnergy.WATT_HOUR | const.UnitOfPower.KILO_WATT | const.UnitOfEnergy.KILO_WATT_HOUR:
                self.max_raw = Config.sanity_check_default_kw * 1000 if not self.max_raw else min(Config.sanity_check_default_kw * 1000, self.max_raw)
            case const.PERCENTAGE:
                self.max_raw = 100 * (gain if gain else 1)
        if self.min_raw is not None and self.max_raw is not None:
            self.min_raw = max(self.max_raw * -1, self.min_raw)

    def __repr__(self):
        if self.min_raw is None and self.max_raw is None:
            return "Sanity checking disabled"
        min_value = self._raw2value(self.min_raw)
        max_value = self._raw2value(self.max_raw)
        min_raw_str = f" (raw={self.min_raw})" if self.min_raw != min_value else ""
        max_raw_str = f" (raw={self.max_raw})" if self.max_raw != max_value else ""
        range_str = (f" (raw={self.min_raw}-{self.max_raw})" if float(self.min_raw) != min_value or float(self.max_raw) != max_value else "") if self.min_raw is not None and self.max_raw is not None else ""
        if self.delta:
            if self.min_raw is None:
                return f"The delta of the value compared to the previous value is sanity checked to be a maximum of {max_value}{max_raw_str}"
            if self.max_raw is None:
                return f"The delta of the value compared to the previous value is sanity checked to be a minimum of {min_value}{min_raw_str}"
            return f"The delta of the value compared to the previous value is sanity checked to be between {min_value} and {max_value}{range_str}"
        if self.min_raw is None:
            return f"The value is sanity checked to be a maximum of {max_value}{max_raw_str}"
        if self.max_raw is None:
            return f"The value is sanity checked to be a minimum of {min_value}{min_raw_str}"
        return f"The value is sanity checked to be between {min_value} and {max_value}{range_str}"

    def _raw2value(self, raw: float | int | None) -> float | int | None:
        if raw is None:
            return raw
        if self.gain is not None:
            raw /= self.gain
        if isinstance(raw, float) and self.precision is not None:
            raw = round(raw, self.precision)
            if self.precision == 0:
                raw = int(cast(float, raw))
        return raw

    @property
    def is_enabled(self) -> bool:
        return self.min_raw is not None or self.max_raw is not None

    def check(self, state: float | int, previous_states: list[tuple[float, float | int | str]]) -> bool:
        if state is None or not isinstance(state, (float, int)) or (self.min_raw is None and self.max_raw is None) or (self.delta and len(previous_states) == 0):
            return True
        if self.delta:
            if len(previous_states) > 0 and isinstance(previous_states[-1][1], (float, int)):
                previous_value = previous_states[-1][1]
                value = state - previous_value  # pyrefly: ignore
            else:
                return True
        else:
            value = state
        if self.min_raw is None and self.max_raw is not None:
            if value > self.max_raw:
                raise SanityCheckException(f"Raw {'delta' if self.delta else 'value'} {value} exceeds sanity check maximum {self.max_raw} ({state=} {previous_states=})")
        elif self.max_raw is None and self.min_raw is not None:
            if value < self.min_raw:
                raise SanityCheckException(f"Raw {'delta' if self.delta else 'value'} {value} is below sanity check minimum {self.min_raw} ({state=} {previous_states=})")
        elif self.min_raw is not None and self.max_raw is not None and not (self.min_raw <= value <= self.max_raw):
            raise SanityCheckException(f"Raw {'delta' if self.delta else 'value'} {value} is not within sanity check range {self.min_raw} to {self.max_raw} ({state=} {previous_states=})")
        return True
