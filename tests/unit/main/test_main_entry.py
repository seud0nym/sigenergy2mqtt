import builtins
import os
import signal
import sys
from types import SimpleNamespace
import pytest

import sigenergy2mqtt.__main__ as main_mod

# Test early signal handler behavior without exiting the process
def test_make_early_signal_handler_first_and_second_signal(monkeypatch):
    # Patch os._exit to capture calls
    exit_calls = []
    monkeypatch.setattr(main_mod.os, "_exit", lambda code: exit_calls.append(code))
    # Mock auto_discovery interrupt flag
    monkeypatch.setattr(main_mod.auto_discovery, "_interrupted", False)
    handler = main_mod._make_early_signal_handler()
    # First call should set flag but not exit
    handler(signal.SIGINT, None)
    assert main_mod.auto_discovery._interrupted is True
    assert exit_calls == []
    # Second call should trigger os._exit with code 130 for SIGINT
    handler(signal.SIGINT, None)
    assert exit_calls == [130]

# Test that _validate_main runs async initialize and validates connections
@pytest.mark.asyncio
async def test_validate_main_calls_initialize_and_validate(monkeypatch):
    called = {}
    async def fake_init():
        called["init"] = True
    async def fake_validate(show_credentials=False):
        called["validate"] = True
    monkeypatch.setattr(main_mod, "initialize_async", fake_init)
    monkeypatch.setattr(main_mod, "validate_connections", fake_validate)
    await main_mod._validate_main(show_credentials=False)
    assert called.get("init") and called.get("validate")

# Test main flow for configuration error handling
def test_main_configuration_error(monkeypatch, caplog):
    """ConfigurationError should be logged as CRITICAL and exit with code 1."""
    class DummyError(main_mod.ConfigurationError):
        pass
    monkeypatch.setattr(main_mod, "initialize", lambda: (_ for _ in ()).throw(DummyError("bad")))
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 1
    assert any("Configuration error" in rec.message for rec in caplog.records)

# Test main handling of KeyboardInterrupt during init
def test_main_keyboard_interrupt(monkeypatch, caplog):
    """KeyboardInterrupt during initialize should log info and exit with code 130."""
    monkeypatch.setattr(main_mod, "initialize", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 130
    assert any("Initialization interrupted" in rec.message for rec in caplog.records)

# Test that when validate_only_mode is set, main runs _validate_main and exits 0
def test_main_validate_only_mode(monkeypatch):
    """When validate_only_mode is set, main should run _validate_main and exit with 0."""
    cfg = SimpleNamespace(
        validate_only_mode=True,
        validate_show_credentials=False,
        log_level=20,  # logging.INFO — needed if execution leaks past sys.exit
    )
    monkeypatch.setattr(main_mod, "active_config", cfg)
    monkeypatch.setattr(main_mod, "initialize", lambda: True)
    called = {}
    async def fake_validate_main(show_credentials=False):
        called["called"] = True
    monkeypatch.setattr(main_mod, "_validate_main", fake_validate_main)
    # Defensively patch async_main so it never runs if execution somehow leaks past sys.exit
    async def fake_async_main():
        pass
    monkeypatch.setattr(main_mod, "async_main", fake_async_main)
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 0
    assert called.get("called")
