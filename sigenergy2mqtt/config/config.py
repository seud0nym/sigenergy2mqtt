"""
Runtime configuration for sigenergy2mqtt.

Configuration is loaded from a YAML file and optionally overridden by environment
variables.  The single global instance :data:`active_config` is the authoritative
source of truth at runtime.  All other modules should read from this instance rather
than constructing their own.

Typical startup sequence::

    found_path = active_config.system_initialize()
    active_config.persistent_state_path = found_path
    active_config.load(config_filename)

For testing, use :func:`_swap_active_config` to temporarily replace the global::

    with _swap_active_config(Config()) as cfg:
        cfg.load("test_fixture.yaml")
        ...
"""

import asyncio
import logging
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from ruamel.yaml import YAML

from sigenergy2mqtt import i18n

from . import const, version
from .auto_discovery import scan as auto_discovery_scan
from .settings import Settings


class ConfigurationError(Exception):
    """Raised when the configuration is invalid or cannot be loaded."""


class Config:
    """Holds the complete runtime configuration for sigenergy2mqtt.

    Instances are initialised with sensible defaults via :meth:`_apply_defaults`.
    Configuration is then layered in two passes:

    1. A YAML file loaded by :meth:`load` / :meth:`reload`.
    2. Environment variable overrides applied on top.

    The global singleton :data:`active_config` is the instance used at runtime.
    Direct instantiation is supported for testing via :func:`_swap_active_config`.
    """

    clean: bool = False
    origin: dict[str, str] = {"name": "sigenergy2mqtt", "sw": version.__version__, "url": "https://github.com/seud0nym/sigenergy2mqtt"}
    persistent_state_path: Path

    _settings: Settings | None
    _source: str | None

    def __init__(self):
        self._source = None
        self._settings = None

        try:
            self.persistent_state_path = _create_persistent_state_path()
        except Exception:
            self.persistent_state_path = Path(".")

        try:
            self.reload()
        except Exception:
            pass

    def __getattr__(self, name: str) -> Any:
        if name == "_settings":
            raise AttributeError("_settings not initialised")
        # Fall through to settings for all data attributes
        return getattr(self._settings, name)

    def get_modbus_log_level(self) -> int:
        """Return the minimum log level across all configured Modbus devices.

        This is used to set the log level of the underlying Modbus library so that
        debug output is shown whenever any device is configured for debug logging.
        Returns ``logging.WARNING`` when no devices are configured.
        """
        if not self._settings or not self._settings.modbus:
            return logging.WARNING
        return min(device.log_level for device in self._settings.modbus)

    def set_modbus_log_level(self, level: int) -> None:
        """Set the log level on every configured Modbus device.

        Args:
            level: A ``logging`` module level constant (e.g. ``logging.DEBUG``).
        """
        if not self._settings:
            raise AttributeError("_settings not initialised")
        for device in self._settings.modbus:
            device.log_level = level

    def load(self, filename: str) -> None:
        """Load configuration from a YAML file and apply environment variable overrides.

        Records *filename* as the configuration source and delegates to :meth:`reload`.
        Subsequent calls to :meth:`reload` will re-read the same file.

        Args:
            filename: Path to the YAML configuration file.
        """
        logging.info(f"Loading configuration from {filename}...")
        self._source = filename
        self.reload()

    def reload(self) -> None:
        """Reload configuration from the YAML source file and re-apply all overrides.

        The full load sequence on every call:

        1. Reset all attributes to defaults via :meth:`_apply_defaults`.
        2. If a source file was set by :meth:`load`, parse and apply it.
        3. Run Modbus auto-discovery if requested (``force``) or not yet cached
           (``once``), writing results to a YAML cache file for subsequent runs.
        4. Apply environment variable overrides on top.
        5. Load the i18n translation for the resolved language.
        6. Merge auto-discovered devices into :attr:`modbus`.

        Raises:
            ConfigurationError: If an environment variable override cannot be processed.
            OSError: If the YAML source file or auto-discovery cache cannot be read or
                written.
        """

        auto_discovery = os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY)
        auto_discovery_cache = Path(self.persistent_state_path, "auto-discovery.yaml")

        if auto_discovery == "force" or (auto_discovery == "once" and not auto_discovery_cache.is_file()):
            port = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_PORT, "502"))
            modbus_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT, "0.25"))
            modbus_retries = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES, "0"))
            ping_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT, "0.5"))
            logging.info(f"Auto-discovery required ({auto_discovery}), scanning for Sigenergy devices ({port=} {ping_timeout=} {modbus_timeout=} {modbus_retries=})...")
            auto_discovered = self._run_auto_discovery(port, ping_timeout, modbus_timeout, modbus_retries)
            if len(auto_discovered) > 0:
                with open(auto_discovery_cache, "w") as f:
                    _yaml = YAML(typ="safe", pure=True)
                    _yaml.dump(auto_discovered, f)
        elif auto_discovery == "once" and auto_discovery_cache.is_file():
            logging.info("Auto-discovery already completed, using cached results.")
        else:
            logging.debug("Auto-discovery disabled")
            auto_discovery_cache = None

        self._settings = Settings(yaml_file_arg=self._source, discovery_yaml_arg=auto_discovery_cache)  # type: ignore[reportCallIssue]
        i18n.load(self._settings.language)

    def reset(self):
        """Reset all configuration to defaults, discarding any loaded state.

        Equivalent to constructing a fresh ``Config()`` instance.  Useful in tests
        that share a config object across multiple cases.
        """
        self._source = None
        self._settings = Settings()  # type: ignore[reportCallIssue]

    def _run_auto_discovery(self, port: int, ping_timeout: float, modbus_timeout: float, modbus_retries: int, timeout: float = 120.0) -> list:
        """Execute the async auto-discovery scan, handling event loop edge cases.

        If no event loop is running, uses asyncio.run(). If called from within
        already-running async code (e.g. during a reload triggered by a signal
        handler), submits the coroutine to the running loop via
        run_coroutine_threadsafe and waits up to *timeout* seconds.

        Args:
            port: The Modbus TCP port to scan.
            ping_timeout: Seconds to wait for an ICMP ping response.
            modbus_timeout: Seconds to wait for a Modbus TCP response.
            modbus_retries: Number of Modbus connection retries per host.
            timeout: Maximum seconds to wait when submitting to a running loop.

        Returns:
            A list of discovered device dicts, or an empty list on failure.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            # Normal case: no event loop running, asyncio.run() is safe.
            try:
                return asyncio.run(auto_discovery_scan(port, ping_timeout, modbus_timeout, modbus_retries))
            except Exception:
                logging.exception("Auto-discovery failed")
                return []

        # A loop is already running (e.g. called from a signal handler or sync
        # code invoked from async context). Submit to the running loop from this
        # thread and wait with a finite timeout to avoid hanging indefinitely.
        try:
            future = asyncio.run_coroutine_threadsafe(auto_discovery_scan(port, ping_timeout, modbus_timeout, modbus_retries), loop)
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()  # type: ignore - future is always bound before .result() raises.
            logging.error("Auto-discovery timed out after %.1fs", timeout)
            return []
        except Exception:
            logging.exception("Auto-discovery failed when submitting to running loop")
            return []

    def version(self) -> str:
        """Return the current sigenergy2mqtt version string."""
        return version.__version__

    @classmethod
    def system_initialize(cls):
        """Perform one-time system-level initialisation before configuration is loaded.

        This classmethod should be called once at application startup, before
        constructing or loading any :class:`Config` instance.  It:

        1. Configures the root logger with an appropriate format (TTY, Docker, or
           plain syslog-style) via :func:`_setup_logging`.
        2. Logs the application and Python version.
        3. Enforces the minimum Python version requirement (3.12+).
        4. Locates or creates the persistent state directory via
           :func:`_create_persistent_state_path`.
        5. Removes stale state files older than 7 days via :func:`_clean_stale_files`.

        Returns:
            The resolved :class:`~pathlib.Path` to the persistent state directory.

        Raises:
            ConfigurationError: If the Python version requirement is not met, or if no
                writable directory can be found for persistent state storage.
        """
        _setup_logging()

        logger = logging.getLogger("root")
        logger.info(f"Release {version.__version__} (Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})")

        min_version = (3, 12)
        if sys.version_info < min_version:
            raise ConfigurationError(f"Python {min_version[0]}.{min_version[1]} or higher is required!")

        found_path = _create_persistent_state_path()
        _clean_stale_files(found_path)
        return found_path


def _setup_logging() -> None:
    """Configure the root logger with a format appropriate to the runtime environment.

    Three formats are used:

    - **TTY**: includes timestamp and ``sigenergy2mqtt:`` prefix — for interactive use.
    - **Docker**: includes timestamp but no prefix — for structured container log collectors.
    - **Other**: no timestamp — for init systems (systemd, etc.) that add their own.
    """
    if os.isatty(sys.stdout.fileno()):
        fmt = "{asctime} {levelname:<8} sigenergy2mqtt:{module:.<15.15}{lineno:04d} {message}"
    else:
        cgroup = Path("/proc/self/cgroup")
        in_docker = Path("/.dockerenv").is_file() or (cgroup.is_file() and "docker" in cgroup.read_text())
        fmt = "{asctime} {levelname:<8} {module:.<15.15}{lineno:04d} {message}" if in_docker else "{levelname:<8} {module:.<15.15}{lineno:04d} {message}"
    logging.basicConfig(format=fmt, level=logging.INFO, style="{")


def _create_persistent_state_path() -> Path:
    """Find a writable base directory and create the ``sigenergy2mqtt`` subdirectory.

    Candidate base directories are tried in order: the value of the environment
    variable ``SIGENERGY2MQTT_STATE_DIR`` (if set), ``/data/``, ``/var/lib/``,
    the current user's home directory, and ``/tmp/``.  The first writable candidate
    is used.

    Returns:
        The resolved absolute :class:`~pathlib.Path` of the persistent state directory.

    Raises:
        ConfigurationError: If none of the candidate directories are writable.
    """
    candidates = [os.getenv("SIGENERGY2MQTT_STATE_DIR", None), "/data/", "/var/lib/", str(Path.home()), "/tmp/"]
    for base in candidates:
        if base is None:
            continue
        if os.path.isdir(base) and os.access(base, os.W_OK):
            path = Path(base, "sigenergy2mqtt")
            if not path.is_dir():
                logging.info(f"Persistent state folder '{path}' created")
                path.mkdir()
            else:
                logging.debug(f"Persistent state folder '{path}' already exists")
            return path.resolve()
    raise ConfigurationError("Unable to create persistent state folder!")


def _clean_stale_files(path: Path) -> None:
    """Remove files from *path* that have not been modified in the last 7 days.

    The following files are always retained regardless of age:

    - ``".current-version"``
    - Files with the suffix ``.yaml``, ``.publishable``, or ``.token``

    Args:
        path: The directory to clean.  Only regular files are considered;
            subdirectories are ignored.
    """
    threshold_time = time.time() - (7 * 86400)
    _keep_suffixes = {".yaml", ".publishable", ".token"}
    _keep_names = {".current-version"}
    for file in path.iterdir():
        if not file.is_file():
            continue
        stat = file.stat()
        if stat.st_mtime < threshold_time and file.name not in _keep_names and file.suffix not in _keep_suffixes:
            try:
                file.unlink()
                logging.info(f"Removed stale state file: {file} (last modified: {time.ctime(stat.st_mtime)})")
            except (PermissionError, OSError) as e:
                logging.error(f"Failed to remove stale state file: {file} ({e})")


class _ConfigProxy:
    """A proxy for the active Config instance that allows it to be swapped.

    This ensures that internal modules which do 'from sigenergy2mqtt.config import active_config'
    continue to refer to the same proxy object even when the underlying Config is replaced
    by _swap_active_config.
    """

    def __init__(self, config: Config):
        # Use super().__setattr__ to avoid recursion
        super().__setattr__("_config", config)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._config, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_config":
            super().__setattr__(name, value)
        else:
            setattr(self._config, name, value)

    def __delattr__(self, name: str) -> None:
        if name == "_config":
            super().__delattr__(name)
        else:
            delattr(self._config, name)

    def __repr__(self) -> str:
        return f"<ConfigProxy for {self._config!r}>"

    def __dir__(self):
        return dir(self._config)


@contextmanager
def _swap_active_config(new_config: Config) -> Generator[Config, None, None]:
    """Context manager that temporarily replaces the global :data:`active_config`.

    Intended for use in tests that need to load a fixture configuration without
    affecting the global singleton used by production code.  The original
    ``active_config`` is restored when the context exits, even if an exception is
    raised.

    Args:
        new_config: The :class:`Config` instance to install as the active config.

    Yields:
        *new_config*, so callers can use ``as`` to receive it::

            with _swap_active_config(Config()) as cfg:
                cfg.load("test_fixture.yaml")
                ...
    """
    global active_config
    if isinstance(active_config, _ConfigProxy):
        old = active_config._config
        active_config._config = new_config
        try:
            yield new_config
        finally:
            active_config._config = old
    else:
        # Fallback for when active_config is not proxied (e.g. during some edge cases in tests)
        old = active_config
        active_config = new_config
        try:
            yield new_config
        finally:
            active_config = old


# Global singleton — the authoritative configuration instance at runtime.
active_config = _ConfigProxy(Config())
