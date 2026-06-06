#!/usr/bin/env python3
"""
translate_missing.py

Finds all untranslated (still-English) leaf values in the non-English YAML
translation files and replaces them with machine translations via the free
Google Translate web endpoint (no API key or third-party library required —
only the standard `requests` package).

Special handling:
  - Template variables {like_this} are preserved through translation.
  - source / source_range fields inherit the established "Modbus …" pattern
    already present in each file, rather than being sent to Google Translate.
  - Values with a # verify:ignore comment are skipped.
  - Technical acronyms (HVRT, LVRT, EMS, TOU, SoC …) survive translation
    reasonably well because Google Translate usually leaves them alone.

Usage:
    .venv/bin/python scripts/translate_missing.py [--dry-run] [--lang LANG …]

Options:
    --dry-run      Print what would be changed without writing files.
    --lang LANG    Limit to one or more language codes (e.g. --lang de fr).
    --verbose      Also report English keys that are missing from target files.
    --cache PATH   Path to persistent JSON translation cache
                   (default: .translation_cache.json next to this script).
    --no-cache     Disable the persistent on-disk cache entirely.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "sigenergy2mqtt" / "translations"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parent / ".translation_cache.json"

# Map YAML filename stem → Google Translate language code
LANG_CODES: dict[str, str] = {
    "de": "de",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "nl": "nl",
    "pt": "pt",
    "zh-Hans": "zh-CN",
}

# Strings considered "safe" to leave untranslated (mirrors verify_translations.py)
_SKIP_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\d+(\.\d+)?$"),
    re.compile(r"^[a-z]+://", re.IGNORECASE),
    re.compile(r"^[\w.+-]+@[\w.-]+\.\w+$"),
    re.compile(r"^<[^>]+>$"),
    re.compile(r"^(true|false|yes|no)$", re.IGNORECASE),
    re.compile(r"^(\{[^{}]+\}[\s.,:;/-]*)+$"),  # pure placeholders
]

# Placeholder regex: {word} or {word_word}
_PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")

# Google Translate free endpoint — same URL deep_translator used internally.
# No API key required; "gtx" client is the public web client identifier.
_GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"

# Base delay between API calls (seconds); actual delay uses exponential backoff
# on errors.
_API_DELAY = 0.25
_API_MAX_RETRIES = 4
_API_TIMEOUT = 15  # seconds per request

# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

# width=4096 prevents ruamel from reflowing long translation strings onto
# multiple lines, which would produce noisy diffs and hard-to-read files.
yaml = YAML(typ="rt")
yaml.preserve_quotes = True
yaml.width = 4096


def load_yaml(path: Path) -> object:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f)


def save_yaml(path: Path, data: object) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


# ---------------------------------------------------------------------------
# Persistent translation cache
# ---------------------------------------------------------------------------


class TranslationCache:
    """Two-level cache: in-process dict + optional on-disk JSON file.

    Cache keys are ``"<lang_code>:<english_text>"`` strings so the file
    remains human-readable and can be inspected / edited manually.

    The in-process layer means that strings shared across multiple language
    files are only sent to the API once per run even when the disk cache is
    disabled.
    """

    def __init__(self, path: Path | None) -> None:
        self._path = path
        # In-process cache: (lang_code, en_text) → translated_text
        self._mem: dict[tuple[str, str], str] = {}
        self._dirty = False

        if path is not None and path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                for composite_key, value in raw.items():
                    lang, _, en_text = composite_key.partition(":")
                    if lang and en_text:
                        self._mem[(lang, en_text)] = value
                print(f"  [cache] Loaded {len(self._mem)} entries from {path}.")
            except Exception as exc:
                print(f"  [cache] Could not load cache from {path}: {exc}", file=sys.stderr)

    def get(self, lang_code: str, en_text: str) -> str | None:
        return self._mem.get((lang_code, en_text))

    def set(self, lang_code: str, en_text: str, translated: str) -> None:
        self._mem[(lang_code, en_text)] = translated
        self._dirty = True

    def save(self) -> None:
        if self._path is None or not self._dirty:
            return
        serialisable = {f"{lang}:{en}": val for (lang, en), val in self._mem.items()}
        try:
            self._path.write_text(
                json.dumps(serialisable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  [cache] Saved {len(serialisable)} entries to {self._path}.")
        except Exception as exc:
            print(f"  [cache] Could not save cache to {self._path}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# verify:ignore helpers (mirrors verify_translations.py)
# ---------------------------------------------------------------------------


def _has_ignore(container: object, key: object) -> bool:
    """Return True if the YAML node carries a ``# verify:ignore`` comment."""
    try:
        if not isinstance(container, CommentedMap):
            return False
        entry = container.ca.items.get(key)
        if not entry:
            return False
        eol = entry[2]
        return eol is not None and "verify:ignore" in eol.value
    except Exception:
        return False


