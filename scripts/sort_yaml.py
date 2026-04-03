#!/usr/bin/env python3
"""Sort a YAML file's keys alphabetically using ruamel.yaml (preserves comments and formatting)."""

import argparse
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


def sort_key(key):
    """Sort numeric string keys (e.g. '0', '10') numerically; all others alphabetically.

    Numeric keys are sorted before non-numeric ones within the same mapping so
    that mixed maps produce a stable, predictable order.
    """
    try:
        return (0, int(str(key)), "")
    except (ValueError, TypeError):
        pass
    try:
        return (0, float(str(key)), "")
    except (ValueError, TypeError):
        pass
    return (1, 0, str(key).lower())


def sort_commented_map(obj):
    """Recursively sort CommentedMap keys, preserving inline/block comments."""
    if isinstance(obj, CommentedMap):
        sorted_map = CommentedMap()

        for key in sorted(obj.keys(), key=sort_key):
            sorted_map[key] = sort_commented_map(obj[key])
            # Copy per-key comment attributes (inline comments, pre-key comments, etc.)
            if key in obj.ca.items:
                sorted_map.ca.items[key] = obj.ca.items[key]

        # Copy the mapping-level comment (e.g. a comment before the first key)
        if obj.ca.comment is not None:
            sorted_map.ca.comment = obj.ca.comment

        return sorted_map
    elif isinstance(obj, list):
        return [sort_commented_map(item) for item in obj]
    return obj


def sort_yaml_file(input_path: Path, output_path: Path):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 2**31 - 1  # Prevent line wrapping
    yaml.indent(mapping=2, sequence=4, offset=2)

    with open(input_path, "r") as f:
        data = yaml.load(f)

    sorted_data = sort_commented_map(data)

    with open(output_path, "w") as f:
        yaml.dump(sorted_data, f)

    print(f"Sorted '{input_path}' -> '{output_path}'")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sort YAML file keys alphabetically, preserving comments and formatting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Sort in-place (overwrite input file)
  python sort_yaml.py config.yaml

  # Sort to a new file
  python sort_yaml.py config.yaml --output config_sorted.yaml

  # Sort to a different directory
  python sort_yaml.py config.yaml --output ./sorted/config.yaml
        """,
    )
    parser.add_argument("input", type=Path, help="Path to the input YAML file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Path to the output YAML file (default: overwrite input file)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.input.exists():
        print(f"Error: input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.input.suffix.lower() not in (".yaml", ".yml"):
        print(f"Warning: '{args.input}' does not have a .yaml/.yml extension.")

    output_path = args.output or args.input

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sort_yaml_file(args.input, output_path)


if __name__ == "__main__":
    main()
