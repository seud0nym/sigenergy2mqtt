import asyncio
import signal

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.main import main as main_mod


@pytest.mark.asyncio
async def test_async_main_with_no_devices(monkeypatch):
    # Ensure no devices to probe so async_main skips modbus probing
    monkeypatch.setattr(Config, "modbus", [], raising=False)
    monkeypatch.setattr(Config, "pvoutput", Config.pvoutput, raising=False)
    Config.pvoutput.enabled = False
    monkeypatch.setattr(main_mod, "ThreadConfigFactory", main_mod.ThreadConfigFactory, raising=False)
    # Prevent Config.get_modbus_log_level from failing when devices is empty
    import logging as _logging

    monkeypatch.setattr(Config, "get_modbus_log_level", classmethod(lambda cls: _logging.INFO), raising=False)
    monkeypatch.setattr(Config, "validate", classmethod(lambda cls: None), raising=False)

    called = {}

    async def fake_start(configs, upgrade_clean_required):
        called["configs"] = configs
        called["upgrade"] = upgrade_clean_required

    # Prevent changing real signal handlers in test runner
    monkeypatch.setattr(signal, "signal", lambda *a, **k: None)
    monkeypatch.setattr(main_mod, "start", fake_start)

    await main_mod.async_main()

    # start should have been called with a list (configs)
    assert "configs" in called
    assert isinstance(called["configs"], list)


@pytest.mark.asyncio
async def test_async_main_registers_signal_handlers_and_callable(monkeypatch):
    # Setup minimal config
    monkeypatch.setattr(Config, "modbus", [], raising=False)
    monkeypatch.setattr(Config, "pvoutput", Config.pvoutput, raising=False)
    Config.pvoutput.enabled = False
    import logging as _logging

    monkeypatch.setattr(Config, "get_modbus_log_level", classmethod(lambda cls: _logging.INFO), raising=False)
    monkeypatch.setattr(Config, "validate", classmethod(lambda cls: None), raising=False)

    # Capture registered signal handlers
    handlers = {}

    def fake_signal(sig, handler):
        handlers[sig] = handler

    monkeypatch.setattr(signal, "signal", fake_signal)

    called = {}

    async def fake_start(configs, upgrade_clean_required):
        called["called"] = True

    monkeypatch.setattr(main_mod, "start", fake_start)
    monkeypatch.setattr(main_mod, "pymodbus_apply_logging_config", lambda *a, **k: None)
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", classmethod(lambda cls: []), raising=False)
    monkeypatch.setattr(main_mod, "get_pvoutput_services", lambda configs: [])

    await main_mod.async_main()

    # Ensure handlers registered
    assert signal.SIGINT in handlers
    assert signal.SIGHUP in handlers
    assert signal.SIGTERM in handlers
    assert signal.SIGUSR1 in handlers

    # Call each handler to ensure they are callable and don't raise
    for sig in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM, signal.SIGUSR1):
        handlers[sig](sig, None)


@pytest.mark.asyncio
async def test_async_main_writes_persistent_version_on_upgrade(tmp_path, monkeypatch):
    # Setup config to enable home assistant and pvoutput write flow
    monkeypatch.setattr(Config, "modbus", [], raising=False)
    monkeypatch.setattr(Config, "pvoutput", Config.pvoutput, raising=False)
    monkeypatch.setattr(Config, "persistent_state_path", tmp_path, raising=False)
    monkeypatch.setattr(Config, "home_assistant", Config.home_assistant, raising=False)
    Config.home_assistant.enabled = True
    import logging as _logging

    monkeypatch.setattr(Config, "get_modbus_log_level", classmethod(lambda cls: _logging.INFO), raising=False)
    monkeypatch.setattr(Config, "validate", classmethod(lambda cls: None), raising=False)

    # create existing .current-version file with old version
    cur_file = tmp_path / ".current-version"
    cur_file.write_text("old-version")

    # Cause Config.version() to return a new value
    monkeypatch.setattr(Config, "version", staticmethod(lambda: "new-version"), raising=False)

    # Ensure start doesn't actually run threads
    async def fake_start(configs, upgrade_clean_required):
        return

    monkeypatch.setattr(main_mod, "start", fake_start)
    monkeypatch.setattr(main_mod, "pymodbus_apply_logging_config", lambda *a, **k: None)
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", classmethod(lambda cls: []), raising=False)
    monkeypatch.setattr(main_mod, "get_pvoutput_services", lambda configs: [])

    # Prevent signal changes in test runner
    monkeypatch.setattr(signal, "signal", lambda *a, **k: None)

    await main_mod.async_main()

    # File should be updated to new version
    assert cur_file.read_text() == "new-version"