def _is_safe(value: str) -> bool:
    """Return True for values that should never be translated."""
    clean = value.strip()
    if len(clean) <= 1:
        return True
    return any(p.match(clean) for p in _SKIP_PATTERNS)


# ---------------------------------------------------------------------------
# Detect the established "Modbus …" format already used in a translation file
# ---------------------------------------------------------------------------


def _detect_modbus_format(data: object) -> tuple[str | None, str | None]:
    """Walk the YAML tree and find how this file renders source/source_range.

    Returns a (source_template, source_range_template) tuple where each element
    is either the first non-English translated pattern found, or None.

    English patterns we deliberately avoid returning:
        source       → "Modbus Register {address}"
        source_range → "Modbus Registers {start}-{end}"
    """
    EN_SOURCE = "Modbus Register {address}"
    EN_SOURCE_RANGE = "Modbus Registers {start}-{end}"

    source_tpl: str | None = None
    source_range_tpl: str | None = None

    def _walk(node):
        nonlocal source_tpl, source_range_tpl
        if isinstance(node, dict):
            for k, v in node.items():
                if source_tpl and source_range_tpl:
                    return
                if k == "source" and isinstance(v, str) and v != EN_SOURCE and "{address}" in v:
                    source_tpl = v
                elif k == "source_range" and isinstance(v, str) and v != EN_SOURCE_RANGE and "{start}" in v:
                    source_range_tpl = v
                else:
                    _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(data)
    return source_tpl, source_range_tpl


# ---------------------------------------------------------------------------
# Placeholder-safe translation
# ---------------------------------------------------------------------------


