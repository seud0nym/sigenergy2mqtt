import locale
import logging
import os
from pathlib import Path
from typing import Any, Final

from ruamel.yaml import YAML

DEFAULT_LANGUAGE: Final[str] = "en"


class Translator:
    def __init__(self):
        self._translations: dict[str, Any] = {}
        self._fallback_translations: dict[str, Any] = {}
        self._language: str = DEFAULT_LANGUAGE
        self._translations_dir = Path(__file__).parent / "translations"
        self._cache: dict[str, dict[str, Any]] = {}
        self._yaml = YAML(typ="safe", pure=True)
        self._available_translations: list[str] | None = None

    def get_available_translations(self) -> list[str]:
        """Return a list of available language codes (cached)."""
        if self._available_translations is None:
            self._available_translations = sorted([f.stem for f in self._translations_dir.glob("*.yaml")])
        return self._available_translations

    def load(self, language: str):
        if self._language == language and self._translations:
            return

        self._language = language
        self._translations = self._load_file(language)
        if language != DEFAULT_LANGUAGE:
            self._fallback_translations = self._load_file(DEFAULT_LANGUAGE)
        else:
            self._fallback_translations = self._translations

    def reset(self):
        self._language = DEFAULT_LANGUAGE
        self._translations = {}
        self._fallback_translations = {}
        self._cache = {}
        self._available_translations = None
        # We don't need to reset self._yaml as it is stateless regarding translations

    def set_translations(self, language: str, data: dict[str, Any]):
        """Inject translations directly into the cache (primarily for testing)."""
        self._cache[language] = data
        if self._language == language:
            self._translations = data
        if language == DEFAULT_LANGUAGE:
            self._fallback_translations = data

    def _load_file(self, language: str) -> dict[str, Any]:
        if language in self._cache:
            return self._cache[language]

        file_path = self._translations_dir / f"{language}.yaml"
        if not file_path.exists():
            if language != DEFAULT_LANGUAGE:
                logging.warning(f"Translation file not found: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = self._yaml.load(f) or {}
                self._cache[language] = data
                return data
        except Exception as e:
            logging.error(f"Failed to load translation file {file_path}: {e}")
            return {}

    def translate(self, key: str, default: str | None = None) -> tuple[str, str, bool]:
        # Key format: "ClassName.field" or "ClassName.field.index"
        parts = key.split(".")

        # Try primary language
        value = self._get_nested(self._translations, parts)
        if value is not None:
            return str(value), self._language, True

        # Try fallback language (English)
        value = self._get_nested(self._fallback_translations, parts)
        if value is not None:
            return str(value), DEFAULT_LANGUAGE, False

        return default if default is not None else key, DEFAULT_LANGUAGE, False

    def _get_nested(self, data: dict, parts: list[str]) -> Any:
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


_translator = Translator()


def load(language: str):
    _translator.load(language)


def _t(key: str, default: str | None = None, debugging: bool = False, **kwargs) -> str:
    translation, language, translated = _translator.translate(key, default)
    if not translated:
        if debugging:
            logging.debug(f"{key} : {default=} {translation=} [{language}]")
        logging.warning(f"{key} Failed to translate! Using {default=}")

    try:
        return translation.format(**kwargs)
    except KeyError as e:
        logging.warning(f"{key} Translation formatting failed: missing key {e}")
        return translation
    except Exception as e:
        logging.warning(f"{key} Translation formatting failed: {e}")
        return translation


def reset():
    _translator.reset()


def set_translations(language: str, data: dict[str, Any]):
    _translator.set_translations(language, data)


def get_available_translations() -> list[str]:
    return _translator.get_available_translations()


def get_default_language() -> str:
    """Determine the default language based on system settings and available translations."""
    available = get_available_translations()

    # Try language module first
    try:
        # First try getlocale() which is not deprecated
        sys_lang, _ = locale.getlocale()
        if sys_lang:
            lang = sys_lang.split("_")[0].lower()
            if lang in available:
                return lang
    except Exception:
        pass

    try:
        # Fallback to getdefaultlocale() if getlocale() didn't work
        sys_lang, _ = locale.getdefaultlocale()
        if sys_lang:
            lang = sys_lang.split("_")[0].lower()
            if lang in available:
                return lang
    except Exception:
        pass

    # Try LANG environment variable as fallback
    lang_env = os.environ.get("LANG")
    if lang_env:
        # Handle formats like en_US.UTF-8 or en_US:en
        lang = lang_env.split("_")[0].split(".")[0].split(":")[0].lower()
        if lang in available:
            return lang

    return DEFAULT_LANGUAGE
