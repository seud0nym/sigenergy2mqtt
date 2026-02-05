#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from ruamel.yaml import YAML

yaml_loader = YAML(typ="rt")


def load_yaml(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml_loader.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None


def find_missing_keys(en_data, other_data, path=""):
    """
    Recursively find keys present in en_data but missing in other_data.
    """
    issues = []
    if isinstance(en_data, dict):
        if not isinstance(other_data, dict):
            # Type mismatch means the structure is wrong/missing at this level
            return [f"Type mismatch at {path}: expected dict, got {type(other_data).__name__}"]

        for k, v in en_data.items():
            full_key = f"{path}.{k}" if path else k
            if k not in other_data:
                issues.append(f"Missing key: {full_key}")
            else:
                issues.extend(find_missing_keys(v, other_data[k], full_key))
    elif isinstance(en_data, list):
        if not isinstance(other_data, list):
            return [f"Type mismatch at {path}: expected list, got {type(other_data).__name__}"]

        # For lists, we can't easily match items by key, but we can verify length or structure if needed.
        # For translation files, strict index matching is usually assumed.
        for i, item in enumerate(en_data):
            full_key = f"{path}[{i}]"
            if i >= len(other_data):
                issues.append(f"Missing list item: {full_key}")
            else:
                issues.extend(find_missing_keys(item, other_data[i], full_key))

    return issues


def has_ignore_comment(container, key):
    try:
        # Check if the container supports comments
        if not hasattr(container, "ca"):
            return False

        # ca.items is a dict mapping key/index to comment structures
        # The structure is typically [start_token, [comment_token], end_token]
        # We are looking for the comment token
        comments = container.ca.items.get(key)
        if comments:
            # comments[2] is usually the inline comment token
            # It might be None or a wrapper, we need to be careful
            for item in comments:
                if hasattr(item, "value") and item.value and "verify:ignore" in item.value:
                    return True
                if isinstance(item, list):
                    for subitem in item:
                        if hasattr(subitem, "value") and subitem.value and "verify:ignore" in subitem.value:
                            return True
    except Exception:
        # If accessing implementation details fails, assume no ignore
        pass
    return False


def find_untranslated_values(en_data, other_data, path=""):
    """
    Recursively find leaf values that are identical in both files.
    """
    issues = []
    if isinstance(en_data, dict) and isinstance(other_data, dict):
        for k, v in en_data.items():
            # Skip keys missing in other_data (handled by find_missing_keys)
            if k in other_data:
                # Check for ignore comment on this key in either file
                if has_ignore_comment(other_data, k) or has_ignore_comment(en_data, k):
                    continue
                issues.extend(find_untranslated_values(v, other_data[k], f"{path}.{k}" if path else k))
    elif isinstance(en_data, list) and isinstance(other_data, list):
        for i, (v1, v2) in enumerate(zip(en_data, other_data)):
            # Check for ignore comment on this list item in either file
            if has_ignore_comment(other_data, i) or has_ignore_comment(en_data, i):
                continue
            issues.extend(find_untranslated_values(v1, v2, f"{path}[{i}]"))
    else:
        # Comparison logic for leaf values
        # We ignore non-string types as they might be configuration values (booleans, numbers)
        if isinstance(en_data, str) and isinstance(other_data, str):
            # Ignore very short strings or strings that look like technical identifiers/numbers
            clean_val = en_data.strip()
            if en_data == other_data and len(clean_val) > 1:
                # Heuristic: if it's just a number or symbol, ignore it
                if not clean_val.replace(".", "", 1).isdigit():
                    issues.append(f"Untranslated value at {path}: '{en_data}'")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Verify translation files against en.yaml")
    parser.add_argument("--check-keys", action="store_true", default=True, help="Check for missing keys (default: True)")
    parser.add_argument("--check-values", action="store_true", default=True, help="Check for untranslated values (default: True)")
    parser.add_argument("--no-check-keys", action="store_false", dest="check_keys", help="Disable check for missing keys")
    parser.add_argument("--no-check-values", action="store_false", dest="check_values", help="Disable check for untranslated values")
    args = parser.parse_args()

    # Determine project root relative to this script
    script_dir = Path(__file__).parent.resolve()
    # Assuming script is in /scripts/, go up one level then to sigenergy2mqtt/translations
    project_root = script_dir.parent
    translations_dir = project_root / "sigenergy2mqtt" / "translations"

    en_path = translations_dir / "en.yaml"
    if not en_path.exists():
        print(f"Error: {en_path} not found.")
        sys.exit(1)

    print(f"Loading base language file: {en_path}")
    en_data = load_yaml(en_path)
    if en_data is None:
        sys.exit(1)

    found_issues = False

    for yaml_file in sorted(translations_dir.glob("*.yaml")):
        if yaml_file.name == "en.yaml":
            continue

        print(f"\n--- Verifying {yaml_file.name} ---")
        other_data = load_yaml(yaml_file)
        if other_data is None:
            continue

        file_issues = []

        if args.check_keys:
            file_issues.extend(find_missing_keys(en_data, other_data))

        if args.check_values:
            file_issues.extend(find_untranslated_values(en_data, other_data))

        if file_issues:
            found_issues = True
            for issue in file_issues:
                print(issue)
        else:
            print("OK")

    if found_issues:
        sys.exit(1)
    else:
        print("\nAll checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
