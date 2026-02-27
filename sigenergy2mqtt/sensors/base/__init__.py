"""Base sensor module for Sigenergy sensors."""

from __future__ import annotations

import asyncio  # noqa: F401
import logging  # noqa: F401
import re  # noqa: F401
import sys  # noqa: F401
import time  # noqa: F401
from pathlib import Path  # noqa: F401

from sigenergy2mqtt.common import DeviceType, Protocol  # noqa: F401
from sigenergy2mqtt.config import active_config  # noqa: F401
from sigenergy2mqtt.i18n import _t  # noqa: F401
from sigenergy2mqtt.metrics import Metrics  # noqa: F401
from sigenergy2mqtt.modbus.types import ModbusDataType  # noqa: F401

# Accumulation sensors
from .accumulation import (  # noqa: F401
    EnergyDailyAccumulationSensor,
    EnergyLifetimeAccumulationSensor,
    ResettableAccumulationSensor,
)

# Alarm sensors
from .alarms import (  # noqa: F401
    Alarm1Sensor,
    Alarm2Sensor,
    Alarm3Sensor,
    Alarm4Sensor,
    Alarm5Sensor,
    AlarmCombinedSensor,
    AlarmSensor,
    RunningStateSensor,
)

# Constants and utilities
from .constants import (  # noqa: F401
    DiscoveryKeys,
    ModbusLockFactory,
    SensorAttribute,
    SensorAttributeKeys,
    SensorDict,
    SensorValue,
    StateHistory,
    _sanitize_path_component,
)

# Derived sensors
from .derived import DerivedSensor  # noqa: F401

# Behaviour mixins
from .mixins import (  # noqa: F401
    ModbusSensorMixin,
    ObservableMixin,
    PVPowerSensor,
    ReadableSensorMixin,
    SubstituteMixin,
    WritableSensorMixin,
)

# Readable sensors
from .readable import (  # noqa: F401
    ReadOnlySensor,
    ReservedSensor,
    UnpublishResetSensorMixin,
)

# Re-export commonly used types from const and sanity_check for convenience
from .sanity_check import SanityCheck, SanityCheckException  # noqa: F401

# Scan Interval
from .scan_interval import (  # noqa: F401
    ScanInterval,
)

# Base sensor and core mixins
from .sensor import (  # noqa: F401
    AvailabilityMixin,
    Sensor,
    SensorDebuggingMixin,
    TypedSensorMixin,
)

# Timestamp sensors
from .timestamp import TimestampSensor  # noqa: F401

# Writable sensors
from .writable import (  # noqa: F401
    NumericSensor,
    ReadWriteSensor,
    SelectSensor,
    SwitchSensor,
    ThreePhaseAdjustmentTargetValue,
    WriteOnlySensor,
)
