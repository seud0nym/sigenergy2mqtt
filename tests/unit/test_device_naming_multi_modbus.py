import copy

from sigenergy2mqtt.common import HybridInverter, Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices import ACCharger, DCCharger, ESS, Inverter, PVString, PowerPlant


def test_multi_modbus_device_naming_uses_plant_index():
    cfg = Config()
    cfg.modbus = [cfg.modbus[0], copy.deepcopy(cfg.modbus[0])]

    with _swap_active_config(cfg):
        plant0 = PowerPlant(0, HybridInverter(), Protocol.V2_8)
        plant1 = PowerPlant(1, HybridInverter(), Protocol.V2_8)

        inverter1 = Inverter(1, 1, HybridInverter(), Protocol.V2_8, "SigenStor EC 10.0 SP", "SN123", "V01.01.113")
        ess1 = ESS(1, 1, HybridInverter(), Protocol.V2_8, "SigenStor EC 10.0 SP", "SN123")
        pv_string1 = PVString(1, 1, HybridInverter(), "SigenStor EC 10.0 SP", "SN123", 1, 31027, 31028, Protocol.V2_8)
        ac1 = ACCharger(1, 248 - 1, Protocol.V2_8)
        dc1 = DCCharger(1, 248 - 1, Protocol.V2_8)

    assert plant0["name"] == "Sigenergy Plant"
    assert plant1["name"] == "Sigenergy Plant 2"

    assert inverter1["name"].startswith("Sigenergy Plant 2 ")
    assert ess1["name"].startswith("Sigenergy Plant 2 ")
    assert pv_string1["name"] == "SigenStor SN123 PV String 1"
    assert ac1["name"] == "Sigenergy Plant 2 AC Charger"
    assert dc1["name"] == "Sigenergy Plant 2 DC Charger"
