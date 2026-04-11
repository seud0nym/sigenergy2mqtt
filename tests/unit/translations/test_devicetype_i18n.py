from unittest.mock import patch

from sigenergy2mqtt.common import HybridInverter, PVInverter


def test_hybrid_inverter_str_i18n():
    hybrid = HybridInverter()
    hybrid._model_id = "SigenStor EC"

    # Test default English
    with patch("sigenergy2mqtt.i18n._translator.translate", return_value=("Hybrid Inverter", "en", True)):
        assert str(hybrid) == "Hybrid Inverter"

    # Test translation
    with patch("sigenergy2mqtt.i18n._translator.translate", return_value=("Hybrid-Wechselrichter", "de", True)):
        assert str(hybrid) == "Hybrid-Wechselrichter"


def test_pv_inverter_str_i18n():
    pv = PVInverter()
    pv._model_id = "Sigen PV Max"

    # Test default English
    with patch("sigenergy2mqtt.i18n._translator.translate", return_value=("PV Inverter", "en", True)):
        assert str(pv) == "PV Inverter"

    # Test translation
    with patch("sigenergy2mqtt.i18n._translator.translate", return_value=("PV-Wechselrichter", "de", True)):
        assert str(pv) == "PV-Wechselrichter"
