import asyncio
import ipaddress
from dataclasses import dataclass, field
from typing import Literal

from sigenergy2mqtt.devices import Device


@dataclass
class ThreadConfig:
    """Configuration for a single Modbus polling thread.

    Each instance represents one Modbus TCP connection, identified by host and
    port, and owns the collection of devices polled over that connection.

    Args:
        name: Human-readable label for this thread. Used in logs and as the
            fallback ``url`` when no host is configured. At least one of
            ``name`` or ``host`` must be non-blank.
        host: IP address or hostname of the Modbus TCP target. May be ``None``
            for configs that are identified by name only.
        port: TCP port of the Modbus target. Must be in the range 0–65535 if
            provided. ``None`` is permitted when ``host`` is also ``None``.
        timeout: Per-request timeout in seconds passed to the Modbus client.
            Defaults to ``1.0``.
        retries: Number of retry attempts on failure passed to the Modbus
            client. Defaults to ``3``.

    Raises:
        ValueError: If both ``name`` and ``host`` are absent or blank.
        ValueError: If ``port`` is outside the range 0–65535.
    """

    name: str
    host: str | None
    port: int | None
    timeout: float = 1.0
    retries: int = 3

    _devices: list[Device] = field(default_factory=list)

    def __post_init__(self) -> None:
        host_missing = not self.host or self.host.isspace()
        name_missing = not self.name or self.name.isspace()
        if host_missing and name_missing:
            raise ValueError("At least one of host or name must be provided")
        if self.port is not None and not (0 <= self.port <= 65535):
            raise ValueError("Port must be between 0 and 65535")

    @property
    def description(self) -> str:
        """Human-readable identifier for this thread.

        Returns ``name`` if it is non-blank, otherwise falls back to ``url``.
        """
        return self.name if self.name and not self.name.isspace() else self.url

    @property
    def devices(self) -> list[Device]:
        """Snapshot of the devices registered to this thread."""
        return list(self._devices)

    @property
    def has_devices(self) -> bool:
        """``True`` if at least one device has been added to this thread."""
        return bool(self._devices)

    @property
    def url(self) -> str:
        """Connection URL for this thread.

        Returns a ``modbus://host:port`` URL when a host is configured.
        Falls back to ``name`` when no host is present.

        After a valid ``__post_init__``, the empty-string branch is unreachable
        because at least one of ``host`` or ``name`` is guaranteed to be
        non-blank.
        """
        if self.host and not self.host.isspace():
            return f"modbus://{self.host}:{self.port}"
        elif self.name and not self.name.isspace():
            return self.name
        else:
            assert False, "unreachable: __post_init__ guarantees host or name is present"

    def add_device(self, device: Device) -> None:
        """Register a device to be polled on this thread.

        Args:
            device: The device to add.
        """
        self._devices.append(device)

    def online(self, value: Literal[False] | asyncio.Future) -> None:
        """Set the online status of all devices registered to this thread.

        Pass a ``Future`` to bring devices online. The future is stored on each
        device; polling loops interpret it as a signal to begin or resume work.

        Pass ``False`` to take all devices offline, triggering a coordinated
        graceful shutdown of their polling loops.

        Passing ``True`` is explicitly forbidden — use a ``Future`` to bring
        devices online so that callers must provide a meaningful shutdown
        handle rather than a bare boolean.

        Args:
            value: A ``Future`` to bring devices online, or ``False`` to take
                them offline.

        Raises:
            ValueError: If ``value`` is ``True``.
        """
        if value is True:
            raise ValueError("Use a Future to bring devices online, not True")
        for device in self._devices:
            device.online = value

    def offline(self) -> None:
        """Take all devices registered to this thread offline.

        Equivalent to calling ``online(False)``. Triggers a coordinated
        graceful shutdown of each device's polling loop.
        """
        self.online(False)

    def reapply_sensor_overrides(self) -> None:
        """Reapply configuration overrides to every sensor on every device.

        Should be called after a configuration reload to ensure that any
        user-supplied register or sensor overrides are reflected in the
        current sensor state.
        """
        for device in self._devices:
            for sensor in device.sensors.values():
                sensor.apply_sensor_overrides(device.registers)


class ThreadConfigRegistry:
    """Registry of :class:`ThreadConfig` instances keyed by ``(host, port)``.

    Provides a find-or-create interface so that the rest of the application
    can request a config for a given Modbus endpoint without worrying about
    duplicates. Configs are cached for the lifetime of the registry.

    A module-level default instance is provided as :data:`thread_config_registry`.
    """

    def __init__(self) -> None:
        self._configs: dict[tuple[str, int], ThreadConfig] = {}

    def get_config(
        self,
        host: str,
        port: int,
        timeout: float = 1.0,
        retries: int = 3,
    ) -> ThreadConfig:
        """Return the config for ``(host, port)``, creating it if necessary.

        ``timeout`` and ``retries`` are applied only when a new config is
        created. Subsequent calls with the same ``(host, port)`` return the
        cached instance unchanged, regardless of the values passed.

        Args:
            host: IP address or hostname of the Modbus TCP target.
            port: TCP port of the Modbus target.
            timeout: Per-request timeout in seconds. Only used on first call
                for this ``(host, port)`` pair.
            retries: Number of retry attempts on failure. Only used on first
                call for this ``(host, port)`` pair.

        Returns:
            The :class:`ThreadConfig` for the given endpoint.
        """
        key = (host, port)
        if key not in self._configs:
            self._configs[key] = ThreadConfig(
                name=self._make_name(host, port),
                host=host,
                port=port,
                timeout=timeout,
                retries=retries,
            )
        return self._configs[key]

    def get_all(self) -> list[ThreadConfig]:
        """Return a snapshot of all registered configs.

        The returned list reflects the state of the registry at the time of
        the call; it will not update if new configs are added afterwards.
        """
        return list(self._configs.values())

    def clear(self) -> None:
        """Remove all configs from the registry.

        Primarily useful between tests or when reinitialising the application.
        Does not affect any :class:`ThreadConfig` instances already held by
        callers.
        """
        self._configs.clear()

    @staticmethod
    def _make_name(host: str, port: int) -> str:
        """Derive a display name from a Modbus host and port.

        IPv4 addresses are encoded as uppercase hex octets (e.g.
        ``192.168.1.100`` → ``C0A80164``). Hostnames are used as-is.
        Port 502 (the standard Modbus port) is omitted from the name;
        non-standard ports are appended in uppercase hex.

        Args:
            host: IP address or hostname of the Modbus target.
            port: TCP port of the Modbus target.

        Returns:
            A display name such as ``"Modbus@C0A80164"`` or
            ``"Modbus@C0A80164:1F96"``.
        """
        try:
            addr = ipaddress.IPv4Address(host)
            hostname = "".join(f"{octet:02X}" for octet in addr.packed)
        except ipaddress.AddressValueError:
            hostname = host
        return f"Modbus@{hostname}" if port == 502 else f"Modbus@{hostname}:{port:02X}"


#: Global default registry. Most application code should use this instance
#: rather than creating a private :class:`ThreadConfigRegistry`.
thread_config_registry = ThreadConfigRegistry()
