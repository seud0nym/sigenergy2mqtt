import ast
from pathlib import Path

from ruamel.yaml import YAML

# Initialize YAML with specific settings for en.yaml
yaml_parser = YAML()
yaml_parser.indent(mapping=2, sequence=4, offset=2)
yaml_parser.preserve_quotes = True
yaml_parser.width = 1000  # Avoid wrapping


RESET_TRANSLATIONS = {
    "de": "Setze {name}",
    "es": "Establecer {name}",
    "fr": "Régler {name}",
    "it": "Imposta {name}",
    "ja": "{name}を設定",
    "ko": "{name} 설정",
    "nl": "Stel {name} in",
    "pt": "Definir {name}",
    "zh": "设置 {name}",
}


class TranslationExtractor(ast.NodeVisitor):
    def __init__(self):
        self.translations = {}
        self.current_class = None
        self.is_resettable = False
        self.resettable_bases = {"ResettableAccumulationSensor", "EnergyDailyAccumulationSensor", "EnergyLifetimeAccumulationSensor"}

    def _get_string_values(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.JoinedStr):
            parts = []
            for val in node.values:
                if isinstance(val, ast.Constant):
                    parts.append(str(val.value))
                elif isinstance(val, ast.FormattedValue):
                    # Try to extract the name if it's a simple variable or expression
                    if isinstance(val.value, ast.Name):
                        parts.append(f"{{{val.value.id}}}")
                    elif isinstance(val.value, ast.Attribute) and isinstance(val.value.value, ast.Name):
                        parts.append(f"{{{val.value.value.id}.{val.value.attr}}}")
                    elif isinstance(val.value, ast.Call) and isinstance(val.value.func, ast.Attribute) and val.value.func.attr == "lower":
                        if isinstance(val.value.func.value, ast.Name):
                            parts.append(f"{{{val.value.func.value.id}}}")
                    else:
                        parts.append("{}")
            return ["".join(parts)]
        if isinstance(node, ast.IfExp):
            return self._get_string_values(node.body) + self._get_string_values(node.orelse)
        return []

    def visit_ClassDef(self, node):
        prev_class = self.current_class
        prev_resettable = self.is_resettable
        self.current_class = node.name

        # Check if class inherits from a resettable base
        self.is_resettable = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in self.resettable_bases:
                self.is_resettable = True
                break

        self.generic_visit(node)
        self.current_class = prev_class
        self.is_resettable = prev_resettable

    def visit_Call(self, node):
        if not self.current_class:
            self.generic_visit(node)
            return

        # Handle super().__init__(name="...")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "__init__":
            if isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == "super":
                name_value = None
                for keyword in node.keywords:
                    if keyword.arg == "name":
                        names = self._get_string_values(keyword.value)
                        if names:
                            name_value = names[0]
                            self._add_translation(self.current_class, "name", name_value)
                    elif keyword.arg in ["name_off", "name_on"]:
                        names = self._get_string_values(keyword.value)
                        if names:
                            self._add_translation(self.current_class, keyword.arg, names[0])
                # Handle positional name if it's the first argument
                if node.args:
                    names = self._get_string_values(node.args[0])
                    if names:
                        name_value = names[0]
                        self._add_translation(self.current_class, "name", name_value)

                # If this is a resettable sensor and we found a name, add the reset name translation
                if self.is_resettable and name_value:
                    self._add_translation(self.current_class, "name_reset", f"Set {name_value}")

                # Handle options=[...]
                for keyword in node.keywords:
                    if keyword.arg == "options" and isinstance(keyword.value, ast.List):
                        options = {}
                        for i, elt in enumerate(keyword.value.elts):
                            opt_values = self._get_string_values(elt)
                            if opt_values and opt_values[0].strip():
                                options[str(i)] = opt_values[0]
                        if options:
                            self._add_translation(self.current_class, "options", options)

        self.generic_visit(node)

    def visit_Assign(self, node):
        if not self.current_class:
            self.generic_visit(node)
            return

        # Handle self["options"] = [...]
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                if isinstance(target.value, ast.Name) and target.value.id == "self":
                    if isinstance(target.slice, ast.Constant) and target.slice.value == "options":
                        if isinstance(node.value, ast.List):
                            options = {}
                            for i, elt in enumerate(node.value.elts):
                                opt_values = self._get_string_values(elt)
                                if opt_values and opt_values[0].strip():
                                    options[str(i)] = opt_values[0]
                            if options:
                                self._add_translation(self.current_class, "options", options)

                    # Handle self["comment"] = "..."
                    if isinstance(target.slice, ast.Constant) and target.slice.value == "comment":
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            self._add_attr(self.current_class, "comment", node.value.value)

            # Handle attributes["comment"] = "..."
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

        # Handle AlarmSensor bit decoding
        if isinstance(node.pattern, ast.MatchValue):
            if isinstance(node.pattern.value, ast.Constant) and isinstance(node.pattern.value.value, int):
                bit = str(node.pattern.value.value)
                # Look for return "..." in the body
                for body_node in node.body:
                    if isinstance(body_node, ast.Return):
                        names = self._get_string_values(body_node.value)
                        if names and names[0].strip():
                            self._add_alarm(self.current_class, bit, names[0])

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


