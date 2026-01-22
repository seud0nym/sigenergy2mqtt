import ast
from pathlib import Path

from ruamel.yaml import YAML

# Initialize YAML with specific settings for en.yaml
yaml_parser = YAML()
yaml_parser.indent(mapping=2, sequence=4, offset=2)
yaml_parser.preserve_quotes = True
yaml_parser.width = 1000  # Avoid wrapping


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
                    # But only if it's likely a name (string)
                    if isinstance(node.args[0].value, str):
                        self._add_translation(self.current_class, "name", node.args[0].value)

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
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and elt.value.strip():
                                    options[str(i)] = elt.value
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


if __name__ == "__main__":
    package_dir = Path(__file__).parent.parent / "sigenergy2mqtt"
    all_translations = {
        "AlarmSensor": {"no_alarm": "No Alarm", "unknown_alarm": "Unknown (bit{bit}∈{value})"},
        "ReadOnlySensor": {"attributes": {"source": "Modbus Register {address}", "source_range": "Modbus Registers {start}-{end}"}},
        "MqttOverriddenSensor": {"attributes": {"source": "MQTT Override"}},
    }

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

    en_yaml_path = package_dir / "locales" / "en.yaml"
    with open(en_yaml_path, "w", encoding="utf-8") as f:
        yaml_parser.dump(all_translations, f)
    print(f"Successfully updated {en_yaml_path}")
