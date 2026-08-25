"""
translate_missing.py

Finds all untranslated (still-English) leaf values in the non-English YAML
translation files and replaces them with machine translations via the
official DeepL API (requires a DeepL API key, set via --api-key or the
DEEPL_AUTH_KEY environment variable).

Optimised for a metered DeepL subscription:
  - Persistent on-disk cache means every string is only ever billed once,
    across every run, forever (unless you edit/clear the cache).
  - A pre-flight pass counts exactly how many *new* characters this run
    would bill before any API call is made, and checks it against your
    account's remaining quota (via GET /usage) plus an optional
    --max-chars session cap. Nothing is sent unless it fits.
  - Requests are batched (default 50 strings/call) instead of one string
    per call, cutting HTTP round-trips dramatically without changing the
    character cost.
  - A fixed --context hint is sent with every batch. DeepL's `context`
    parameter improves quality for short, ambiguous UI strings and is
    *not* billed — free quality, not free characters, but it doesn't
    cost you anything either.
  - Placeholders are protected via DeepL's own `ignore_tags` XML
    mechanism (the officially supported way to mark spans as
    do-not-translate) rather than a token round-trip.

Special handling (unchanged from the previous Google-Translate version):
  - Template variables {like_this} are preserved through translation.
  - source / source_range fields inherit the established "Modbus …" pattern
    already present in each file, rather than being sent to the API.
  - Values with a # verify:ignore comment are skipped.
  - Technical acronyms (HVRT, LVRT, EMS, TOU, SoC …) are wrapped the same
    way as placeholders would be if they collide with the regex, but
    otherwise are just sent as normal text — DeepL generally leaves
    unrecognised acronyms alone.

Usage:
    .venv/bin/python scripts/translate_missing.py [--dry-run] [--lang LANG …]

Options:
    --dry-run        Print what would be changed without writing files or
                      calling the API.
    --lang LANG      Limit to one or more language codes (e.g. --lang de fr).
    --verbose        Also report English keys that are missing from target files.
    --cache PATH     Path to persistent JSON translation cache
                     (default: .translation_cache.json next to this script).
    --no-cache       Disable the persistent on-disk cache entirely (NOT
                     recommended — every string will be re-billed every run).
    --api-key KEY    DeepL API key. Falls back to the DEEPL_AUTH_KEY
                     environment variable.
    --formality PREF Formality for languages that support it: default,
                     more, less, prefer_more, prefer_less. (default: default)
    --max-chars N    Hard cap on new characters billed this run, on top of
                     whatever your DeepL account quota allows. Useful as a
                     safety net even on an unlimited Pro plan.
    --force          Proceed even if the pre-flight estimate exceeds the
                     account's remaining quota or --max-chars (DeepL will
                     simply reject the call once the account limit is hit).
    --batch-size N   Strings per DeepL API call (default: 50).
"""

import argparse
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import deepl
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS_DIR = PROJECT_ROOT / "sigenergy2mqtt" / "translations"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parent / ".translation_cache.json"