def extract_cli_help(config_init_path: Path) -> dict:
    """Extract CLI help text from config/__init__.py."""
    extractor = CLIHelpExtractor()
    tree = ast.parse(config_init_path.read_text(encoding="utf-8"))
    extractor.visit(tree)
    return extractor.cli_translations


def merge_translations(base, new):
    for key, value in new.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merge_translations(base[key], value)
        else:
            base[key] = value


def propagate_to_other_translations(en_translations: dict, translations_dir: Path):
    """Add new keys to other locale files, preserving existing translations."""
    for locale_file in translations_dir.glob("*.yaml"):
        if locale_file.name == "en.yaml":
            continue

        locale_code = locale_file.stem
        print(f"Updating {locale_file.name}...")

        # Load existing translations
        with open(locale_file, "r", encoding="utf-8") as f:
            existing = yaml_parser.load(f) or {}

        # Add new keys from English, preserving existing translations
        updated = False
        for key, value in en_translations.items():
            if key not in existing:
                # Add the entire new section
                if isinstance(value, dict):
                    # Check if any nested key needs translation
                    new_section = value.copy()
                    if "name_reset" in new_section and locale_code in RESET_TRANSLATIONS:
                        # Translate "Set {name}"
                        # Try to find the base name from 'name' key if available, otherwise parse from English string
                        base_name = new_section.get("name", "")
                        if not base_name and new_section["name_reset"].startswith("Set "):
                            base_name = new_section["name_reset"][4:]

                        if base_name:
                            new_section["name_reset"] = RESET_TRANSLATIONS[locale_code].format(name=base_name)

                    existing[key] = new_section
                else:
                    existing[key] = value

                updated = True
                print(f"  Added new key: {key}")
            elif isinstance(value, dict):
                # Recursively add missing sub-keys
                for subkey, subvalue in value.items():
                    if subkey not in existing[key]:
                        # Handle name_reset specifically
                        if subkey == "name_reset" and locale_code in RESET_TRANSLATIONS:
                            base_name = ""
                            # Try to get existing translated name first
                            if "name" in existing[key]:
                                base_name = existing[key]["name"]
                            elif "name" in value:
                                base_name = value["name"]  # Fallback to English name

                            if not base_name and isinstance(subvalue, str) and subvalue.startswith("Set "):
                                base_name = subvalue[4:]

                            if base_name:
                                existing[key][subkey] = RESET_TRANSLATIONS[locale_code].format(name=base_name)
                            else:
                                existing[key][subkey] = subvalue
                        else:
                            existing[key][subkey] = subvalue
                        updated = True
                        print(f"  Added new subkey: {key}.{subkey}")
                    elif isinstance(subvalue, dict):
                        for subsubkey, subsubvalue in subvalue.items():
                            if subsubkey not in existing[key][subkey]:
                                existing[key][subkey][subsubkey] = subsubvalue
                                updated = True
                                print(f"  Added new subsubkey: {key}.{subkey}.{subsubkey}")

        if updated:
            with open(locale_file, "w", encoding="utf-8") as f:
                yaml_parser.dump(existing, f)
            print(f"  Saved {locale_file.name}")
        else:
            print(f"  No changes needed for {locale_file.name}")


if __name__ == "__main__":
    package_dir = Path(__file__).parent.parent / "sigenergy2mqtt"
    all_translations = {
        "AlarmSensor": {"no_alarm": "No Alarm", "unknown_alarm": "Unknown (bit{bit}∈{value})"},
        "ReadOnlySensor": {"attributes": {"source": "Modbus Register {address}", "source_range": "Modbus Registers {start}-{end}"}},
        "WriteOnlySensor": {"name_on": "Power On", "name_off": "Power Off"},
        "MqttOverriddenSensor": {"attributes": {"source": "MQTT Override"}},
    }

    # Extract sensor translations
    extractor = TranslationExtractor()
    for py_file in package_dir.glob("**/*.py"):
        if py_file.name == "i18n.py" or "test" in py_file.name:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            extractor.visit(tree)
        except Exception as e:
            print(f"Error parsing {py_file}: {e}")

    merge_translations(all_translations, extractor.translations)

    # Extract CLI help text
    config_init_path = package_dir / "config" / "__init__.py"
    cli_translations = extract_cli_help(config_init_path)
    if cli_translations:
        all_translations["cli"] = cli_translations
        print(f"Extracted {len(cli_translations)} CLI help texts")

    # Write en.yaml
    en_yaml_path = package_dir / "translations" / "en.yaml"
    with open(en_yaml_path, "w", encoding="utf-8") as f:
        yaml_parser.dump(all_translations, f)
    print(f"Successfully updated {en_yaml_path}")

    # Propagate new keys to other locale files
    translations_dir = package_dir / "translations"
    propagate_to_other_translations(all_translations, translations_dir)
    print("Done!")
