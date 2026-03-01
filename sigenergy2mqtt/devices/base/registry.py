from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .device import Device


class DeviceRegistry:
    """Process-wide registry mapping plant indices to their associated Device instances.

    Provides a simple class-level store used during device construction and
    teardown. All access is through class methods; the registry is not intended
    to be instantiated.
    """

    # Use defaultdict to automatically handle missing keys without requiring
    # an existence check before appending. clear() reassigns this attribute
    # (rather than calling .clear() on it) to guarantee the type invariant is
    # restored even if external code has replaced it with a plain dict.
    _devices: dict[int, list["Device"]] = defaultdict(list)

    @classmethod
    def add(cls, plant_index: int, device: "Device") -> None:
        """Register a device under the given plant index.

        Called automatically from Device.__init__; callers should not need to
        invoke this directly.

        Args:
            plant_index: The plant index the device belongs to.
            device:      The Device instance to register.
        """
        cls._devices[plant_index].append(device)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered devices and reset the registry to a clean state.

        Reassigns _devices to a fresh defaultdict(list) to ensure the type
        invariant holds regardless of any prior external assignments to the
        class attribute.
        """
        cls._devices = defaultdict(list)

    @classmethod
    def get(cls, plant_index: int) -> list["Device"]:
        """Return a copy of the device list for the given plant index.

        Args:
            plant_index: The plant index to query.

        Returns:
            A new list containing the Device instances registered under
            plant_index, or an empty list if the plant index is not known.
        """
        return list(cls._devices.get(plant_index, []))
