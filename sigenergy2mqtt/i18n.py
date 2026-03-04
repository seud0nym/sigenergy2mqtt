"""Internationalisation (i18n) support module.

Provides YAML-backed translation loading with language fallback to English,
system locale detection, and a simple key-based lookup API.

Typical usage::

    import i18n
    i18n.load("fr")
    label = i18n._t("MyClass.name", default="Name")
"""

import locale
import logging
import os
from pathlib import Path
from typing import Any, Final

from ruamel.yaml import YAML

DEFAULT_LANGUAGE: Final[str] = "en"

# Languages whose translation files use a script suffix (e.g. zh-Hans.yaml).
# Maps the bare language code to the preferred full tag, in priority order.
_SCRIPT_VARIANTS: Final[dict[str, list[str]]] = {
    "zh": ["zh-Hans", "zh-Hant"],
}


class Translator:
    """Loads and caches YAML translation files and resolves keyed lookups.

    Translation files live in the ``translations/`` sub-directory next to this
    module, one file per language (e.g. ``en.yaml``, ``fr.yaml``,
    ``zh-Hans.yaml``).  Keys are dot-separated paths into the YAML hierarchy;
    keys that do not start with ``cli.`` are automatically prefixed with
    ``class.`` to preserve backwards compatibility.

    When a key is not found in the requested language the lookup falls back to
    the default language (English).
    """

    def __init__(self) -> None:
        self._translations: dict[str, Any] = {}
        self._fallback_translations: dict[str, Any] = {}
        self._language: str = DEFAULT_LANGUAGE
        self._translations_dir = Path(__file__).parent / "translations"
        self._cache: dict[str, dict[str, Any]] = {}
        self._yaml = YAML(typ="safe", pure=True)
        self._available_translations: list[str] | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_available_translations(self) -> list[str]:
        """Return a sorted list of available language codes.

        The result is derived from YAML filenames in the translations directory
        and is cached after the first call.  Bare aliases (e.g. ``"zh"``) are
        included when an appropriate script-variant file exists (e.g.
        ``zh-Hans.yaml``) and the bare file does not.
        """
        if self._available_translations is None:
            found = sorted(f.stem for f in self._translations_dir.glob("*.yaml"))
            for bare, variants in _SCRIPT_VARIANTS.items():
                if bare not in found and any(v in found for v in variants):
                    found.append(bare)
            self._available_translations = sorted(found)
        return self._available_translations

    def load(self, language: str) -> None:
        """Load translations for *language*, with English as the fallback.

        Calling this method a second time with the same language is a no-op.
        Bare language codes that map to a script-variant file (e.g. ``"zh"``
        → ``zh-Hans.yaml``) are resolved transparently.
        """
        if self._language == language and self._translations:
            return

        resolved = self._resolve_language(language)
        self._language = language
        self._translations = self._load_file(resolved)

        if language != DEFAULT_LANGUAGE:
            self._fallback_translations = self._load_file(DEFAULT_LANGUAGE)
        else:
            # Avoid an alias to the same dict; a shallow copy is enough because
            # the translation dicts are never mutated after loading.
            self._fallback_translations = dict(self._translations)

    def reset(self) -> None:
        """Reset all state to initial defaults, clearing caches."""
        self._language = DEFAULT_LANGUAGE
        self._translations = {}
        self._fallback_translations = {}
        self._cache = {}
        self._available_translations = None
        self._yaml = YAML(typ="safe", pure=True)

    def set_translations(self, language: str, data: dict[str, Any]) -> None:
        """Inject translation data directly into the cache.

        Intended primarily for unit tests, so that real YAML files are not
        required on disk.
        """
        self._cache[language] = data
        if self._language == language:
            self._translations = data
        if language == DEFAULT_LANGUAGE:
            self._fallback_translations = data

    def translate(self, key: str, default: str | None = None) -> tuple[str, str, bool]:
        """Look up *key* and return ``(value, language_used, was_translated)``.

        Keys are resolved against the active language first, then against the
        English fallback.  A key that does not start with ``"cli."`` is
        automatically prefixed with ``"class."`` for backwards compatibility.

        If the resolved value is not a scalar type a warning is emitted and the
        lookup falls through to the fallback, rather than returning a
        stringified dict.

        Returns:
            A 3-tuple of:
            - The translated string (or *default* / *key* when not found).
            - The language code the value came from.
            - ``True`` when a translation was found, ``False`` otherwise.
        """
        lookup_key = key if key.startswith("cli.") else f"class.{key}"
        parts = lookup_key.split(".")

        value = self._get_nested(self._translations, parts)
        if value is not None:
            if not isinstance(value, (str, int, float, bool)):
                logging.warning(
                    "Translation key %r resolved to a non-scalar (%s); falling back to English.",
                    key,
                    type(value).__name__,
                )
            else:
                return str(value), self._language, True

        value = self._get_nested(self._fallback_translations, parts)
        if value is not None:
            if isinstance(value, (str, int, float, bool)):
                return str(value), DEFAULT_LANGUAGE, False
            logging.warning(
                "Fallback translation key %r also resolved to a non-scalar (%s).",
                key,
                type(value).__name__,
            )

        return default if default is not None else key, DEFAULT_LANGUAGE, False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_language(self, language: str) -> str:
        """Return the canonical language tag for *language*.

        For bare codes that have no corresponding YAML file (e.g. ``"zh"``),
        the first matching script-variant file is used instead
        (e.g. ``"zh-Hans"``).  If no match is found the original value is
        returned unchanged so that the missing-file path can handle the error.
        """
        if (self._translations_dir / f"{language}.yaml").exists():
            return language
        for variant in _SCRIPT_VARIANTS.get(language, []):
            if (self._translations_dir / f"{variant}.yaml").exists():
                return variant
        return language

    def _load_file(self, language: str) -> dict[str, Any]:
        """Load and cache the YAML file for *language*.

        Resolves language aliases (e.g. ``"zh"`` → ``"zh-Hans"``) before
        looking up the file, so callers do not need to pre-resolve.  Returns
        an empty dict if the file does not exist or cannot be parsed, logging
        a warning or error as appropriate.
        """
        if language in self._cache:
            return self._cache[language]

        resolved = self._resolve_language(language)
        file_path = self._translations_dir / f"{resolved}.yaml"
        if not file_path.exists():
            if language != DEFAULT_LANGUAGE:
                logging.warning("Translation file not found: %s", file_path)
            return {}

        try:
            with open(file_path, encoding="utf-8") as f:
                data: dict[str, Any] = self._yaml.load(f) or {}
                self._cache[language] = data
                return data
        except Exception as exc:
            logging.error("Failed to load translation file %s: %s", file_path, exc)
            return {}

    @staticmethod
    def _get_nested(data: dict, parts: list[str]) -> Any:
        """Traverse *data* along the dotted-key *parts* and return the value.

        Returns ``None`` if any segment is missing or if an intermediate node
        is not a dict.
        """
        current: Any = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


