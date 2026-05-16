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
import ipaddress
import logging
import os
import socket
import sys
import time
from contextlib import contextmanager
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

if TYPE_CHECKING:
    from sigenergy2mqtt.common import ConsumptionMethod

    from .models import HomeAssistantConfig, InfluxDbConfig, ModbusConfig, MqttConfig, PersistenceConfig, PvOutputConfig

from ruamel.yaml import YAML

from sigenergy2mqtt import i18n
from sigenergy2mqtt.persistence import Category

from . import const, version
from .auto_discovery import scan as auto_discovery_scan
from .auto_discovery_settings import AutoDiscoverySettings
from .settings import Settings
from .sources import RuamelYamlSettingsSource, _auto_discovery_env_values


class ConfigurationError(Exception):
    """Raised when the configuration is invalid or cannot be loaded."""


class Config:
    """Holds the complete runtime configuration for sigenergy2mqtt.

    Configuration is layered in two passes:

    1. A YAML file loaded by :meth:`load` / :meth:`reload`.
    2. Environment variable overrides applied on top.

    The global singleton :data:`active_config` is the instance used at runtime.
    Direct instantiation is supported for testing via :func:`_swap_active_config`.
    """

    clean: bool = False
    origin: dict[str, str] = {"name": "sigenergy2mqtt", "sw": version.__version__, "url": "https://github.com/seud0nym/sigenergy2mqtt"}
    persistent_state_path: Path

    validate_only_mode: str | None = None
    validate_show_credentials: bool = False

    _settings: Settings | None
    _source: str | None

    if TYPE_CHECKING:
        log_level: int
        language: str
        consumption: ConsumptionMethod
        repeated_state_publish_interval: int
        sanity_check_default_kw: float
        sanity_check_failures_increment: bool
        ems_mode_check: bool
        metrics_enabled: bool
        sensor_debug_logging: bool
        home_assistant: HomeAssistantConfig
        mqtt: MqttConfig
        persistence: PersistenceConfig
        pvoutput: PvOutputConfig
        influxdb: InfluxDbConfig
        modbus: list[ModbusConfig]
        sensor_overrides: dict[str, Any]

    def __init__(self):
        self._source = None
        self._settings = None

        try:
            self.persistent_state_path = _create_persistent_state_path()
        except Exception:
            self.persistent_state_path = Path(".")

        try:
            self.reload(skip_auto_discovery=True)
        except Exception:
            pass

    @property
    def version(self) -> str:
        """Return the current sigenergy2mqtt version string."""
        return version.__version__

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

    def load(self, filename: str, skip_auto_discovery: bool = False) -> None:
        """Load configuration from a file.

        Records *filename* as the configuration source and delegates to :meth:`reload`.
        Subsequent calls to :meth:`reload` will re-read the same file.
        """
        logging.info(f"Loading configuration from {filename}...")
        self._source = filename
        self.reload(skip_auto_discovery=skip_auto_discovery)

    async def load_async(self, filename: str, skip_auto_discovery: bool = False) -> None:
        """Async version of :meth:`load`."""
        logging.info(f"Loading configuration from {filename} (async)...")
        self._source = filename
        await self.reload_async(skip_auto_discovery=skip_auto_discovery)

    def reload(self, skip_auto_discovery: bool = False) -> None:
        """Reload configuration from the YAML source file and re-apply all overrides."""
        auto_discovery_cache = self._perform_auto_discovery(skip_auto_discovery)
        self._finalize_reload(auto_discovery_cache)

    async def reload_async(self, skip_auto_discovery: bool = False) -> None:
        """Async version of :meth:`reload`."""
        auto_discovery_cache = await self._perform_auto_discovery_async(skip_auto_discovery)
        self._finalize_reload(auto_discovery_cache)

    def _finalize_reload(self, auto_discovery_cache: Path | None) -> None:
        """Final load including the auto discovery results (if any), WITH post-init validation."""
        self._settings = Settings(yaml_file_arg=self._source, discovery_yaml_arg=auto_discovery_cache)  # type: ignore[reportCallIssue]
        i18n.load(self._settings.language)

    def _perform_auto_discovery(self, skip_auto_discovery: bool) -> Path | None:
        """Synchronous auto-discovery logic."""
        auto_discovery, auto_discovery_cache, auto_settings = self._prepare_auto_discovery()

        if not skip_auto_discovery and self._should_run_discovery(auto_discovery, auto_discovery_cache):
            if auto_discovery != "force":
                self._restore_discovery_from_mqtt_sync(auto_discovery_cache)

            if auto_discovery == "force" or not auto_discovery_cache.is_file():
                include_networks = self._build_include_networks(auto_settings.modbus_auto_discovery_networks)
                logging.info(f"Auto-discovery required ({auto_discovery}), scanning for Sigenergy devices...")
                auto_discovered = self._run_auto_discovery(
                    auto_settings.modbus_port,
                    auto_settings.modbus_auto_discovery_ping_timeout,
                    auto_settings.modbus_auto_discovery_timeout,
                    auto_settings.modbus_auto_discovery_retries,
                    include_networks=include_networks,
                )
                if auto_discovered:
                    self._save_discovery_results_sync(auto_discovery_cache, auto_discovered)

        return self._get_final_cache_path(auto_discovery, auto_discovery_cache)

    async def _perform_auto_discovery_async(self, skip_auto_discovery: bool) -> Path | None:
        """Asynchronous auto-discovery logic."""
        auto_discovery, auto_discovery_cache, auto_settings = self._prepare_auto_discovery()

        if not skip_auto_discovery and self._should_run_discovery(auto_discovery, auto_discovery_cache):
            if auto_discovery != "force":
                await self._restore_discovery_from_mqtt_async(auto_discovery_cache)

            if auto_discovery == "force" or not auto_discovery_cache.is_file():
                include_networks = self._build_include_networks(auto_settings.modbus_auto_discovery_networks)
                logging.info(f"Auto-discovery required ({auto_discovery}), scanning for Sigenergy devices (async)...")
                auto_discovered = await self._run_auto_discovery_async(
                    auto_settings.modbus_port,
                    auto_settings.modbus_auto_discovery_ping_timeout,
                    auto_settings.modbus_auto_discovery_timeout,
                    auto_settings.modbus_auto_discovery_retries,
                    include_networks=include_networks,
                )
                if auto_discovered:
                    await self._save_discovery_results_async(auto_discovery_cache, auto_discovered)

        return self._get_final_cache_path(auto_discovery, auto_discovery_cache)

    def _prepare_auto_discovery(self):
        auto_discovery = os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY)
        auto_discovery_cache = Path(self.persistent_state_path, "auto-discovery.yaml")
        auto_settings = self._load_auto_discovery_settings()

        if auto_settings.modbus_auto_discovery:
            auto_discovery = auto_settings.modbus_auto_discovery
        if not auto_discovery and not self._has_modbus_source():
            auto_discovery = "once"

        return auto_discovery, auto_discovery_cache, auto_settings

    def _should_run_discovery(self, auto_discovery, auto_discovery_cache) -> bool:
        return auto_discovery == "force" or (auto_discovery == "once" and not auto_discovery_cache.is_file())

    def _get_final_cache_path(self, auto_discovery, auto_discovery_cache) -> Path | None:
        if auto_discovery == "once" and auto_discovery_cache.is_file():
            logging.info("Auto-discovery already completed, using cached results.")
            return auto_discovery_cache
        if not self._should_run_discovery(auto_discovery, auto_discovery_cache) and not auto_discovery_cache.is_file():
            logging.debug("Auto-discovery disabled")
            return None
        return auto_discovery_cache

    def _restore_discovery_from_mqtt_sync(self, auto_discovery_cache: Path):
        try:
            from sigenergy2mqtt.persistence import state_store

            if state_store.is_initialised:
                cached = state_store.load_sync(Category.CONFIG, "auto-discovery")
                if cached:
                    auto_discovery_cache.write_text(cached)
                    logging.info("Auto-discovery cache restored from MQTT")
        except Exception:
            logging.debug("StateStore not available for auto-discovery restore")

    async def _restore_discovery_from_mqtt_async(self, auto_discovery_cache: Path):
        try:
            from sigenergy2mqtt.persistence import state_store

            if state_store.is_initialised:
                cached = await state_store.load(Category.CONFIG, "auto-discovery")
                if cached:
                    auto_discovery_cache.write_text(cached)
                    logging.info("Auto-discovery cache restored from MQTT")
        except Exception:
            logging.debug("StateStore not available for auto-discovery restore")

    def _save_discovery_results_sync(self, auto_discovery_cache: Path, auto_discovered: list):
        yaml_content = self._serialize_discovery(auto_discovered)
        auto_discovery_cache.write_text(yaml_content)
        try:
            from sigenergy2mqtt.persistence import state_store

            if state_store.is_initialised:
                state_store.save_sync(Category.CONFIG, "auto-discovery", yaml_content)
        except Exception:
            pass

    async def _save_discovery_results_async(self, auto_discovery_cache: Path, auto_discovered: list):
        yaml_content = self._serialize_discovery(auto_discovered)
        auto_discovery_cache.write_text(yaml_content)
        try:
            from sigenergy2mqtt.persistence import state_store

            if state_store.is_initialised:
                await state_store.save(Category.CONFIG, "auto-discovery", yaml_content)
        except Exception:
            pass

    def _serialize_discovery(self, auto_discovered: list) -> str:
        with StringIO() as stream:
            _yaml = YAML(typ="safe", pure=True)
            _yaml.dump(auto_discovered, stream)
            return stream.getvalue()

    def _has_modbus_source(self) -> bool:
        """Return True when YAML or env provides enough data to build Modbus config."""
        return self._yaml_has_modbus_entries() or self._env_can_bootstrap_modbus()

    def _yaml_has_modbus_entries(self) -> bool:
        if not self._source:
            return False
        source_path = Path(self._source)
        if not source_path.is_file():
            return False

        yaml = YAML(typ="safe", pure=True)
        with open(source_path, "r") as f:
            data = yaml.load(f)
        if not isinstance(data, dict):
            return False

        entries = data.get("modbus")
        if not isinstance(entries, list) or len(entries) == 0:
            return False
        return any(isinstance(entry, dict) and bool(entry.get("host")) for entry in entries)

    @staticmethod
    def _env_can_bootstrap_modbus() -> bool:
        """Only SIGENERGY2MQTT_MODBUS_HOST can bootstrap modbus when YAML has no devices."""
        return bool(os.getenv(const.SIGENERGY2MQTT_MODBUS_HOST))

    def _load_auto_discovery_settings(self) -> AutoDiscoverySettings:
        """Parse only the pre-discovery settings using YAML + env source layering."""
        payload: dict[str, Any] = {}
        yaml_payload = RuamelYamlSettingsSource(AutoDiscoverySettings, self._source)()
        payload.update(
            {
                "modbus_port": yaml_payload.get("modbus-port"),
                "modbus_auto_discovery": yaml_payload.get("modbus-auto-discovery"),
                "modbus_auto_discovery_timeout": yaml_payload.get("modbus-auto-discovery-timeout"),
                "modbus_auto_discovery_ping_timeout": yaml_payload.get("modbus-auto-discovery-ping-timeout"),
                "modbus_auto_discovery_retries": yaml_payload.get("modbus-auto-discovery-retries"),
                "modbus_auto_discovery_networks": yaml_payload.get("modbus-auto-discovery-networks"),
            }
        )
        payload.update(_auto_discovery_env_values(os.getenv, include_modbus_port=True))
        payload = {k: v for k, v in payload.items() if v is not None}
        return AutoDiscoverySettings(**payload)

    def reset(self):
        """Reset all configuration to defaults, discarding any loaded state.

        Equivalent to constructing a fresh ``Config()`` instance.  Useful in tests
        that share a config object across multiple cases.
        """
        self._source = None
        self._settings = Settings()  # type: ignore[reportCallIssue]

    def _build_include_networks(self, user_networks: list[str]) -> list[str] | None:
        """Build the include_networks list for auto-discovery scanning.

        Prepends /32 CIDR networks derived from any already-configured modbus
        hosts (YAML or env) before the user-specified networks.  Hostnames are
        resolved to IPv4 addresses.

        Args:
            user_networks: Networks from ``modbus_auto_discovery_networks`` setting.

        Returns:
            A combined list of CIDR strings, or ``None`` when no networks are
            specified and no hosts are configured.
        """
        host_networks: list[str] = []

        # Collect hosts from YAML config
        if self._source:
            source_path = Path(self._source)
            if source_path.is_file():
                yaml = YAML(typ="safe", pure=True)
                with open(source_path, "r") as f:
                    data = yaml.load(f)
                if isinstance(data, dict):
                    entries = data.get("modbus")
                    if isinstance(entries, list):
                        for entry in entries:
                            if isinstance(entry, dict) and entry.get("host"):
                                host_networks.extend(self._resolve_host_to_cidr(entry["host"]))

        # Collect host from env override
        env_host = os.getenv(const.SIGENERGY2MQTT_MODBUS_HOST)
        if env_host:
            host_networks.extend(self._resolve_host_to_cidr(env_host))

        # Deduplicate while preserving order
        seen: set[str] = set()
        combined: list[str] = []
        for net in host_networks + user_networks:
            if net not in seen:
                seen.add(net)
                combined.append(net)

        return combined if combined else None

    @staticmethod
    def _resolve_host_to_cidr(host: str) -> list[str]:
        """Resolve a hostname or IP address to a list of /32 CIDR strings.

        If the host is already a valid IPv4 address, returns it as /32 directly.
        Otherwise attempts DNS resolution and returns /32 for each resolved
        IPv4 address.  On resolution failure, logs a warning and returns an
        empty list.
        """
        try:
            ipaddress.IPv4Address(host)
            return [f"{host}/32"]
        except ValueError:
            pass

        try:
            results = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
            ips: list[str] = []
            seen: set[str] = set()
            for _family, _type, _proto, _canonname, sockaddr in results:
                ip = str(sockaddr[0])
                if ip not in seen:
                    seen.add(ip)
                    ips.append(f"{ip}/32")
            if ips:
                logging.info(f"Resolved modbus host '{host}' to {', '.join(ips)} for auto-discovery")
                return ips
            logging.warning(f"Could not resolve modbus host '{host}' to any IPv4 address")
            return []
        except (socket.gaierror, OSError) as e:
            logging.warning(f"Failed to resolve modbus host '{host}' for auto-discovery: {e}")
            return []

    async def _run_auto_discovery_async(
        self,
        port: int,
        ping_timeout: float,
        modbus_timeout: float,
        modbus_retries: int,
        timeout: float = 120.0,
        include_networks: list[str] | None = None,
    ) -> list:
        """Asynchronous execution of auto-discovery scan."""
        try:
            return await asyncio.wait_for(
                auto_discovery_scan(include_networks, port, ping_timeout, modbus_timeout, modbus_retries),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logging.error(f"Auto-discovery timed out after {timeout:.1f}s")
            return []
        except Exception:
            logging.exception("Auto-discovery failed")
            return []

    def _run_auto_discovery(
        self,
        port: int,
        ping_timeout: float,
        modbus_timeout: float,
        modbus_retries: int,
        timeout: float = 120.0,
        include_networks: list[str] | None = None,
    ) -> list:
        """Synchronous execution of auto-discovery scan (wraps async version)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        coro = auto_discovery_scan(include_networks, port, ping_timeout, modbus_timeout, modbus_retries)
        if loop is None:
            try:
                return asyncio.run(coro)
            except Exception:
                logging.exception("Auto-discovery failed")
                return []

        # Fallback: if we are in a loop but must be sync, use a thread to avoid deadlock.
        import threading

        result: list = []
        exception: Exception | None = None

        def worker():
            nonlocal result, exception
            try:
                result = asyncio.run(coro)
            except Exception as e:
                exception = e

        thread = threading.Thread(target=worker, name="AutoDiscoveryWorker", daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            logging.error(f"Auto-discovery timed out after {timeout:.1f}s")
            return []
        if exception:
            logging.error(f"Auto-discovery failed: {exception}")
            return []
        return result

    def __getattr__(self, name: str) -> Any:
        if name == "_settings":
            raise AttributeError("_settings not initialised")
        # Fall through to settings for all data attributes
        return getattr(self._settings, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in ("persistent_state_path", "clean", "validate_only_mode", "validate_show_credentials"):
            super().__setattr__(name, value)
        elif self._settings and name in type(self._settings).model_fields:
            setattr(self._settings, name, value)
        else:
            super().__setattr__(name, value)

    def __str__(self) -> str:
        """Return the current configuration as nicely formatted YAML.

        Password and API-key style fields are redacted unless
        ``validate_show_credentials`` is explicitly enabled.
        """
        payload: dict[str, Any] = {}
        if self._settings is not None:
            payload = self._settings.model_dump(mode="json", by_alias=True, exclude_none=False)

        if not getattr(self, "validate_show_credentials", False):
            payload = self._redact_sensitive(deepcopy(payload))

        yaml = YAML(typ="safe", pure=True)
        yaml.default_flow_style = False
        stream = StringIO()
        yaml.dump(payload, stream)
        return stream.getvalue()

    def __repr__(self) -> str:
        """Return the YAML string representation used by :meth:`__str__`."""
        return self.__str__()

    @staticmethod
    def _redact_sensitive(data: Any) -> Any:
        """Return a deep-copied structure with sensitive values redacted."""
        redacted_keys = ("password", "api-key", "api_key", "apikey")

        if isinstance(data, dict):
            result: dict[str, Any] = {}
            for key, value in data.items():
                key_lower = str(key).lower()
                if any(s in key_lower for s in redacted_keys):
                    result[key] = "[REDACTED]"
                else:
                    result[key] = Config._redact_sensitive(value)
            return result

        if isinstance(data, list):
            return [Config._redact_sensitive(item) for item in data]

        return data


def _clean_stale_files(path: Path) -> None:
    """Remove files from *path* that have not been modified in the last 7 days.

    The following files are always retained regardless of age:

    - Files with the suffix ``.yaml``, ``.publishable``, or ``.token``

    Args:
        path: The directory to clean.  Only regular files are considered;
            subdirectories are ignored.
    """
    threshold_time = time.time() - (7 * 86400)
    _keep_suffixes = {".yaml", ".publishable", ".token"}
    for file in path.iterdir():
        if not file.is_file():
            continue
        stat = file.stat()
        if stat.st_mtime < threshold_time and file.suffix not in _keep_suffixes:
            try:
                file.unlink()
                logging.info(f"Removed stale state file: {file} (last modified: {time.ctime(stat.st_mtime)})")
            except (PermissionError, OSError) as e:
                logging.error(f"Failed to remove stale state file: {file} ({e})")


def _create_persistent_state_path() -> Path:
    """Find a writable base directory and create the ``sigenergy2mqtt`` subdirectory.

    Candidate base directories are tried in order: the value of the environment
    variable ``SIGENERGY2MQTT_STATE_DIR`` (if set), ``/data/``, ``/var/lib/``,
    the current user's home directory, and ``/tmp/``.  The first writable candidate
    is used.

    If the path resolves to an existing directory, it is cleaned via
    :func:`_clean_stale_files`.

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
                _clean_stale_files(path)
            return path.resolve()
    raise ConfigurationError("Unable to create persistent state folder!")


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

    # Apply log level immediately from env so initial logging is correct.
    log_level_name = os.getenv(const.SIGENERGY2MQTT_LOG_LEVEL)
    if log_level_name:
        level = getattr(logging, log_level_name, None)
        if level:
            logging.getLogger().setLevel(level)


def _system_initialize():
    """Perform one-time system-level initialisation before configuration is loaded.

    This classmethod should be called once at application startup, before
    constructing or loading any :class:`Config` instance.  It:

    1. Configures the root logger with an appropriate format (TTY, Docker, or
        plain syslog-style) via :func:`_setup_logging`.
    2. Logs the application and Python version.
    3. Enforces the minimum Python version requirement (3.12+).

    Raises:
        ConfigurationError: If the Python version requirement is not met, or if no
            writable directory can be found for persistent state storage.
    """
    _setup_logging()

    logging.info(f"Release {version.__version__} (Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})")

    min_version = (3, 12)
    if sys.version_info < min_version:
        raise ConfigurationError(f"Python {min_version[0]}.{min_version[1]} or higher is required!")


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


_system_initialize()

# Global singleton — the authoritative configuration instance at runtime.
if TYPE_CHECKING:
    active_config = Config()
else:
    active_config = _ConfigProxy(Config())
