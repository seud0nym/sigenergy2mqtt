#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml


def get_flattened_values(data, prefix=""):
    items = {}
    if isinstance(data, dict):
        for k, v in data.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(get_flattened_values(v, full_key))
            elif isinstance(v, str):
                items[full_key] = v
    return items


def main():
    translations_dir = Path("sigenergy2mqtt/translations")
    en_path = translations_dir / "en.yaml"

    if not en_path.exists():
        print(f"Error: {en_path} not found.")
        sys.exit(1)

    with open(en_path, "r", encoding="utf-8") as f:
        en_data = yaml.safe_load(f)

    en_values = get_flattened_values(en_data)

    found_issues = False

    for yaml_file in sorted(translations_dir.glob("*.yaml")):
        if yaml_file.name == "en.yaml":
            continue

        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        file_values = get_flattened_values(data)

        print(f"\n--- Checking {yaml_file.name} ---")
        file_issues = []
        for key, val in file_values.items():
            if key in en_values:
                en_val = en_values[key]
                # Check for identity, ignoring short numbers/symbols that might be universal
                if val == en_val and len(val) > 1 and not val.replace(".", "", 1).isdigit():
                    # filter out obviously universal things if needed, but for now simple identity
                    file_issues.append((key, val))

        if file_issues:
            found_issues = True
            for key, val in file_issues:
                print(f"Key: {key}")
                print(f"  Value: {val}")

    if not found_issues:
        print("\nNo untranslated English values found!")


if __name__ == "__main__":
    main()
