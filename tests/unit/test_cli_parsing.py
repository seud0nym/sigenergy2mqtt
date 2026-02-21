import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import active_config


@pytest.fixture
def clean_argv():
    with patch.object(sys, "argv", ["sigenergy2mqtt"]):
        yield


def test_cli_parsing_clean(clean_argv, monkeypatch):
    args = ["--clean"]
    # We need to reload the module that does the parsing
    # sigenergy2mqtt.config.__init__ is where the parsing happens
    import sigenergy2mqtt.config as config_mod

    # Reset active_config.clean before reload to ensure we are testing the reload effect
    active_config.clean = False

    # Mock sys.exit to prevent the script from exiting
    with patch("sys.exit"):
        # Mock Path.mkdir and other side effects in __init__.py
        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[]),
            patch("os.access", return_value=True),
            patch("os.path.isdir", return_value=True),
            patch.object(config_mod.active_config, "reload"),
        ):
            config_mod.initialize(args)

            assert active_config.clean is True


def test_cli_parsing_discovery_only(clean_argv, monkeypatch):
    args = ["--hass-discovery-only"]
    import sigenergy2mqtt.config as config_mod

    # Reset discovery_only before reload
    active_config.home_assistant.discovery_only = False

    with patch("sys.exit"):
        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[]),
            patch("os.access", return_value=True),
            patch("os.path.isdir", return_value=True),
            patch.object(config_mod.active_config, "reload"),
        ):
            config_mod.initialize(args)

            assert active_config.home_assistant.discovery_only is True