# Map YAML filename stem -> DeepL target language code.
# See https://developers.deepl.com/docs/getting-started/supported-languages
# "pt" defaults to European Portuguese (PT-PT); change to "PT-BR" if the
# project's Portuguese file is meant to be Brazilian.
LANG_CODES: dict[str, str] = {
    "de": "DE",
    "es": "ES",
    "fr": "FR",
    "it": "IT",
    "ja": "JA",
    "ko": "KO",
    "nl": "NL",
    "pt": "PT-PT",
    "zh-Hans": "ZH",
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

# Context hint sent with every DeepL request. This is NOT billed against
# the character quota -- it only steers translation quality for short,
# otherwise-ambiguous strings (e.g. "Power" as a noun vs. verb).
_CONTEXT_HINT = "Home Assistant integration for Sigenergy solar inverter and battery systems. Technical UI labels, sensor names, and configuration descriptions."

# DeepL batching / retry configuration
_DEFAULT_BATCH_SIZE = 50
_API_MAX_RETRIES = 4
_API_RETRY_BASE_DELAY = 2.0  # seconds; doubles each retry

# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

# width=4096 prevents ruamel from re-flowing long translation strings onto
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

    Every cache hit is a string that never gets billed to the DeepL
    subscription again, so this cache is the single biggest lever for
    keeping monthly character usage down across repeated runs.
    """

    def __init__(self, path: Path | None) -> None:
        self._path = path
        # In-process cache: (lang_code, en_text) -> translated_text
        self._mem: dict[tuple[str, str], str] = {}
        self._dirty = False

        if path is not None and path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for composite_key, value in raw.items():
                        lang, _, en_text = composite_key.partition(":")
                        if lang and en_text:
                            self._mem[(lang, en_text)] = value
                    print(f"  [cache] Loaded {len(self._mem)} entries from {path}.")
                else:
                    print(f"  [cache] Could not load cache from {path}: Expected JSON object/dict.", file=sys.stderr)
            except (OSError, json.JSONDecodeError) as exc:
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
        except (OSError, TypeError, ValueError) as exc:
            print(f"  [cache] Could not save cache to {self._path}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# verify:ignore helpers (mirrors verify_translations.py)
# ---------------------------------------------------------------------------


def _has_ignore(container: object, key: object) -> bool:
    """Return True if the YAML node carries a ``# verify:ignore`` comment."""
    if not isinstance(container, CommentedMap):
        return False

    entry = container.ca.items.get(key)
    if entry and len(entry) > 2:
        eol = entry[2]
        if eol and hasattr(eol, "value") and eol.value:
            return "verify:ignore" in eol.value

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
        source       -> "Modbus Register {address}"
        source_range -> "Modbus Registers {start}-{end}"
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
# Placeholder-safe translation via DeepL
# ---------------------------------------------------------------------------


def _protect(text: str) -> str:
    """Wrap {placeholder} tokens in <x>...</x> so DeepL's ignore_tags leaves
    them untouched, after escaping any pre-existing XML-special characters
    so tag_handling="xml" doesn't choke on stray < > & in source strings."""
    escaped = html.escape(text, quote=False)
    return _PLACEHOLDER_RE.sub(lambda m: f"<x>{m.group(0)}</x>", escaped)


def _unprotect(text: str) -> str:
    """Reverse _protect(): strip the <x> wrapper tags and unescape."""
    text = re.sub(r"</?x>", "", text)
    return html.unescape(text)


def _translate_batch(
    texts: list[str],
    lang_code: str,
    translator: "deepl.Translator | None",
    formality: str,
    dry_run: bool = False,
) -> list[str]:
    """Translate a batch of strings in a single DeepL API call.

    Returns a list of translations in the same order as *texts*. Falls back
    to the original English text for any entry on unrecoverable failure so a
    single bad batch never crashes the whole run.
    """
    if dry_run:
        return [f"<{lang_code}: {t[:40]}>" for t in texts]

    # main() guarantees a real Translator whenever dry_run is False (it exits
    # earlier if --api-key/DEEPL_AUTH_KEY is missing). This assert just makes
    # that guarantee explicit for the type checker.
    assert translator is not None, "translator must be set when dry_run is False"

    protected = [_protect(t) for t in texts]

    delay = _API_RETRY_BASE_DELAY
    for attempt in range(1, _API_MAX_RETRIES + 1):
        try:
            results = translator.translate_text(
                protected,
                source_lang="EN",
                target_lang=lang_code,
                tag_handling="xml",
                ignore_tags=["x"],
                context=_CONTEXT_HINT,
                formality=formality if formality != "default" else None,
                preserve_formatting=True,
            )
            # translate_text returns a single TextResult for a single string
            # input, or a List[TextResult] for a list input. We always pass
            # a list, so this branch is the one that actually runs; the
            # isinstance check just narrows the type honestly rather than
            # assuming the list case.
            if isinstance(results, list):
                return [_unprotect(r.text) for r in results]
            return [_unprotect(results.text)]
        except deepl.QuotaExceededException:
            # No point retrying -- the account is out of characters.
            raise
        except deepl.TooManyRequestsException as exc:
            print(f"    [WARN] Rate limited (attempt {attempt}/{_API_MAX_RETRIES}): {exc}", file=sys.stderr)
        except (deepl.ConnectionException, deepl.DeepLException) as exc:
            print(f"    [WARN] Translation error (attempt {attempt}/{_API_MAX_RETRIES}): {exc}", file=sys.stderr)

        if attempt < _API_MAX_RETRIES:
            time.sleep(delay)
            delay *= 2
        else:
            print(f"    [ERR] Giving up on this batch of {len(texts)} string(s) after {_API_MAX_RETRIES} attempts; leaving as English.", file=sys.stderr)
            return list(texts)  # fall back to English for the whole batch

    return list(texts)  # unreachable, keeps type-checkers happy


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
    elif isinstance(en_node, str) and isinstance(other_node, str) and en_node == other_node and not _is_safe(en_node):
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
    bare integer keys (0, 1 ...) for the same logical entries. This helper
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
    mismatches. The final (leaf) write always uses the exact key form from
    the path (i.e. the English file's key), so translated values are stored
    under the same quoted/unquoted form as the source. If the alternate-type
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
            resolved_last = _resolve_key(current, last)
            write_key = resolved_last if resolved_last is not None else last
            current[write_key] = value
        elif isinstance(current, list):
            current[int(last)] = value
        else:
            return False
        return True
    except (KeyError, IndexError, TypeError):
        return False


def _remove_duplicate_keys(en_node: object, other_node: object) -> int:
    """Remove integer-keyed duplicates from *other_node* where the English
    file uses quoted string keys (e.g. '0', '1') as the canonical form.

    After translation, both a string key and an integer key for the same
    logical entry can coexist in the target file. We always want the string
    key form (matching the English source) to be the surviving entry. This
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
                en_child = en_node.get(k) if isinstance(en_node, dict) else None
                if en_child is None and isinstance(en_node, dict):
                    alt = int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else (str(k) if isinstance(k, int) else None)
                    if alt is not None:
                        en_child = en_node.get(alt)
                if en_child is not None:
                    removed += _remove_duplicate_keys(en_child, v)
                continue

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

            if v == alt_val or alt_val == en_val and v != en_val:
                stale.append(k)

        for k in stale:
            del other_node[k]
            removed += 1
    elif isinstance(en_node, list) and isinstance(other_node, list):
        for en_item, other_item in zip(en_node, other_node):
            removed += _remove_duplicate_keys(en_item, other_item)
    return removed


# ---------------------------------------------------------------------------
# Canonical English Modbus patterns that the template shortcut applies to.
# ---------------------------------------------------------------------------

_EN_SOURCE = "Modbus Register {address}"
_EN_SOURCE_RANGE = "Modbus Registers {start}-{end}"


def _needs_api(path: str, en_val: str, source_tpl: str | None, source_range_tpl: str | None) -> bool:
    last_key = _parse_path(path)[-1]
    is_source = last_key == "source" and source_tpl is not None and en_val == _EN_SOURCE
    is_source_range = last_key == "source_range" and source_range_tpl is not None and en_val == _EN_SOURCE_RANGE
    return not (is_source or is_source_range)


# ---------------------------------------------------------------------------
# Per-language gather phase (no API calls -- just figures out what's needed)
# ---------------------------------------------------------------------------


class LanguageJob:
    """Everything gathered for one language before any billing happens."""

    def __init__(self, stem: str, lang_code: str):
        self.stem = stem
        self.lang_code = lang_code
        self.yaml_path = TRANSLATIONS_DIR / f"{stem}.yaml"
        self.other_data: object = None
        self.source_tpl: str | None = None
        self.source_range_tpl: str | None = None
        self.untranslated: list[tuple[str, str]] = []
        self.missing: list[str] = []
        self.dupes_removed = 0
        # Unique English strings that still need an actual API call
        # (cache misses only, template-shortcut entries excluded).
        self.to_translate: list[str] = []
        self.billable_chars = 0


def gather_language(job: LanguageJob, en_data: object, cache: TranslationCache, verbose: bool) -> None:
    print(f"\n=== {job.yaml_path.name} ({job.lang_code}) ===")
    job.other_data = load_yaml(job.yaml_path)

    job.source_tpl, job.source_range_tpl = _detect_modbus_format(job.other_data)
    print(f"  Detected source template:       {job.source_tpl!r}")
    print(f"  Detected source_range template: {job.source_range_tpl!r}")

    _collect_untranslated(en_data, job.other_data, "", job.untranslated, job.missing, verbose)

    if verbose and job.missing:
        print(f"  {len(job.missing)} key(s) missing from this file:")
        for m in job.missing:
            print(f"    [MISSING] {m}")

    job.dupes_removed = _remove_duplicate_keys(en_data, job.other_data)

    unique_en = {en_val for path, en_val in job.untranslated if _needs_api(path, en_val, job.source_tpl, job.source_range_tpl)}
    job.to_translate = [s for s in unique_en if cache.get(job.lang_code, s) is None]
    job.billable_chars = sum(len(s) for s in job.to_translate)

    cached_hits = len(unique_en) - len(job.to_translate)
    print(
        f"  Found {len(job.untranslated)} untranslated value(s) "
        f"({len(unique_en)} unique string(s); {cached_hits} already cached, "
        f"{len(job.to_translate)} need translation -> {job.billable_chars} new character(s))."
    )


# ---------------------------------------------------------------------------
# Translate phase -- one language, using precomputed job data
# ---------------------------------------------------------------------------


def translate_language(
    job: LanguageJob,
    translator: "deepl.Translator | None",
    cache: TranslationCache,
    dry_run: bool,
    formality: str,
    batch_size: int,
) -> tuple[int, int]:
    """Returns (translated_count, skipped_count)."""
    if job.dupes_removed:
        if dry_run:
            print(f"  [DRY] Would remove {job.dupes_removed} stale duplicate key(s) from {job.yaml_path.name}.")
        else:
            print(f"  Removed {job.dupes_removed} stale duplicate key(s).")
            save_yaml(job.yaml_path, job.other_data)
            print(f"  Saved {job.yaml_path.name} ({job.dupes_removed} duplicates removed).")

    if not job.untranslated:
        if not job.dupes_removed:
            print("  Nothing to translate.")
        return 0, 0

    # Translate every unique string needing an API call, in batches.
    translation_lookup: dict[str, str] = {}
    total_batches = (len(job.to_translate) + batch_size - 1) // batch_size if job.to_translate else 0
    for i in range(0, len(job.to_translate), batch_size):
        batch = job.to_translate[i : i + batch_size]
        batch_num = i // batch_size + 1
        if not dry_run:
            print(f"  Translating batch {batch_num}/{total_batches} ({len(batch)} string(s)) ...")
        results = _translate_batch(batch, job.lang_code, translator, formality, dry_run)
        for en_val, translated in zip(batch, results):
            translation_lookup[en_val] = translated
            if not dry_run and translated != en_val:
                cache.set(job.lang_code, en_val, translated)

    translated = 0
    skipped = 0

    for path, en_val in job.untranslated:
        last_key = _parse_path(path)[-1]

        if last_key == "source" and job.source_tpl is not None and en_val == _EN_SOURCE:
            new_val = job.source_tpl
        elif last_key == "source_range" and job.source_range_tpl is not None and en_val == _EN_SOURCE_RANGE:
            new_val = job.source_range_tpl
        else:
            cached = cache.get(job.lang_code, en_val)
            new_val = cached if cached is not None else translation_lookup.get(en_val, en_val)
            if new_val == en_val:
                skipped += 1
                print(f"  [SKIP] {path}: '{en_val[:60]}'")
                continue

        if dry_run:
            print(f"  [DRY] {path}:")
            print(f"        EN:  {en_val[:80]!r}")
            print(f"        {job.lang_code.upper()}: {new_val[:80]!r}")
        else:
            if _set_by_path(job.other_data, path, new_val):
                print(f"  [OK]  {path}: {new_val[:60]!r}")
                translated += 1
            else:
                print(f"  [ERR] Could not set path: {path}", file=sys.stderr)
                skipped += 1

    if not dry_run and translated > 0:
        save_yaml(job.yaml_path, job.other_data)
        print(f"  Saved {job.yaml_path.name} ({translated} updates).")

    return translated, skipped


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate missing values in non-English YAML translation files using DeepL.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files or calling the API.")
    parser.add_argument("--lang", nargs="+", metavar="LANG", help="Limit to specific language code(s), e.g. --lang de fr.")
    parser.add_argument("--verbose", action="store_true", help="Also report English keys that are missing from target files.")
    parser.add_argument("--cache", metavar="PATH", default=str(DEFAULT_CACHE_PATH), help=f"Path to persistent JSON translation cache (default: {DEFAULT_CACHE_PATH}).")
    parser.add_argument("--no-cache", action="store_true", help="Disable the persistent on-disk cache.")
    parser.add_argument("--api-key", metavar="KEY", default=os.environ.get("DEEPL_AUTH_KEY"), help="DeepL API key (default: DEEPL_AUTH_KEY env var).")
    parser.add_argument("--formality", choices=["default", "more", "less", "prefer_more", "prefer_less"], default="default", help="Formality level for languages that support it.")
    parser.add_argument("--max-chars", type=int, default=None, help="Hard cap on new characters billed this run, in addition to your DeepL account quota.")
    parser.add_argument("--force", action="store_true", help="Proceed even if the pre-flight estimate exceeds remaining quota or --max-chars.")
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE, help=f"Strings per DeepL API call (default: {_DEFAULT_BATCH_SIZE}).")
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

    if not args.dry_run and not args.api_key:
        print("ERROR: No DeepL API key given. Pass --api-key or set DEEPL_AUTH_KEY.", file=sys.stderr)
        sys.exit(1)

    cache_path = None
    if not args.no_cache:
        try:
            resolved_cache = Path(args.cache).resolve()  # Snyk Code CWE-23 : Following code mitigates Path Traversal vulnerability
            if not resolved_cache.is_relative_to(PROJECT_ROOT):
                print(f"ERROR: Cache path must be within the project directory ({PROJECT_ROOT}).", file=sys.stderr)
                sys.exit(1)
            cache_path = resolved_cache
        except (TypeError, ValueError, RuntimeError, OSError) as exc:
            print(f"ERROR: Invalid cache path: {exc}", file=sys.stderr)
            sys.exit(1)
    cache = TranslationCache(cache_path)

    translator = deepl.Translator(args.api_key) if args.api_key else None

    # --- Gather phase: figure out exactly what would be billed, before any
    #     API call is made. ---
    jobs: list[LanguageJob] = []
    for stem, code in target_langs.items():
        yaml_path = TRANSLATIONS_DIR / f"{stem}.yaml"
        if not yaml_path.exists():
            print(f"WARNING: {yaml_path} not found - skipping.", file=sys.stderr)
            continue
        job = LanguageJob(stem, code)
        gather_language(job, en_data, cache, args.verbose)
        jobs.append(job)

    total_new_chars = sum(j.billable_chars for j in jobs)
    print(f"\n--- Pre-flight estimate: {total_new_chars} new character(s) would be billed across {len(jobs)} language file(s). ---")

    if not args.dry_run and total_new_chars > 0:
        if args.max_chars is not None and total_new_chars > args.max_chars and not args.force:
            print(f"ERROR: Estimate ({total_new_chars} chars) exceeds --max-chars ({args.max_chars}). Re-run with --force to proceed anyway, or narrow with --lang.", file=sys.stderr)
            sys.exit(1)

        # main() exits above if --api-key/DEEPL_AUTH_KEY is missing and we're
        # not in --dry-run, so translator is guaranteed set here.
        assert translator is not None, "translator must be set when dry_run is False"

        try:
            usage = translator.get_usage()
            if usage.character.valid:
                # .valid confirms both are non-None; the explicit int(...)
                # makes that narrowing visible to the type checker too.
                count = int(usage.character.count)  # type: ignore[arg-type]
                limit = int(usage.character.limit)  # type: ignore[arg-type]
                remaining = limit - count
                print(f"  DeepL account usage: {count}/{limit} characters this period ({remaining} remaining).")
                if total_new_chars > remaining and not args.force:
                    print(
                        f"ERROR: Estimate ({total_new_chars} chars) exceeds remaining quota ({remaining} chars). Re-run with --force to proceed anyway (DeepL will reject calls once the limit is hit), or narrow with --lang.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            else:
                print("  DeepL account usage: unlimited or unavailable (Pro plan) - skipping quota check.")
        except deepl.DeepLException as exc:
            print(f"  [WARN] Could not fetch DeepL usage: {exc}", file=sys.stderr)

    # --- Translate phase ---
    grand_translated = 0
    grand_skipped = 0

    for job in jobs:
        t, s = translate_language(job, translator, cache, args.dry_run, args.formality, args.batch_size)
        grand_translated += t
        grand_skipped += s

    cache.save()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done: {grand_translated} translated, {grand_skipped} skipped, ~{total_new_chars} new character(s) billed.")


if __name__ == "__main__":
    main()
