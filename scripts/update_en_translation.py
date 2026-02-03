import ast
from pathlib import Path
from typing import TypeVar, cast

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
    "zh-Hans": "设置 {name}",
}


T = TypeVar("T", dict, list)


def sort_dict(d: T) -> T:
    """Recursively sort dictionary keys."""
    if isinstance(d, dict):

        def sort_key(k):
            try:
                # Try sorting as integer if possible (for alarm bits, etc.)
                return (0, int(k))
            except (ValueError, TypeError):
                # Otherwise sort as string
                return (1, str(k))

        return cast(T, {k: sort_dict(v) for k, v in sorted(d.items(), key=lambda x: sort_key(x[0]))})
    if isinstance(d, list):
        return cast(T, [sort_dict(i) for i in d])
    return d


def prune_empty_dicts(d: T) -> T:
    """Recursively remove empty dictionaries."""
    if not isinstance(d, dict):
        return d

    to_delete = []
    for k, v in d.items():
        if isinstance(v, dict):
            pruned = prune_empty_dicts(v)
            if not pruned:  # Empty dictionary
                to_delete.append(k)
        elif v is None or (isinstance(v, str) and not v.strip()):
            to_delete.append(k)

    for k in to_delete:
        del d[k]

    return d


def get_ast_string_values(node):
    """Extract string values from an AST node, handling constants, f-strings, and concatenation."""
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
                elif isinstance(val.value, ast.Attribute) and isinstance(val.value.value, ast.Attribute) and val.value.attr == "__name__" and val.value.value.attr == "__class__":
                    parts.append("{self}")
                else:
                    # Be more aggressive: try to find any Name in the expression
                    found_names = [n.id for n in ast.walk(val.value) if isinstance(n, ast.Name)]
                    if found_names:
                        clean_names = [n for n in found_names if n != "self"]
                        parts.append(f"{{{clean_names[0] if clean_names else found_names[0]}}}")
                    else:
                        parts.append("{}")
        return ["".join(parts)]
    if isinstance(node, ast.IfExp):
        return get_ast_string_values(node.body) + get_ast_string_values(node.orelse)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = get_ast_string_values(node.left)
        right = get_ast_string_values(node.right)
        if left and right:
            return [l + r for l in left for r in right]  # noqa: E741
        return left or right
    if isinstance(node, ast.List):
        res = []
        for elt in node.elts:
            res.extend(get_ast_string_values(elt))
        return res
    if isinstance(node, ast.Call):
        # Handle " ".join(words)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            if isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str):
                sep = node.func.value.value
                if node.args:
                    vals = get_ast_string_values(node.args[0])
                    if vals:
                        return [sep.join(vals)]
                    else:
                        # If we can't resolve the items, try to find names in the argument
                        found_names = [n.id for n in ast.walk(node.args[0]) if isinstance(n, ast.Name)]
                        if found_names:
                            return [f"{{{found_names[0]}}}"]
    return []


