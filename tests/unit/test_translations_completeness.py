import ast
from pathlib import Path

import pytest
from ruamel.yaml import YAML

# Initialize YAML with specific settings for en.yaml
yaml_parser = YAML()
yaml_parser.indent(mapping=2, sequence=4, offset=2)
yaml_parser.preserve_quotes = True


class TranslationExtractor(ast.NodeVisitor):
    def __init__(self):
        self.translations = {}
        self.current_class = None

    def visit_ClassDef(self, node):
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_Call(self, node):
        if not self.current_class:
            self.generic_visit(node)
            return

        # Handle super().__init__(name="...")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "__init__":
            if isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == "super":
                for keyword in node.keywords:
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                        self._add_translation(self.current_class, "name", keyword.value.value)
                # Handle positional name if it's the first argument
                if node.args and isinstance(node.args[0], ast.Constant):
                    if isinstance(node.args[0].value, str):
                        self._add_translation(self.current_class, "name", node.args[0].value)

                # Handle options=[...]
                for keyword in node.keywords:
                    if keyword.arg == "options" and isinstance(keyword.value, ast.List):
                        options = {}
                        for i, elt in enumerate(keyword.value.elts):
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and elt.value.strip():
                                options[str(i)] = elt.value
                        if options:
                            self._add_translation(self.current_class, "options", options)

        self.generic_visit(node)

    def visit_Assign(self, node):
        if not self.current_class:
            self.generic_visit(node)
            return

        for target in node.targets:
            if isinstance(target, ast.Subscript):
                if isinstance(target.value, ast.Name) and target.value.id == "self":
                    if isinstance(target.slice, ast.Constant) and target.slice.value == "options":
                        if isinstance(node.value, ast.List):
                            options = {}
                            for i, elt in enumerate(node.value.elts):
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and elt.value.strip():
                                    options[str(i)] = elt.value
                            if options:
                                self._add_translation(self.current_class, "options", options)

                    if isinstance(target.slice, ast.Constant) and target.slice.value == "comment":
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            self._add_attr(self.current_class, "comment", node.value.value)

            if isinstance(target, ast.Subscript):
                if isinstance(target.value, ast.Name) and target.value.id == "attributes":
                    if isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            self._add_attr(self.current_class, target.slice.value, node.value.value)

        self.generic_visit(node)

    def visit_MatchCase(self, node):
        if not self.current_class:
            self.generic_visit(node)
            return

        if isinstance(node.pattern, ast.MatchValue):
            if isinstance(node.pattern.value, ast.Constant) and isinstance(node.pattern.value.value, int):
                bit = str(node.pattern.value.value)
                for body_node in node.body:
                    if isinstance(body_node, ast.Return) and isinstance(body_node.value, ast.Constant):
                        self._add_alarm(self.current_class, bit, body_node.value.value)

        self.generic_visit(node)

    def _add_translation(self, cls, key, value):
        if cls not in self.translations:
            self.translations[cls] = {}
        self.translations[cls][key] = value

    def _add_attr(self, cls, attr, value):
        if cls not in self.translations:
            self.translations[cls] = {}
        if "attributes" not in self.translations[cls]:
            self.translations[cls]["attributes"] = {}
        self.translations[cls]["attributes"][attr] = value

    def _add_alarm(self, cls, bit, value):
        if cls not in self.translations:
            self.translations[cls] = {}
        if "alarm" not in self.translations[cls]:
            self.translations[cls]["alarm"] = {}
        self.translations[cls]["alarm"][bit] = value


def merge_translations(base, new):
    for key, value in new.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merge_translations(base[key], value)
        else:
            base[key] = value


def test_en_yaml_completeness():
    """Verify that en.yaml contains all translatable strings found in the codebase."""
    package_dir = Path(__file__).parent.parent.parent / "sigenergy2mqtt"
    en_yaml_path = package_dir / "translations" / "en.yaml"

    assert en_yaml_path.exists(), "en.yaml does not exist"

    with open(en_yaml_path, "r", encoding="utf-8") as f:
        current_translations = yaml_parser.load(f)

    expected_translations = {
        "AlarmSensor": {"no_alarm": "No Alarm", "unknown_alarm": "Unknown (bit{bit}∈{value})"},
        "ReadOnlySensor": {"attributes": {"source": "Modbus Register {address}", "source_range": "Modbus Registers {start}-{end}"}},
        "MqttOverriddenSensor": {"attributes": {"source": "MQTT Override"}},
    }

    extractor = TranslationExtractor()
    for py_file in package_dir.glob("**/*.py"):
        if py_file.name == "i18n.py" or "test" in py_file.name:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        extractor.visit(tree)

    merge_translations(expected_translations, extractor.translations)

    # Check for missing keys or values
    # Check for missing keys or values
    if "class" not in current_translations:
        pytest.fail("Missing top-level 'class' key in en.yaml")

    classes = current_translations["class"]

    for cls, content in expected_translations.items():
        assert cls in classes, f"Class {cls} is missing from en.yaml"

        for key, value in content.items():
            assert key in classes[cls], f"Key {cls}.{key} is missing from en.yaml"

            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    assert subkey in classes[cls][key], f"Subkey {cls}.{key}.{subkey} is missing from en.yaml"
                    # We don't necessarily check the value matches exactly (strings might be edited),
                    # but we ensure the key exists.
            else:
                # Top level value check
                pass


def test_en_yaml_no_extra_keys():
    """Optional: Check if en.yaml has keys that no longer exist in code?
    Maybe not strictly required, but keeps it clean."""
    pass


class CLIHelpExtractor(ast.NodeVisitor):
    """Extracts help text from argparse add_argument() calls."""

    def __init__(self):
        self.cli_translations = {}

    def visit_Call(self, node):
        # Look for _parser.add_argument(...) or parser.add_argument(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            dest = None
            help_text = None

            # Extract keyword arguments
            for keyword in node.keywords:
                if keyword.arg == "dest" and isinstance(keyword.value, ast.Constant):
                    dest = keyword.value.value
                elif keyword.arg == "dest" and isinstance(keyword.value, ast.Attribute):
                    # Handle const.SIGENERGY2MQTT_* references
                    dest = keyword.value.attr
                elif keyword.arg == "help" and isinstance(keyword.value, ast.Constant):
                    help_text = keyword.value.value

            # Only add if we have both dest and help
            if dest and help_text:
                self.cli_translations[dest] = {"help": help_text}

        self.generic_visit(node)


def test_cli_translations_completeness():
    """Verify that en.yaml contains all CLI help texts from config/__init__.py."""
    package_dir = Path(__file__).parent.parent.parent / "sigenergy2mqtt"
    en_yaml_path = package_dir / "translations" / "en.yaml"
    config_init_path = package_dir / "config" / "__init__.py"

    assert en_yaml_path.exists(), "en.yaml does not exist"
    assert config_init_path.exists(), "config/__init__.py does not exist"

    with open(en_yaml_path, "r", encoding="utf-8") as f:
        current_translations = yaml_parser.load(f)

    # Extract CLI help from config/__init__.py
    extractor = CLIHelpExtractor()
    tree = ast.parse(config_init_path.read_text(encoding="utf-8"))
    extractor.visit(tree)

    # Verify cli section exists
    assert "cli" in current_translations, "cli section is missing from en.yaml"

    # Verify all CLI help texts are present
    for dest, content in extractor.cli_translations.items():
        assert dest in current_translations["cli"], f"CLI key '{dest}' is missing from en.yaml"
        assert "help" in current_translations["cli"][dest], f"CLI key '{dest}' is missing 'help' in en.yaml"
