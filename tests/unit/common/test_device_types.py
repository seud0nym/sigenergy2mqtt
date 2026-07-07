import importlib.util
from pathlib import Path


def _load_production_types_module():
    module_path = Path(__file__).resolve().parents[3] / "sigenergy2mqtt" / "common" / "types.py"
    spec = importlib.util.spec_from_file_location("production_common_types", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_non_inverter_string_is_empty():
    types_module = _load_production_types_module()

    assert str(types_module.NonInverter()) == ""
