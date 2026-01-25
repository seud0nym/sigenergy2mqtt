import glob
import os
import sys

import pytest
from ruamel.yaml import YAML, YAMLError


def test_translations_are_valid_yaml():
    # Resolve path relative to this file: tests/unit/test_translations_validity.py
    # Access ../../sigenergy2mqtt/locales
    base_dir = os.path.dirname(os.path.abspath(__file__))
    translations_dir = os.path.join(base_dir, "../../sigenergy2mqtt/locales")

    # Normalize path
    translations_dir = os.path.normpath(translations_dir)

    pattern = os.path.join(translations_dir, "*.yaml")
    files = glob.glob(pattern)

    assert len(files) > 0, f"No translation files found in {translations_dir}"

    yaml = YAML(typ="safe", pure=True)

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                yaml.load(f)
            except YAMLError as exc:
                pytest.fail(f"Invalid YAML in {file_path}:\n{exc}")


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