# ---------------------------------------------------------------------------
# Module-level singleton and public API
# ---------------------------------------------------------------------------

_translator = Translator()


def load(language: str) -> None:
    """Load translations for *language* into the module-level translator."""
    _translator.load(language)


def _t(key: str, default: str | None = None, debugging: bool = False, **kwargs) -> str:
    """Translate *key* and return the localised string.

    Template placeholders in the translated string (``{name}``) are replaced
    with matching keyword arguments.  Braces that are not placeholder names are
    left untouched, which avoids ``str.format()`` errors common in alarm
    translations.

    Args:
        key: Dot-separated translation key.
        default: Value to use when no translation is found.  Passing a default
            does *not* suppress lookup — it is returned only when the key is
            genuinely absent from both the active language and English.
        debugging: When ``True``, emit a DEBUG log entry on lookup failure.
        **kwargs: Placeholder values for string interpolation.  Pass
            ``translate=False`` to skip translation entirely and return
            *default* (or *key*) as-is.

    Returns:
        The translated and interpolated string.
    """
    if kwargs.get("translate", True) is False:
        return default if default is not None else key

    translation, language, translated = _translator.translate(key, default)

    if not translated:
        if debugging:
            logging.debug("%s : %s=%r %s=%r [%s]", key, "default", default, "translation", translation, language)
        if default is None:
            # Only warn when there is no intentional fallback; callers that
            # supply a default are using it as the expected display value.
            logging.warning("No translation found for key %r.", key)

    try:
        result = translation
        for k, v in kwargs.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result
    except Exception as exc:
        logging.warning("Translation formatting failed for key %r: %s", key, exc)
        return translation


def reset() -> None:
    """Reset the module-level translator to its initial state."""
    _translator.reset()


def set_translations(language: str, data: dict[str, Any]) -> None:
    """Inject translation data for *language* (primarily for testing)."""
    _translator.set_translations(language, data)


def get_available_translations() -> list[str]:
    """Return a sorted list of available language codes."""
    return _translator.get_available_translations()


def get_default_language() -> str:
    """Determine the best default language from the system environment.

    Checks, in order:

    1. The current locale (``locale.getlocale()``).
    2. The ``LANG`` environment variable.

    Falls back to :data:`DEFAULT_LANGUAGE` (``"en"``) when neither source
    yields a supported language.  For bare ``"zh"`` the first available
    script-variant (``zh-Hans`` then ``zh-Hant``) is preferred.
    """
    available = get_available_translations()

    def _resolve_zh(candidates: list[str]) -> str | None:
        return next((c for c in candidates if c in available), None)

    def _match(lang: str) -> str | None:
        """Return the best available tag for *lang*, or ``None``."""
        if lang in _SCRIPT_VARIANTS:
            return _resolve_zh(_SCRIPT_VARIANTS[lang])
        return lang if lang in available else None

    # 1. System locale
    try:
        sys_lang, _ = locale.getlocale()
        if sys_lang:
            matched = _match(sys_lang.split("_")[0].lower())
            if matched:
                return matched
    except Exception:
        pass

    # 2. LANG environment variable
    lang_env = os.environ.get("LANG", "")
    if lang_env:
        lang = lang_env.split("_")[0].split(".")[0].split(":")[0].lower()
        matched = _match(lang)
        if matched:
            return matched

    return DEFAULT_LANGUAGE
