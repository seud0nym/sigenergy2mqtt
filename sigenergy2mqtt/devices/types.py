class DeviceType:
    """Base class for Inverter types"""


class HybridInverter(DeviceType):
    """Marker class for sensors applicable to the Hybrid Inverter"""

    def __str__(self):
        return "Hybrid Inverter"


class PVInverter(DeviceType):
    """Marker class for sensors applicable to the PV Inverter"""

    def __str__(self):
        return "PV Inverter"