class TranslationExtractor(ast.NodeVisitor):
    def __init__(self):
        self.translations = {}
        self.current_class = None
        self.is_resettable = False
        self.resettable_bases = {"ResettableAccumulationSensor", "EnergyDailyAccumulationSensor", "EnergyLifetimeAccumulationSensor"}
        self.class_bases = {}
        self.local_vars = {}
        self.ignore_name_classes = {"Device", "ModbusDevice", "Service"}

    def visit_ClassDef(self, node):
        prev_class = self.current_class
        prev_resettable = self.is_resettable
        self.current_class = node.name

        # Check if class inherits from a resettable base
        self.is_resettable = False
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
                if base.id in self.resettable_bases:
                    self.is_resettable = True
            elif isinstance(base, ast.Attribute) and isinstance(base.attr, str):
                bases.append(base.attr)

        if bases:
            self.class_bases[node.name] = bases

        self.generic_visit(node)
        self.current_class = prev_class
        self.is_resettable = prev_resettable

    def visit_FunctionDef(self, node):
        prev_vars = self.local_vars
        self.local_vars = {}
        self.generic_visit(node)
        self.local_vars = prev_vars

    def visit_AsyncFunctionDef(self, node):
        prev_vars = self.local_vars
        self.local_vars = {}
        self.generic_visit(node)
        self.local_vars = prev_vars

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
                        names = get_ast_string_values(keyword.value)
                        if names:
                            name_value = names[0]
                            self._add_translation(self.current_class, "name", name_value)
                    elif keyword.arg in ["name_off", "name_on"]:
                        names = get_ast_string_values(keyword.value)
                        if names:
                            self._add_translation(self.current_class, keyword.arg, names[0])

                # If name not found in keywords, try positional args
                if not name_value and node.args:
                    # ModbusDevice and its subclasses have type as first argument, name as second
                    arg_index = 0
                    bases = self.class_bases.get(self.current_class, [])
                    if "ModbusDevice" in bases or any(b in bases for b in ["Inverter", "ACCharger", "DCCharger", "ESS", "PVString", "PowerPlant", "GridSensor", "GridCode"]):
                        arg_index = 1

                    if len(node.args) > arg_index:
                        # Try to resolve from local variables FIRST
                        if isinstance(node.args[arg_index], ast.Name):
                            var_name = node.args[arg_index].id  # type: ignore
                            if var_name in self.local_vars:
                                name_value = self.local_vars[var_name]

                        # Fallback to direct string extraction
                        if not name_value:
                            names = get_ast_string_values(node.args[arg_index])
                            if names:
                                name_value = names[0]

                        # Handle specific dynamic cases for Inverter/ESS
                        if not name_value or name_value in ["{words}", "{name}", "{}"]:
                            if self.current_class == "Inverter":
                                name_value = "{model_id} {serial}"
                            elif self.current_class == "ESS":
                                name_value = "{model_id} {serial_number} ESS"
                            elif self.current_class == "PVString":
                                name_value = "{model_id} {serial_number} PV String {string_number}"

                        # Still no name? Try the model argument (index 4 for ModbusDevice/Device)
                        if not name_value or name_value in ["{words}", "{name}", "{}"]:
                            model_index = 4
                            if len(node.args) > model_index:
                                model_names = get_ast_string_values(node.args[model_index])
                                if model_names:
                                    name_value = model_names[0]

                        if name_value and self.current_class not in self.ignore_name_classes:
                            self._add_translation(self.current_class, "name", name_value)

                # If this is a resettable sensor and we found a name, add the reset name translation
                if self.is_resettable and name_value:
                    self._add_translation(self.current_class, "name_reset", f"Set {name_value}")

                # Handle options=[...]
                for keyword in node.keywords:
                    if keyword.arg == "options" and isinstance(keyword.value, ast.List):
                        options = {}
                        for i, elt in enumerate(keyword.value.elts):
                            opt_values = get_ast_string_values(elt)
                            if opt_values and opt_values[0].strip():
                                options[str(i)] = opt_values[0]
                        if options:
                            self._add_translation(self.current_class, "options", options)

        # Handle _t("key", "default")
        if isinstance(node.func, ast.Name) and node.func.id == "_t":
            if len(node.args) >= 2:
                names = get_ast_string_values(node.args[0])
                if names:
                    key = names[0]
                    defaults = get_ast_string_values(node.args[1])
                    if defaults:
                        default = defaults[0]
                        if self.current_class:
                            # Replace {self} or {} if it's the class name key or similar
                            key = key.replace("{self}", self.current_class).replace("{}", self.current_class)

                            # If it's something like "HybridInverter.name", extract the subkey
                            if key.startswith(f"{self.current_class}."):
                                sub_key = key[len(self.current_class) + 1 :]
                                self._add_translation(self.current_class, sub_key, default)
                            else:
                                # Possibly a generic key used within a class, but we don't have a place for it
                                # besides under the class itself in our current yaml structure.
                                # For now, let's assume it's meant to be a subkey if it has no dot.
                                if "." not in key:
                                    self._add_translation(self.current_class, key, default)

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
                                opt_values = get_ast_string_values(elt)
                                if opt_values and opt_values[0].strip():
                                    options[str(i)] = opt_values[0]
                            if options:
                                self._add_translation(self.current_class, "options", options)

                    # Handle self["comment"] = "..."
                    if isinstance(target.slice, ast.Constant) and target.slice.value == "comment":
                        vals = get_ast_string_values(node.value)
                        if vals:
                            self._add_attr(self.current_class, "comment", vals[0])

            # Handle attributes["comment"] = "..."
            if isinstance(target, ast.Subscript):
                if isinstance(target.value, ast.Name) and target.value.id == "attributes":
                    if isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str):
                        vals = get_ast_string_values(node.value)
                        if vals:
                            self._add_attr(self.current_class, target.slice.value, vals[0])

            # Handle name = "..." (local variable tracking)
            if isinstance(target, ast.Name):
                names = get_ast_string_values(node.value)
                if names:
                    self.local_vars[target.id] = names[0]

            # Handle self.name = "..." or self["name"] = "..."
            if isinstance(target, ast.Attribute) and target.attr == "name" and isinstance(target.value, ast.Name) and target.value.id == "self":
                names = get_ast_string_values(node.value)
                if names and self.current_class not in self.ignore_name_classes:
                    self._add_translation(self.current_class, "name", names[0])

            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == "self":
                if isinstance(target.slice, ast.Constant) and target.slice.value == "name":
                    names = get_ast_string_values(node.value)
                    if names and self.current_class not in self.ignore_name_classes:
                        self._add_translation(self.current_class, "name", names[0])

        self.generic_visit(node)

    def visit_match_case(self, node):
        self._handle_match_case(node)

    def visit_MatchCase(self, node):
        self._handle_match_case(node)

    def _handle_match_case(self, node):
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
                        names = get_ast_string_values(body_node.value)
                        if names and names[0].strip():
                            self._add_alarm(self.current_class, bit, names[0])

        self.generic_visit(node)

    def _add_translation(self, cls, key, value):
        if cls not in self.translations:
            self.translations[cls] = {}
        self.translations[cls][key] = value

    def _add_attr(self, cls, attr, value):
        if attr == "since-protocol":
            return
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

    def propagate_translations(self, data=None):
        """Propagate options, attributes, and alarm bits from base classes to child classes."""
        if data is None:
            data = self.translations

        # Simple BFS-like propagation (one level at a time to handle deep inheritance)
        changed = True
        while changed:
            changed = False
            for cls, bases in self.class_bases.items():
                if cls not in data:
                    data[cls] = {}

                for base in bases:
                    if base in data:
                        base_trans = data[base]
                        for key in ["options", "attributes", "alarm", "name"]:
                            if key in base_trans:
                                if key not in data[cls]:
                                    data[cls][key] = base_trans[key].copy() if isinstance(base_trans[key], dict) else base_trans[key]
                                    changed = True
                                elif isinstance(base_trans[key], dict) and isinstance(data[cls][key], dict):
                                    # Merge dictionaries if child doesn't have some keys
                                    for subkey, subval in base_trans[key].items():
                                        if subkey not in data[cls][key]:
                                            data[cls][key][subkey] = subval
                                            changed = True


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
                if keyword.arg == "dest":
                    vals = get_ast_string_values(keyword.value)
                    if vals:
                        dest = vals[0]
                    elif isinstance(keyword.value, ast.Attribute):
                        # Handle const.SIGENERGY2MQTT_* references
                        dest = keyword.value.attr
                elif keyword.arg == "help":
                    vals = get_ast_string_values(keyword.value)
                    if vals:
                        help_text = vals[0]

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