def _translate_string(
    text: str,
    lang_code: str,
    cache: TranslationCache,
    dry_run: bool = False,
) -> str:
    """Translate *text* while preserving {placeholder} tokens.

    Uses the free Google Translate web endpoint directly (no third-party
    library, no API key).  Checks the cache first; only calls the API on a
    miss.  In dry-run mode returns a placeholder immediately without any
    network activity.  Retries with exponential backoff on transient errors.
    """
    # --- Dry-run: no API call needed ---
    if dry_run:
        return f"<{lang_code}: {text[:40]}>"

    # --- Cache hit ---
    cached = cache.get(lang_code, text)
    if cached is not None:
        return cached

    # --- Tokenise placeholders ---
    # Use re.sub with a counter so each occurrence gets a unique token,
    # correctly handling repeated placeholders like "{name} and {name}".
    counter = [0]
    token_map: dict[str, str] = {}

    def _make_token(m: re.Match) -> str:
        token = f"XPLACEHOLDERX{counter[0]}X"
        token_map[token] = m.group(0)
        counter[0] += 1
        return token

    tokenised = _PLACEHOLDER_RE.sub(_make_token, text)

    # --- API call with exponential backoff ---
    delay = _API_DELAY
    translated: str | None = None
    for attempt in range(1, _API_MAX_RETRIES + 1):
        try:
            resp = requests.get(
                _GOOGLE_TRANSLATE_URL,
                params={"client": "gtx", "dt": "t", "sl": "en", "tl": lang_code, "q": tokenised},
                timeout=_API_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            # Response structure: [ [ [translated, original, ...], ... ], ... ]
            translated = "".join(part[0] for part in data[0] if part[0])
            time.sleep(_API_DELAY)
            break
        except Exception as exc:
            print(
                f"    [WARN] Translation error (attempt {attempt}/{_API_MAX_RETRIES}) for '{text[:60]}': {exc}",
                file=sys.stderr,
            )
            if attempt < _API_MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
            else:
                return text  # fallback to English after all retries exhausted

    if translated is None:
        return text

    # --- Restore placeholders ---
    for token, ph in token_map.items():
        translated = translated.replace(token, ph)

    cache.set(lang_code, text, translated)
    return translated


# ---------------------------------------------------------------------------
# Recursive walk to collect + apply translations
# ---------------------------------------------------------------------------


def _collect_untranslated(
    en_node: object,
    other_node: object,
    path: str,
    results: list[tuple[str, str]],
    missing: list[str],
    verbose: bool = False,
) -> None:
    """Depth-first walk; appends (dotted_path, english_value) to *results*.

    Keys present in *en_node* but absent from *other_node* are appended to
    *missing* when *verbose* is True.
    """
    if isinstance(en_node, dict) and isinstance(other_node, dict):
        for k, en_val in en_node.items():
            child_path = f"{path}.{k}" if path else str(k)
            # Resolve the counterpart key tolerating string/int mismatches
            # (e.g. English file uses quoted '0' but target file uses integer 0).
            other_k = _resolve_key(other_node, k)
            if other_k is None:
                if verbose:
                    missing.append(child_path)
                continue
            if _has_ignore(other_node, other_k) or _has_ignore(en_node, k):
                continue
            _collect_untranslated(en_val, other_node[other_k], child_path, results, missing, verbose)
    elif isinstance(en_node, list) and isinstance(other_node, list):
        for i, (en_item, other_item) in enumerate(zip(en_node, other_node)):
            _collect_untranslated(en_item, other_item, f"{path}[{i}]", results, missing, verbose)
    elif isinstance(en_node, str) and isinstance(other_node, str):
        if en_node == other_node and not _is_safe(en_node):
            results.append((path, en_node))


def _parse_path(path: str) -> list[str | int]:
    """Parse a dotted/indexed path string into a list of keys/indices.

    Examples:
        "sensors.power"       -> ["sensors", "power"]
        "items[0].label"      -> ["items", 0, "label"]
    """
    result: list[str | int] = []
    for segment in re.split(r"\[(\d+)\]|\.", path):
        if not segment:
            continue
        result.append(int(segment) if segment.isdigit() else segment)
    return result


def _resolve_key(d: dict, k: object) -> object:
    """Return the actual key present in *d* that matches logical key *k*.

    Some YAML files use quoted string keys ('0', '1' ...) while others use
    bare integer keys (0, 1 ...) for the same logical entries.  This helper
    tries *k* directly first, then falls back to the int<->str counterpart so
    that cross-file comparisons work regardless of quoting style.

    Returns the resolved key, or None if neither form is present.
    """
    if k in d:
        return k
    alt: object
    if isinstance(k, str) and k.lstrip("-").isdigit():
        alt = int(k)
    elif isinstance(k, int):
        alt = str(k)
    else:
        return None
    return alt if alt in d else None


def _set_by_path(node: object, path: str, value: str) -> bool:
    """Set a leaf value in the ruamel.yaml tree by its dotted/indexed path.

    Intermediate traversal uses _resolve_key to tolerate int/string key-type
    mismatches.  The final (leaf) write always uses the exact key form from
    the path (i.e. the English file's key), so translated values are stored
    under the same quoted/unquoted form as the source.  If the alternate-type
    key exists it is left in place for _remove_duplicate_keys to clean up.
    """
    parts = _parse_path(path)
    current = node
    for part in parts[:-1]:
        if isinstance(current, dict):
            resolved = _resolve_key(current, part)
            if resolved is None:
                return False
            current = current[resolved]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (IndexError, TypeError):
                return False
        else:
            return False

    last = parts[-1]
    try:
        if isinstance(current, dict):
            # Always write under the canonical key form from the English file.
            # _resolve_key is used only to check existence for traversal;
            # for the leaf we use `last` directly so the key type matches the
            # English source (e.g. string '0' rather than integer 0).
            current[last] = value
        elif isinstance(current, list):
            current[int(last)] = value
        else:
            return False
        return True
    except (KeyError, IndexError, TypeError):
        return False


def _get_by_path(node: object, path: str) -> object:
    """Get a value from the ruamel.yaml tree by its dotted/indexed path.

    Returns None and emits a warning if the path cannot be resolved.
    """
    parts = _parse_path(path)
    current = node
    for part in parts:
        if isinstance(current, dict):
            resolved = _resolve_key(current, part)
            if resolved is None:
                print(f"    [WARN] Could not resolve key '{part}' in path '{path}'", file=sys.stderr)
                return None
            current = current[resolved]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (IndexError, TypeError) as exc:
                print(f"    [WARN] Could not resolve path '{path}' at index '{part}': {exc}", file=sys.stderr)
                return None
        else:
            return None
    return current


def _remove_duplicate_keys(en_node: object, other_node: object) -> int:
    """Remove integer-keyed duplicates from *other_node* where the English
    file uses quoted string keys (e.g. '0', '1') as the canonical form.

    After translation, both a string key and an integer key for the same
    logical entry can coexist in the target file.  We always want the string
    key form (matching the English source) to be the surviving entry.  This
    pass removes any integer key whose string counterpart is also present and
    holds the same value, and any string key whose integer counterpart holds
    the translation while this key still holds the original English.

    Returns the number of keys removed.
    """
    removed = 0
    if isinstance(en_node, dict) and isinstance(other_node, dict):
        stale: list = []
        for k, v in list(other_node.items()):
            if not isinstance(v, str):
                # Recurse into nested dicts/lists; resolve child in en_node
                # by either key form.
                en_child = en_node.get(k) if isinstance(en_node, dict) else None
                if en_child is None and isinstance(en_node, dict):
                    alt = int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else (str(k) if isinstance(k, int) else None)
                    if alt is not None:
                        en_child = en_node.get(alt)
                if en_child is not None:
                    removed += _remove_duplicate_keys(en_child, v)
                continue

            # Compute the int<->str alternate key form.
            if isinstance(k, str) and k.lstrip("-").isdigit():
                alt = int(k)
            elif isinstance(k, int):
                alt = str(k)
            else:
                continue

            if alt not in other_node:
                continue

            alt_val = other_node[alt]
            if not isinstance(alt_val, str):
                continue

            en_val = en_node.get(k) if isinstance(en_node, dict) else None
            if en_val is None:
                en_val = en_node.get(alt) if isinstance(en_node, dict) else None

            # Case 1: this key is an integer and its string counterpart exists
            # with the same value → the string form is canonical; drop the int.
            # Only ever remove integer keys; string keys are always canonical
            # (they match the quoted form used in the English source file).
            if not isinstance(k, int):
                continue
            # Case 1: both int and string keys hold the same translated value
            # → string key is the keeper, drop the int.
            if v == alt_val:
                stale.append(k)
            # Case 2: int key holds a translation, string key still holds
            # English → drop the int so the next run writes the translation
            # under the string key.
            elif alt_val == en_val and v != en_val:
                stale.append(k)

        for k in stale:
            del other_node[k]
            removed += 1
    elif isinstance(en_node, list) and isinstance(other_node, list):
        for en_item, other_item in zip(en_node, other_node):
            removed += _remove_duplicate_keys(en_item, other_item)
    return removed


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


def process_language(
    lang_stem: str,
    lang_code: str,
    en_data: object,
    dry_run: bool,
    cache: TranslationCache,
    verbose: bool = False,
) -> tuple[int, int]:
    """Translate all untranslated strings in one language file.

    Returns (translated_count, skipped_count).
    """
    yaml_path = TRANSLATIONS_DIR / f"{lang_stem}.yaml"
    print(f"\n=== {yaml_path.name} ({lang_code}) ===")

    other_data = load_yaml(yaml_path)

    # Detect existing source/source_range format for this language
    source_tpl, source_range_tpl = _detect_modbus_format(other_data)
    print(f"  Detected source template:       {source_tpl!r}")
    print(f"  Detected source_range template: {source_range_tpl!r}")

    # Collect all untranslated values
    untranslated: list[tuple[str, str]] = []
    missing: list[str] = []
    _collect_untranslated(en_data, other_data, "", untranslated, missing, verbose)

    if verbose and missing:
        print(f"  {len(missing)} key(s) missing from this file:")
        for m in missing:
            print(f"    [MISSING] {m}")

    # Remove stale integer keys regardless of whether there is anything left
    # to translate — they may have been left behind by a previous run.
    dupes = _remove_duplicate_keys(en_data, other_data)
    if dupes:
        if dry_run:
            print(f"  [DRY] Would remove {dupes} stale duplicate key(s).")
        else:
            print(f"  Removed {dupes} stale duplicate key(s).")
            save_yaml(yaml_path, other_data)
            print(f"  Saved {yaml_path.name} ({dupes} duplicates removed).")

    if not untranslated:
        if not dupes:
            print("  Nothing to translate.")
        return 0, 0

    # --- Within-language deduplication ---
    # Build the set of unique English strings that need actual translation
    # (exclude source/source_range entries that use the template shortcut).
    def _needs_api(path: str, en_val: str) -> bool:
        last_key = _parse_path(path)[-1]
        if last_key == "source" and source_tpl is not None:
            return False
        if last_key == "source_range" and source_range_tpl is not None:
            return False
        return True

    unique_en = {en_val for path, en_val in untranslated if _needs_api(path, en_val)}
    print(f"  Found {len(untranslated)} untranslated value(s) ({len(unique_en)} unique string(s) to translate).")

    # Pre-translate all unique strings so each is sent to the API at most once
    # per language (cache hits are free regardless).  Dry-run skips all API
    # calls and prints a progress counter only for real runs.
    translation_lookup: dict[str, str] = {}
    total = len(unique_en)
    for i, en_val in enumerate(unique_en, 1):
        if not dry_run:
            print(f"  Translating {i}/{total} ...", end="\r", flush=True)
        translation_lookup[en_val] = _translate_string(en_val, lang_code, cache, dry_run)

    if not dry_run:
        print()  # clear the \r progress line

    translated = 0
    skipped = 0

    for path, en_val in untranslated:
        last_key = _parse_path(path)[-1]

        # ---- source / source_range: use existing template ----
        if last_key == "source" and source_tpl is not None:
            new_val = source_tpl
        elif last_key == "source_range" and source_range_tpl is not None:
            new_val = source_range_tpl
        else:
            new_val = translation_lookup[en_val]
            if new_val == en_val:
                skipped += 1
                print(f"  [SKIP] {path}: '{en_val[:60]}'")
                continue

        if dry_run:
            print(f"  [DRY] {path}:")
            print(f"        EN:  {en_val[:80]!r}")
            print(f"        {lang_code.upper()}: {new_val[:80]!r}")
        else:
            if _set_by_path(other_data, path, new_val):
                print(f"  [OK]  {path}: {new_val[:60]!r}")
                translated += 1
            else:
                print(f"  [ERR] Could not set path: {path}", file=sys.stderr)
                skipped += 1

    if not dry_run and translated > 0:
        save_yaml(yaml_path, other_data)
        print(f"  Saved {yaml_path.name} ({translated} updates).")

    return translated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate missing values in non-English YAML translation files.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files.")
    parser.add_argument(
        "--lang",
        nargs="+",
        metavar="LANG",
        help="Limit to specific language code(s), e.g. --lang de fr.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also report English keys that are missing from target files.",
    )
    parser.add_argument(
        "--cache",
        metavar="PATH",
        default=str(DEFAULT_CACHE_PATH),
        help=f"Path to persistent JSON translation cache (default: {DEFAULT_CACHE_PATH}).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the persistent on-disk cache.",
    )
    args = parser.parse_args()

    en_path = TRANSLATIONS_DIR / "en.yaml"
    if not en_path.exists():
        print(f"ERROR: {en_path} not found.", file=sys.stderr)
        sys.exit(1)

    en_data = load_yaml(en_path)

    target_langs = {k: v for k, v in LANG_CODES.items() if not args.lang or k in args.lang}
    if not target_langs:
        print("ERROR: No matching languages found.", file=sys.stderr)
        sys.exit(1)

    cache_path = None if args.no_cache else Path(args.cache)
    cache = TranslationCache(cache_path)

    grand_translated = 0
    grand_skipped = 0

    for stem, code in target_langs.items():
        yaml_path = TRANSLATIONS_DIR / f"{stem}.yaml"
        if not yaml_path.exists():
            print(f"WARNING: {yaml_path} not found – skipping.", file=sys.stderr)
            continue
        t, s = process_language(stem, code, en_data, args.dry_run, cache, args.verbose)
        grand_translated += t
        grand_skipped += s

    cache.save()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done: {grand_translated} translated, {grand_skipped} skipped.")


if __name__ == "__main__":
    main()
