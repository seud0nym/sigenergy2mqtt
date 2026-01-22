import logging
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class Translator:
    def __init__(self):
        self._translations: dict[str, Any] = {}
        self._fallback_translations: dict[str, Any] = {}
        self._locale: str = "en"
        self._locales_dir = Path(__file__).parent / "locales"
        self._cache: dict[str, dict[str, Any]] = {}
        self._yaml = YAML(typ="safe", pure=True)

    def load(self, locale: str):
        if self._locale == locale and self._translations:
            return

        self._locale = locale
        self._translations = self._load_file(locale)
        if locale != "en":
            self._fallback_translations = self._load_file("en")
        else:
            self._fallback_translations = self._translations

    def reset(self):
        self._locale = "en"
        self._translations = {}
        self._fallback_translations = {}
        self._cache = {}
        # We don't need to reset self._yaml as it is stateless regarding translations

    def set_translations(self, locale: str, data: dict[str, Any]):
        """Inject translations directly into the cache (primarily for testing)."""
        self._cache[locale] = data
        if self._locale == locale:
            self._translations = data
        if locale == "en":
            self._fallback_translations = data

    def _load_file(self, locale: str) -> dict[str, Any]:
        if locale in self._cache:
            return self._cache[locale]

        file_path = self._locales_dir / f"{locale}.yaml"
        if not file_path.exists():
            if locale != "en":
                logging.warning(f"Translation file not found: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = self._yaml.load(f) or {}
                self._cache[locale] = data
                return data
        except Exception as e:
            logging.error(f"Failed to load translation file {file_path}: {e}")
            return {}

    def translate(self, key: str, default: str | None = None) -> str:
        # Key format: "ClassName.field" or "ClassName.field.index"
        parts = key.split(".")

        # Try primary locale
        value = self._get_nested(self._translations, parts)
        if value is not None:
            return str(value)

        # Try fallback locale (English)
        value = self._get_nested(self._fallback_translations, parts)
        if value is not None:
            return str(value)

        return default if default is not None else key

    def _get_nested(self, data: dict, parts: list[str]) -> Any:
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


_translator = Translator()


def load(locale: str):
    _translator.load(locale)


def _t(key: str, default: str | None = None) -> str:
    return _translator.translate(key, default)


def reset():
    _translator.reset()


def set_translations(locale: str, data: dict[str, Any]):
    _translator.set_translations(locale, data)
