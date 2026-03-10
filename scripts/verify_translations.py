#!/usr/bin/env python3
"""
verify_translations.py

Verifies that non-English YAML translation files are consistent with the
canonical English base file (en.yaml). Two checks are performed:

  - Missing keys: keys present in en.yaml that are absent in the target file.
  - Untranslated values: leaf strings whose value is identical in both files,
    indicating the translation was never filled in.

Individual keys or list items can be exempted from the untranslated-value
check by adding a ``# verify:ignore`` inline comment in either file.

Exit code is always 0; issue counts are printed in the final summary.
"""

import argparse
import itertools
import logging
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML

yaml_loader = YAML(typ="rt")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns for strings that are safe to leave untranslated
# ---------------------------------------------------------------------------
_SKIP_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\d+(\.\d+)?$"),  # pure numbers / decimals
    re.compile(r"^[a-z]+://", re.IGNORECASE),  # URLs (http://, mailto:// …)
    re.compile(r"^[\w.+-]+@[\w.-]+\.\w+$"),  # email addresses
    re.compile(r"^<[^>]+>$"),  # bare HTML tags
    re.compile(r"^(true|false|yes|no)$", re.IGNORECASE),  # boolean-like literals
]


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class TranslationLoadError(Exception):
    """Raised when a YAML translation file cannot be read or parsed."""


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def load_yaml(path: Path) -> object:
    """Load and return the contents of a YAML file.

    Args:
        path: Filesystem path to the YAML file.

    Returns:
        The parsed YAML data structure (typically a CommentedMap).

    Raises:
        TranslationLoadError: If the file cannot be opened or parsed.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml_loader.load(f)
    except Exception as e:
        raise TranslationLoadError(f"Error loading {path}: {e}") from e


def has_ignore_comment(container: object, key: object) -> bool:
    """Return True if a ``# verify:ignore`` inline comment is attached to *key*.

    ruamel.yaml stores per-key comment tokens in ``container.ca.items[key]``,
    a 4-element list with the following slots:

    * 0 – comment before the key
    * 1 – comment between key and value (after the colon)
    * 2 – end-of-line (inline) comment   ← the only realistic slot for ``# verify:ignore``
    * 3 – comment after the value

    Only slot 2 is inspected to avoid false matches from adjacent-key comments
    that ruamel.yaml may store in the neighbouring slots.

    Args:
        container: A ruamel.yaml CommentedMap or CommentedSeq.
        key: The mapping key (str) or sequence index (int) to inspect.

    Returns:
        True if a ``verify:ignore`` comment is found on slot 2, False otherwise.
    """
    try:
        if not hasattr(container, "ca"):
            return False
        comment_entry = getattr(container, "ca").items.get(key)
        if not comment_entry:
            return False
        eol_comment = comment_entry[2]  # inline / end-of-line slot only
        if eol_comment is None:
            return False
        return "verify:ignore" in eol_comment.value
    except Exception:
        logger.debug(
            "Unexpected error inspecting comment for key %r in %r; assuming no ignore.",
            key,
            container,
            exc_info=True,
        )
        return False


# ---------------------------------------------------------------------------
# Translation-safe heuristic
# ---------------------------------------------------------------------------


def _is_translation_safe(value: str) -> bool:
    """Return True if *value* is a string that may legitimately be left untranslated.

    Strings considered safe include: single characters, pure numbers, URLs,
    email addresses, bare HTML tags, and boolean-like literals. This replaces
    the original ``isdigit()`` heuristic with an explicit pattern allowlist so
    that technical strings (e.g. ``"$"``, ``"http://example.com"``) are not
    falsely flagged.

    Args:
        value: The English source string to evaluate.

    Returns:
        True if the string should be exempt from untranslated-value warnings.
    """
    clean = value.strip()
    if len(clean) <= 1:
        return True
    return any(pattern.match(clean) for pattern in _SKIP_PATTERNS)


# ---------------------------------------------------------------------------
# Core recursive checker (single-pass, combines key and value checks)
# ---------------------------------------------------------------------------


def find_issues(
    en_data: object,
    other_data: object,
    check_keys: bool,
    check_values: bool,
    path: str = "",
) -> list[str]:
    """Recursively find translation issues between *en_data* and *other_data*.

    Combines the missing-key check and the untranslated-value check in a single
    depth-first walk, avoiding the double traversal of the original design.

    For a given key, a ``# verify:ignore`` comment suppresses only the
    untranslated-value check for that subtree; missing-key checks within the
    same subtree are still reported.

    Args:
        en_data: Data from the English base file (or a sub-tree thereof).
        other_data: Data from the target translation file (or a sub-tree thereof).
        check_keys: Whether to report missing keys / list items.
        check_values: Whether to report untranslated (identical) string values.
        path: Dot-separated key path used in error messages (populated during recursion).

    Returns:
        A list of human-readable issue strings. Empty list means no issues found.
    """
    issues: list[str] = []

    # ---- mapping nodes ----
    if isinstance(en_data, dict):
        if not isinstance(other_data, dict):
            if check_keys:
                issues.append(f"Type mismatch at '{path}': expected dict, got {type(other_data).__name__}")
            return issues

        for k, en_val in en_data.items():
            full_key = f"{path}.{k}" if path else k
            if k not in other_data:
                if check_keys:
                    issues.append(f"Missing key: {full_key}")
            else:
                # A verify:ignore comment suppresses value checking for this subtree
                # but key checking continues so deeply nested missing keys are still caught.
                ignored = check_values and (has_ignore_comment(other_data, k) or has_ignore_comment(en_data, k))
                issues.extend(find_issues(en_val, other_data[k], check_keys, check_values and not ignored, full_key))

    # ---- sequence nodes ----
    elif isinstance(en_data, list):
        if not isinstance(other_data, list):
            if check_keys:
                issues.append(f"Type mismatch at '{path}': expected list, got {type(other_data).__name__}")
            return issues

        # zip_longest so that items present in en but absent in other are never silently skipped
        for i, (en_item, other_item) in enumerate(itertools.zip_longest(en_data, other_data, fillvalue=None)):
            full_key = f"{path}[{i}]"
            if other_item is None:
                if check_keys:
                    issues.append(f"Missing list item: {full_key}")
            elif en_item is None:
                # Extra items in the translation file are not an error
                pass
            else:
                ignored = check_values and (has_ignore_comment(other_data, i) or has_ignore_comment(en_data, i))
                issues.extend(find_issues(en_item, other_item, check_keys, check_values and not ignored, full_key))

    # ---- leaf nodes ----
    else:
        if check_values and isinstance(en_data, str) and isinstance(other_data, str):
            if en_data == other_data and not _is_translation_safe(en_data):
                issues.append(f"Untranslated value at '{path}': '{en_data}'")

    return issues


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _default_translations_dir() -> Path:
    """Return the default translations directory inferred from this script's location.

    Assumes the script lives in ``<project_root>/scripts/`` and translations
    are at ``<project_root>/sigenergy2mqtt/translations/``.

    Returns:
        The default Path to the translations directory.
    """
    return Path(__file__).parent.resolve().parent / "sigenergy2mqtt" / "translations"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments, run all translation checks, and print a summary.

    Iterates over every ``*.yaml`` file in the translations directory (except
    ``en.yaml`` itself), runs :func:`find_issues` against the English base
    file, and prints per-file results followed by an aggregate summary.

    Always exits with code 0 so CI pipelines can inspect the summary output
    rather than relying solely on the exit code.
    """
    parser = argparse.ArgumentParser(description="Verify translation YAML files against the English base file (en.yaml).")
    parser.add_argument(
        "--check-keys",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Check for missing keys (default: enabled). Use --no-check-keys to disable.",
    )
    parser.add_argument(
        "--check-values",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Check for untranslated values (default: enabled). Use --no-check-values to disable.",
    )
    parser.add_argument(
        "--translations-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=("Path to the translations directory containing en.yaml and peer files. Defaults to <project_root>/sigenergy2mqtt/translations/ relative to this script."),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging (useful for diagnosing comment-detection issues).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    translations_dir: Path = args.translations_dir or _default_translations_dir()

    en_path = translations_dir / "en.yaml"
    if not en_path.exists():
        print(f"Error: base file not found: {en_path}")
        sys.exit(1)

    print(f"Loading base language file: {en_path}")
    try:
        en_data = load_yaml(en_path)
    except TranslationLoadError as exc:
        print(exc)
        sys.exit(1)

    total_issues = 0
    files_with_issues = 0
    files_checked = 0

    for yaml_file in sorted(translations_dir.glob("*.yaml")):
        if yaml_file.name == "en.yaml":
            continue

        print(f"\n--- Verifying {yaml_file.name} ---")
        try:
            other_data = load_yaml(yaml_file)
        except TranslationLoadError as exc:
            print(exc)
            continue

        files_checked += 1
        file_issues = find_issues(en_data, other_data, args.check_keys, args.check_values)

        if file_issues:
            files_with_issues += 1
            total_issues += len(file_issues)
            for issue in file_issues:
                print(issue)
        else:
            print("OK")

    # ---- Summary ----
    print(f"\n{'=' * 48}")
    if total_issues:
        print(f"Found {total_issues} issue(s) across {files_with_issues} of {files_checked} file(s) checked.")
        sys.exit(1)
    else:
        print(f"All {files_checked} file(s) passed with no issues.")
        sys.exit(0)


if __name__ == "__main__":
    main()
