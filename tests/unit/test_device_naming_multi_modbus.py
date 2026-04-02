import copy

from sigenergy2mqtt.common import HybridInverter, Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices import ACCharger, DCCharger, ESS, Inverter, PVString, PowerPlant


def test_multi_modbus_device_naming_uses_plant_index_and_charger_sequence():
    cfg = Config()
    cfg.modbus = [cfg.modbus[0], copy.deepcopy(cfg.modbus[0])]

    with _swap_active_config(cfg):
        plant0 = PowerPlant(0, HybridInverter(), Protocol.V2_8)
        plant1 = PowerPlant(1, HybridInverter(), Protocol.V2_8)

        inverter1 = Inverter(1, 1, HybridInverter(), Protocol.V2_8, "SigenStor EC 10.0 SP", "SN123", "V01.01.113")
        ess1 = ESS(1, 1, HybridInverter(), Protocol.V2_8, "SigenStor EC 10.0 SP", "SN123")
        pv_string1 = PVString(1, 1, HybridInverter(), "SigenStor EC 10.0 SP", "SN123", 1, 31027, 31028, Protocol.V2_8)
        ac1 = ACCharger(1, 248 - 1, Protocol.V2_8, sequence_number=1, total_count=2)
        ac2 = ACCharger(0, 248 - 2, Protocol.V2_8, sequence_number=2, total_count=2)
        dc1 = DCCharger(1, 248 - 1, Protocol.V2_8, sequence_number=1, total_count=2)
        dc2 = DCCharger(0, 248 - 2, Protocol.V2_8, sequence_number=2, total_count=2)

    assert plant0["name"] == "Sigenergy Plant"
    assert plant1["name"] == "Sigenergy Plant 2"

    assert inverter1["name"].startswith("Sigenergy Plant 2 ")
    assert ess1["name"] == "SigenStor SN123 ESS"
    assert pv_string1["name"] == "SigenStor SN123 PV String 1"
    assert ac1["name"] == "Sigenergy AC Charger 1"
    assert ac2["name"] == "Sigenergy AC Charger 2"
    assert dc1["name"] == "Sigenergy DC Charger 1"
    assert dc2["name"] == "Sigenergy DC Charger 2"