def propagate_to_other_translations(en_translations: dict, translations_dir: Path, class_bases: dict, old_en_translations: dict | None = None):
    """Add new keys to other language files, preserving existing translations."""
    en_class = en_translations.get("class", {})
    en_cli = en_translations.get("cli", {})
    old_en_class = old_en_translations.get("class", {}) if old_en_translations else {}
    old_en_cli = old_en_translations.get("cli", {}) if old_en_translations else {}

    for language_file in translations_dir.glob("*.yaml"):
        if language_file.name == "en.yaml":
            continue

        language_code = language_file.stem
        print(f"Updating {language_file.name}...")

        # Load existing translations
        with open(language_file, "r", encoding="utf-8") as f:
            existing = yaml_parser.load(f) or {}

        # Migration check: move any keys that exist in en_class from top-level to 'class'
        updated = False
        if "class" not in existing:
            existing["class"] = {}

        for k, v in list(existing.items()):
            if k in en_class and k != "class" and k != "cli":
                if k not in existing["class"]:
                    existing["class"][k] = v
                    updated = True
                del existing[k]
                updated = True

        if "cli" not in existing:
            existing["cli"] = {}
        elif not isinstance(existing["cli"], dict):
            # Fix case where 'cli' might have been corrupted to a string
            existing["cli"] = {}
            updated = True

        # Prune keys from other languages that are missing in English
        def prune_missing(d, ref_d):
            nonlocal updated
            if not isinstance(d, dict) or not isinstance(ref_d, dict):
                return
            for k in list(d.keys()):
                if k not in ref_d:
                    print(f"  Removing obsolete key: {k}")
                    del d[k]
                    updated = True
                else:
                    prune_missing(d[k], ref_d[k])

        prune_missing(existing, en_translations)

        # Recursive pruning of 'since-protocol' (covered by prune_missing if gone from EN, but good to keep explicit)
        def prune_obsolete(d):
            nonlocal updated
            if not isinstance(d, dict):
                return
            if "since-protocol" in d:
                del d["since-protocol"]
                updated = True
            for k, v in list(d.items()):
                prune_obsolete(v)

        prune_obsolete(existing)
        prune_empty_dicts(existing)

        # First, propagate existing translations within the language based on inheritance
        changed = True
        while changed:
            changed = False
            for cls, bases in class_bases.items():
                if cls not in existing["class"]:
                    continue

                for base in bases:
                    if base in existing["class"]:
                        base_trans = existing["class"][base]
                        for key in ["options", "attributes", "alarm", "name"]:
                            if key in base_trans:
                                if key not in existing["class"][cls]:
                                    existing["class"][cls][key] = base_trans[key].copy() if isinstance(base_trans[key], dict) else base_trans[key]
                                    changed = True
                                    updated = True
                                elif not isinstance(base_trans[key], dict) and not isinstance(existing["class"][cls][key], dict):
                                    # Handle simple string values (e.g., 'name')
                                    # Only update if existing is generic placeholder or matches English (old or new)
                                    is_placeholder = any(p in str(existing["class"][cls][key]) for p in ["{name}", "{}", "{words}"])
                                    is_english = False
                                    if cls in en_class and key in en_class[cls]:
                                        # Match new EN
                                        is_english = existing["class"][cls][key] == en_class[cls][key]
                                        # Or match OLD EN (propagation of change)
                                        if not is_english and cls in old_en_class and key in old_en_class[cls]:
                                            is_english = existing["class"][cls][key] == old_en_class[cls][key]

                                    if is_placeholder or is_english:
                                        if existing["class"][cls][key] != base_trans[key]:
                                            existing["class"][cls][key] = base_trans[key]
                                            changed = True
                                            updated = True
                                elif isinstance(base_trans[key], dict) and isinstance(existing["class"][cls][key], dict):
                                    for subkey, subval in base_trans[key].items():
                                        # Only update if missing OR if child is still in English
                                        is_missing = subkey not in existing["class"][cls][key]
                                        is_english = False
                                        if not is_missing and cls in en_class and key in en_class[cls] and isinstance(en_class[cls][key], dict) and subkey in en_class[cls][key]:
                                            # Match new EN
                                            is_english = existing["class"][cls][key][subkey] == en_class[cls][key][subkey]
                                            # Or match Old EN
                                            if not is_english and cls in old_en_class and key in old_en_class[cls] and isinstance(old_en_class[cls][key], dict) and subkey in old_en_class[cls][key]:
                                                is_english = existing["class"][cls][key][subkey] == old_en_class[cls][key][subkey]
                                        elif not is_missing:
                                            # If not matched against EN, it might still be a generic placeholder we want to update
                                            is_placeholder = any(p in str(existing["class"][cls][key][subkey]) for p in ["{name}", "{}", "{words}"])
                                            is_english = is_placeholder

                                        if is_missing or is_english:
                                            if existing["class"][cls][key].get(subkey) != subval:
                                                existing["class"][cls][key][subkey] = subval
                                                changed = True
                                                updated = True

        # Add new keys from English class translations, preserving existing translations
        for key, value in en_class.items():
            if key not in existing["class"]:
                # Add the entire new section
                if isinstance(value, dict):
                    # Check if any nested key needs translation
                    new_section = value.copy()
                    if "name_reset" in new_section and language_code in RESET_TRANSLATIONS:
                        # Translate "Set {name}"
                        # Try to find the base name from 'name' key if available, otherwise parse from English string
                        base_name = new_section.get("name", "")
                        if not base_name and new_section["name_reset"].startswith("Set "):
                            base_name = new_section["name_reset"][4:]

                        if base_name:
                            new_section["name_reset"] = RESET_TRANSLATIONS[language_code].format(name=base_name)

                    existing["class"][key] = new_section
                else:
                    existing["class"][key] = value

                updated = True
                print(f"  Added new key: {key}")
            elif isinstance(value, dict):
                # Recursively add missing sub-keys
                for subkey, subvalue in value.items():
                    if subkey not in existing["class"][key]:
                        # Handle name_reset specifically
                        if subkey == "name_reset" and language_code in RESET_TRANSLATIONS:
                            base_name = ""
                            # Try to get existing translated name first
                            if "name" in existing["class"][key]:
                                base_name = existing["class"][key]["name"]
                            elif "name" in value:
                                base_name = value["name"]  # Fallback to English name

                            if not base_name and isinstance(subvalue, str) and subvalue.startswith("Set "):
                                base_name = subvalue[4:]

                            if base_name:
                                existing["class"][key][subkey] = RESET_TRANSLATIONS[language_code].format(name=base_name)
                            else:
                                existing["class"][key][subkey] = subvalue
                        else:
                            existing["class"][key][subkey] = subvalue
                        updated = True
                        print(f"  Added new subkey: {key}.{subkey}")
                    elif isinstance(subvalue, dict):
                        for subsubkey, subsubvalue in subvalue.items():
                            if subsubkey not in existing["class"][key][subkey]:
                                existing["class"][key][subkey][subsubkey] = subsubvalue
                                updated = True
                                print(f"  Added new subsubkey: {key}.{subkey}.{subsubkey}")
                            elif existing["class"][key][subkey][subsubkey] != subsubvalue:
                                # Update if matches Old EN
                                if key in old_en_class and subkey in old_en_class[key] and isinstance(old_en_class[key][subkey], dict) and subsubkey in old_en_class[key][subkey]:
                                    if existing["class"][key][subkey][subsubkey] == old_en_class[key][subkey][subsubkey]:
                                        existing["class"][key][subkey][subsubkey] = subsubvalue
                                        updated = True

                    elif existing["class"][key][subkey] != subvalue:
                        # If existing value exists but template changed in English, update it if it's still in English/Placeholder
                        is_placeholder = any(p in str(existing["class"][key][subkey]) for p in ["{name}", "{}", "{words}"])
                        is_english = False
                        if key in old_en_class and subkey in old_en_class[key]:
                            is_english = existing["class"][key][subkey] == old_en_class[key][subkey]

                        if is_placeholder or is_english:
                            # If name_reset, re-translate
                            if subkey == "name_reset" and language_code in RESET_TRANSLATIONS:
                                base_name = existing["class"][key].get("name", "")
                                if not base_name and isinstance(subvalue, str) and subvalue.startswith("Set "):
                                    base_name = subvalue[4:]
                                if base_name:
                                    existing["class"][key][subkey] = RESET_TRANSLATIONS[language_code].format(name=base_name)
                                else:
                                    existing["class"][key][subkey] = subvalue
                            else:
                                existing["class"][key][subkey] = subvalue
                            updated = True

        # Add new keys from English CLI translations
        for key, value in en_cli.items():
            if key not in existing["cli"]:
                existing["cli"][key] = value
                updated = True
                print(f"  Added new CLI key: {key}")
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if subkey not in existing["cli"][key]:
                        existing["cli"][key][subkey] = subvalue
                        updated = True
                    elif existing["cli"][key][subkey] != subvalue:
                        is_placeholder = any(p in str(existing["cli"][key][subkey]) for p in ["{name}", "{}", "{words}"])
                        is_english = False
                        if key in old_en_cli and subkey in old_en_cli[key]:
                            is_english = existing["cli"][key][subkey] == old_en_cli[key][subkey]

                        if is_placeholder or is_english:
                            existing["cli"][key][subkey] = subvalue
                            updated = True

        if updated:
            # Sort everything before saving
            existing = sort_dict(existing)
            with open(language_file, "w", encoding="utf-8") as f:
                yaml_parser.dump(existing, f)
            print(f"  Saved {language_file.name}")
        else:
            print(f"  No changes needed for {language_file.name}")


