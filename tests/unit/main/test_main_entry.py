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
def test_main_configuration_error(monkeypatch, capsys):
    # Make initialize raise ConfigurationError
    class DummyError(main_mod.ConfigurationError):
        pass
    monkeypatch.setattr(main_mod, "initialize", lambda: (_ for _ in ()).throw(DummyError("bad")))
    # Patch sys.exit to capture exit code
    exit_codes = []
    monkeypatch.setattr(sys, "exit", lambda code=0: exit_codes.append(code))
    # Run main (should hit except and call sys.exit(1))
    main_mod.main()
    captured = capsys.readouterr()
    assert "Configuration error" in captured.out
    assert exit_codes == [1]

# Test main handling of KeyboardInterrupt during init
def test_main_keyboard_interrupt(monkeypatch, capsys):
    # initialize returns True then raise KeyboardInterrupt on second call
    state = {"called": 0}
    def fake_initialize():
        state["called"] += 1
        if state["called"] == 2:
            raise KeyboardInterrupt
        return True
    monkeypatch.setattr(main_mod, "initialize", fake_initialize)
    exit_codes = []
    monkeypatch.setattr(sys, "exit", lambda code=0: exit_codes.append(code))
    # Patch Metrics.shutdown to avoid side effects
    monkeypatch.setattr(main_mod.Metrics, "shutdown", lambda timeout=2.0: None)
    # Run main – should handle KeyboardInterrupt and exit with code 130
    main_mod.main()
    captured = capsys.readouterr()
    assert "Initialization interrupted" in captured.out
    assert exit_codes == [130]

# Test that when validate_only_mode is set, main runs _validate_main and exits 0
def test_main_validate_only_mode(monkeypatch, capsys):
    # Mock active_config with validate_only_mode flag
    cfg = SimpleNamespace(validate_only_mode=True, validate_show_credentials=False)
    monkeypatch.setattr(main_mod, "active_config", cfg)
    # Mock initialize to return True
    monkeypatch.setattr(main_mod, "initialize", lambda: True)
    # Patch _validate_main to record call
    called = {}
    async def fake_validate(show_credentials=False):
        called["called"] = True
    monkeypatch.setattr(main_mod, "_validate_main", fake_validate)
    # Patch signal handling to default
    monkeypatch.setattr(main_mod.signal, "default_int_handler", lambda *a, **k: None)
    # Patch sys.exit to capture
    exit_codes = []
    monkeypatch.setattr(sys, "exit", lambda code=0: exit_codes.append(code))
    # Run main
    main_mod.main()
    captured = capsys.readouterr()
    assert called.get("called")
    assert exit_codes == [0]
