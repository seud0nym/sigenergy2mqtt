import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config


@pytest.fixture
def clean_argv():
    with patch.object(sys, "argv", ["sigenergy2mqtt"]):
        yield


def test_cli_parsing_clean(clean_argv, monkeypatch):
    # Set up mock argv with --clean
    with patch.object(sys, "argv", ["sigenergy2mqtt", "--clean"]):
        # We need to reload the module that does the parsing
        # sigenergy2mqtt.config.__init__ is where the parsing happens
        import sigenergy2mqtt.config as config_mod

        # Reset Config.clean before reload to ensure we are testing the reload effect
        Config.clean = False

        # Mock sys.exit to prevent the script from exiting
        with patch("sys.exit"):
            # Mock Path.mkdir and other side effects in __init__.py
            with (
                patch("pathlib.Path.mkdir"),
                patch("pathlib.Path.is_dir", return_value=True),
                patch("pathlib.Path.iterdir", return_value=[]),
                patch("os.access", return_value=True),
                patch("os.path.isdir", return_value=True),
            ):
                importlib.reload(config_mod)

                assert Config.clean is True


def test_cli_parsing_discovery_only(clean_argv, monkeypatch):
    # Set up mock argv with --hass-discovery-only
    with patch.object(sys, "argv", ["sigenergy2mqtt", "--hass-discovery-only"]):
        import sigenergy2mqtt.config as config_mod

        # Reset discovery_only before reload
        Config.home_assistant.discovery_only = False

        with patch("sys.exit"):
            with (
                patch("pathlib.Path.mkdir"),
                patch("pathlib.Path.is_dir", return_value=True),
                patch("pathlib.Path.iterdir", return_value=[]),
                patch("os.access", return_value=True),
                patch("os.path.isdir", return_value=True),
            ):
                importlib.reload(config_mod)

                assert Config.home_assistant.discovery_only is True