if __name__ == "__main__":
    package_dir = Path(__file__).parent.parent / "sigenergy2mqtt"
    sensor_translations = {
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

    merge_translations(sensor_translations, extractor.translations)

    # Propagate inherited translations
    extractor.propagate_translations(data=sensor_translations)

    # Extract CLI help text
    config_cli_path = package_dir / "config" / "cli.py"
    cli_translations = extract_cli_help(config_cli_path)

    # Nest under class and cli top-level keys and sort
    all_translations = {
        "class": sort_dict(sensor_translations),
    }

    if cli_translations:
        all_translations["cli"] = sort_dict(cli_translations)
        print(f"Extracted {len(cli_translations)} CLI help texts")

    # Final sort of top-level keys
    all_translations = sort_dict(all_translations)
    prune_empty_dicts(all_translations)

    # Write en.yaml
    en_yaml_path = package_dir / "translations" / "en.yaml"
    old_all_translations = {}
    if en_yaml_path.exists():
        with open(en_yaml_path, "r", encoding="utf-8") as f:
            old_all_translations = yaml_parser.load(f) or {}

    with open(en_yaml_path, "w", encoding="utf-8") as f:
        yaml_parser.dump(all_translations, f)
    print(f"Successfully updated {en_yaml_path}")

    # Propagate to other languages
    propagate_to_other_translations(all_translations, package_dir / "translations", extractor.class_bases, old_all_translations)
    print("Done!")
