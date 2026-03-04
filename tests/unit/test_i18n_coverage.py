import os
from unittest.mock import MagicMock, patch

from sigenergy2mqtt.i18n import Translator, _t, _translator, get_default_language, reset, set_translations


def test_translator_cache_hit():
    t = Translator()
    t._cache["test"] = {"key": "value"}
    assert t._load_file("test") == {"key": "value"}


def test_translator_zh_mapping():
    t = Translator()
    # Mock the directory and the files it creates
    mock_dir = MagicMock()
    t._translations_dir = mock_dir

    mock_zh = MagicMock()
    mock_zh.exists.return_value = False
    mock_zh_hans = MagicMock()
    mock_zh_hans.exists.return_value = True

    def mock_div(name):
        if "zh.yaml" in name:
            return mock_zh
        if "zh-Hans.yaml" in name:
            return mock_zh_hans
        return MagicMock()

    mock_dir.__truediv__.side_effect = mock_div

    # Mock YAML and open
    with patch.object(t, "_yaml") as mock_yaml:
        mock_yaml.load.return_value = {"zh": 1}
        with patch("builtins.open", MagicMock()):
            assert t._load_file("zh") == {"zh": 1}

    # Line 63
    t.load("zh")
    assert t._language == "zh"


def test_load_file_not_found_warning():
    t = Translator()
    mock_dir = MagicMock()
    t._translations_dir = mock_dir
    mock_file = MagicMock()
    mock_file.exists.return_value = False
    mock_dir.__truediv__.return_value = mock_file

    with patch("sigenergy2mqtt.i18n.logging.warning") as mock_warn:
        t._load_file("nonexistent")
        mock_warn.assert_called()


def test_load_file_exception():
    t = Translator()
    mock_dir = MagicMock()
    t._translations_dir = mock_dir
    mock_file = MagicMock()
    mock_file.exists.return_value = True
    mock_dir.__truediv__.return_value = mock_file

    with patch("builtins.open", side_effect=Exception("perm error")):
        with patch("sigenergy2mqtt.i18n.logging.error") as mock_error:
            assert t._load_file("en") == {}
            mock_error.assert_called()


def test_load_fallback_branch():
    t = Translator()
    with patch.object(t, "_load_file", side_effect=[{"lang": "nl"}, {"lang": "en"}]):
        t._language = "init"
        t.load("nl")
        assert t._translations == {"lang": "nl"}
        assert t._fallback_translations == {"lang": "en"}

    t.load("nl")


def test_set_translations_logic():
    t = Translator()
    t._language = "en"
    t.set_translations("en", {"a": 1})
    assert t._translations == {"a": 1}
    assert t._fallback_translations == {"a": 1}

    t._language = "nl"
    t.set_translations("nl", {"b": 2})
    assert t._translations == {"b": 2}


def test_global_set_translations():
    reset()
    set_translations("fr", {"c": 3})
    assert _translator._cache["fr"] == {"c": 3}


def test_get_nested_missing_part():
    t = Translator()
    assert t._get_nested({"a": {"b": 1}}, ["a", "c"]) is None
    assert t._get_nested({"a": 1}, ["a", "b"]) is None


def test_translate_fallback_to_english():
    t = Translator()
    t._translations = {"class": {"known": "ja"}}
    t._fallback_translations = {"class": {"unknown_in_primary": "fallback_en"}}
    t._language = "nl"

    val, lang, tr = t.translate("known")
    assert val == "ja"

    val, lang, tr = t.translate("unknown_in_primary")
    assert val == "fallback_en"
    assert lang == "en"
    assert tr is False

    val, lang, tr = t.translate("totally_unknown")
    assert val == "totally_unknown"


def test_t_no_translate_flag():
    assert _t("key", default="def", translate=False) == "def"


def test_t_debugging_and_failure_logs():
    reset()
    with patch("sigenergy2mqtt.i18n.logging.warning") as mock_warn:
        with patch("sigenergy2mqtt.i18n.logging.debug") as mock_debug:
            with patch.object(_translator, "translate", return_value=("key", "en", False)):
                _t("missing_key", debugging=True)
                mock_debug.assert_called()
                mock_warn.assert_called()


def test_t_formatting_exception():
    reset()
    with patch.object(_translator, "translate", return_value=(None, "en", True)):
        with patch("sigenergy2mqtt.i18n.logging.warning") as mock_warn:
            assert _t("class.bad", x=1) is None
            mock_warn.assert_called()


def test_get_default_language_exhaustive():
    with patch("sigenergy2mqtt.i18n.get_available_translations") as mock_avail:
        mock_avail.return_value = ["en", "nl", "zh-Hans", "zh-Hant"]

        with patch("locale.getlocale", return_value=("zh_CN", "UTF-8")):
            assert get_default_language() == "zh-Hans"

        mock_avail.return_value = ["en", "zh-Hant"]
        with patch("locale.getlocale", return_value=("zh_TW", "UTF-8")):
            assert get_default_language() == "zh-Hant"

        mock_avail.return_value = ["en", "nl"]
        with patch("sigenergy2mqtt.i18n.locale.getlocale", return_value=("nl_NL", "UTF-8")):
            assert get_default_language() == "nl"

        with patch("locale.getlocale", side_effect=Exception("fail")):
            with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}):
                assert get_default_language() == "en"

    with patch("locale.getlocale", return_value=(None, None)):
        with patch("sigenergy2mqtt.i18n.get_available_translations") as mock_avail:
            mock_avail.return_value = ["en", "nl", "zh-Hans", "zh-Hant"]
            with patch.dict(os.environ, {"LANG": "zh_CN.UTF-8"}):
                assert get_default_language() == "zh-Hans"

            mock_avail.return_value = ["en", "zh-Hant"]
            with patch.dict(os.environ, {"LANG": "zh_TW.UTF-8"}):
                assert get_default_language() == "zh-Hant"

            mock_avail.return_value = ["en", "nl"]
            with patch.dict(os.environ, {"LANG": "nl_BE.UTF-8"}):
                assert get_default_language() == "nl"

        with patch.dict(os.environ, {}, clear=True):
            assert get_default_language() == "en"
