import re


class DeviceType:
    """Base class for Inverter types"""

    @classmethod
    def create(cls, model_id: str):
        device_type = HybridInverter() if re.search(r"EC|Hybrid|PG|PV.*M1-HY", model_id) else PVInverter()
        device_type._model_id = model_id
        return device_type

    @property
    def has_independent_phase_power_control_interface(self) -> bool:
        """Independent phase power control interface (registers 40008~40025, 40030), only SigenStor, Sigen Hybrid, Sigen PV M1-HYB series support"""
        return True if re.search(r"SigenStor|Hybrid|PV.*M1-HYB", self._model_id) else False

    @property
    def has_grid_code_interface(self) -> bool:
        """Grid code interface (registers 40051~40068), only SigenStor, Sigen Hybrid support"""
        return True if re.search(r"SigenStor|Hybrid", self._model_id) else False


class HybridInverter(DeviceType):
    """Applicable Models:
    SigenStor EC (3.0, 3.6, 4.0, 4.6, 5.0, 6.0, 8.0, 10.0, 12.0) SP series
    Sigen Hybrid (3.0, 3.6, 4.0, 4.6, 5.0, 6.0) SP
    Sigen Hybrid (5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 17.0, 20.0, 25.0, 30.0) TP series
    SigenStor EC (5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 17.0, 20.0, 25.0, 30.0) TP/TPLV series
    Sigen PV (50, 60, 80, 99.9, 100, 110, 125) M1-HYA series
    PG Controller (3.8, 4.8, 5.7, 7.6, 9.6, 11.4) series
    Sigen PV (50, 60, 80, 99.9, 100, 110) M1-HYB series
    """

    def __str__(self):
        return "Hybrid Inverter"


class PVInverter(DeviceType):
    """Applicable Models:
    Sigen PV Max (3.0, 3.6, 4.0, 4.6, 5.0, 6.0) SP
    Sigen PV Max (5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 17.0, 20.0, 25.0) TP
    Sigen PV (50, 60, 80, 99.9, 100, 110, 125)M1 series
    Sigen PV (500)H1 series
    """

    def __str__(self):
        return "PV Inverter"
