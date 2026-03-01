import logging
from typing import TYPE_CHECKING

from sigenergy2mqtt.common import Constants, InputType
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import ModbusSensorMixin, ReadableSensorMixin, ReservedSensor

if TYPE_CHECKING:
    from .device import Device


class ReadableSensorGroup(list[ReadableSensorMixin | ModbusSensorMixin]):
    """A typed list of readable sensors that tracks Modbus address range metadata.

    For Modbus sensor groups, maintains the contiguous address range
    (first_address, last_address), the shared device_address, and the shared
    input_type as sensors are appended. This metadata is used by publish_updates
    to perform a single read-ahead register fetch covering all sensors in the
    group, rather than individual per-sensor reads.

    All ModbusSensorMixin instances in a group must share the same device_address
    and input_type; mixing them raises ValueError. Non-Modbus sensors may be
    grouped together but cannot be mixed with Modbus sensors in the same group.
    """

    def __init__(self, *sensors: ReadableSensorMixin | ModbusSensorMixin):
        """Initialise the group and append each provided sensor via the overridden append().

        Args:
            *sensors: Zero or more readable sensors to include in the group.
                      All constraints enforced by append() apply at construction time.
        """
        super().__init__()
        self.first_address: int = -1
        self.last_address: int = -1
        self.device_address: int = -1
        self.input_type: InputType = InputType.NONE
        for sensor in sensors:
            self.append(sensor)

    @property
    def register_count(self) -> int:
        """The number of Modbus registers spanning first_address to last_address inclusive.

        Returns -1 if no publishable Modbus sensors have been appended yet.
        """
        if self.first_address != -1 and self.last_address != -1:
            return self.last_address - self.first_address + 1
        else:
            return -1

    def append(self, sensor: ReadableSensorMixin | ModbusSensorMixin):
        """Append a sensor and update Modbus address range metadata if applicable.

        For publishable ModbusSensorMixin instances, updates first_address and
        last_address to ensure they span the new sensor's register range, and
        validates that device_address and input_type are consistent with existing
        members.

        Args:
            sensor: The sensor to append. Must be a ReadableSensorMixin instance.

        Raises:
            ValueError: If sensor is not a ReadableSensorMixin.
            ValueError: If sensor is a ModbusSensorMixin with a different device_address
                        than existing Modbus sensors in this group.
            ValueError: If sensor is a ModbusSensorMixin with a different input_type
                        than existing Modbus sensors in this group.
            ValueError: If sensor is a non-Modbus sensor being added to a group that
                        already contains ModbusSensorMixin instances, or vice versa.
        """
        if not isinstance(sensor, ReadableSensorMixin):
            raise ValueError(f"Only ReadableSensorMixin instances can be added to ReadableSensorGroup, got {type(sensor)}")
        if isinstance(sensor, ModbusSensorMixin):
            if sensor.publishable:
                if self.first_address == -1 or sensor.address < self.first_address:
                    self.first_address = sensor.address
                if self.last_address == -1 or (sensor.address + sensor.count - 1) > self.last_address:
                    self.last_address = sensor.address + sensor.count - 1
                if self.device_address == -1:
                    self.device_address = sensor.device_address
                elif self.device_address != sensor.device_address:
                    raise ValueError(f"All ModbusSensorMixin instances in a ReadableSensorGroup must have the same device address, expected {self.device_address}, got {sensor.device_address}")
                if self.input_type == InputType.NONE:
                    self.input_type = sensor.input_type
                elif self.input_type != sensor.input_type:
                    raise ValueError(f"All ModbusSensorMixin instances in a ReadableSensorGroup must have the same input type, expected {self.input_type}, got {sensor.input_type}")
        elif any(s for s in self if isinstance(s, ModbusSensorMixin)):
            raise ValueError("Cannot add non-ModbusSensorMixin to a ReadableSensorGroup that already contains ModbusSensorMixin instances")
        return super().append(sensor)


def create_sensor_scan_groups(device: "Device") -> dict[str, list[ReadableSensorMixin]]:
    """Build optimised Modbus scan groups for all readable sensors on a device and its children.

    Groups are constructed to minimise the number of Modbus read requests:
    sensors with contiguous register addresses on the same device and of the
    same input type are batched into a single group, subject to the
    Constants.MAX_MODBUS_REGISTERS_PER_REQUEST limit. If active_config.modbus[plant_index].
    disable_chunking is True, each sensor gets its own group.

    Named groups (registered via Device._add_read_sensor with a group key) are always
    kept intact and take priority. Auto-generated groups use the key format
    "{device_address:03d}_{first_address:05d}".

    ReservedSensors at the start of a new group are skipped (they cannot lead
    a group). ReservedSensors trailing a group are removed in post-processing.
    Empty groups are deleted.

    Non-Modbus readable sensors are collected into a single "non_modbus_sensors"
    group at the end.

    Args:
        device: The root device whose sensors (and children's sensors) are to be grouped.

    Returns:
        A dict mapping group name to list of ReadableSensorMixin instances.
    """
    all_child_sensors = device.get_all_sensors(search_children=True)
    combined_sensors: dict[str, ReadableSensorMixin] = {uid: s for uid, s in all_child_sensors.items() if isinstance(s, ReadableSensorMixin)}

    # Recursively collect named group sensors
    combined_groups: dict[str, list[ReadableSensorMixin]] = {}

    def collect_groups(d: "Device") -> None:
        for group, sensor_list in d.group_sensors.items():
            if group not in combined_groups:
                combined_groups[group] = []
            combined_groups[group].extend(sensor_list)
        for child in d.children:
            collect_groups(child)

    collect_groups(device)

    named_group_sensors: dict[int, ModbusSensorMixin] = {  # Multiple sensors with the same address are not possible and would in any event be detected in the Sensor constructor
        s.address: s for sublist in combined_groups.values() for s in sublist if isinstance(s, ModbusSensorMixin)
    }
    first_address: int = -1
    next_address: int = -1
    device_address: int = -1
    input_type: InputType = InputType.NONE
    group_name: str | None = None

    # Create Modbus sensor scan groups for sensors that are not already in a named group.
    # Grouped by device_address and contiguous addresses only (scan_interval handled per-sensor in publish_updates).
    all_grouped = [gs for lst in combined_groups.values() for gs in lst]
    for sensor in sorted(
        [s for s in combined_sensors.values() if isinstance(s, ModbusSensorMixin) and s not in all_grouped],
        key=lambda s: (s.device_address, s.address),
    ):
        if (  # Conditions for creating a new sensor scan group
            active_config.modbus[device.plant_index].disable_chunking  # If chunking is disabled, always create a new group
            or group_name is None  # First sensor
            or first_address == -1  # Safety check for uninitialized first_address
            or sensor.device_address != device_address  # Device address changed
            or sensor.input_type != input_type  # Input type changed
            or sensor.address > next_address  # Non-contiguous addresses
            or (next_address - first_address + sensor.count) > Constants.MAX_MODBUS_REGISTERS_PER_REQUEST  # Modbus request size exceeded
        ):
            # Don't start a group with a ReservedSensor
            if isinstance(sensor, ReservedSensor):
                continue

            group_name = f"{sensor.device_address:03d}_{sensor.address:05d}"
            combined_groups[group_name] = []
            first_address = sensor.address

        # If we skipped creating a group (because of ReservedSensor), we can't append
        if group_name is not None and first_address != -1:  # Validate first_address
            combined_groups[group_name].append(sensor)

        next_address = sensor.address + sensor.count
        while next_address in named_group_sensors:  # Include any named group sensors that fall within the range
            if first_address == -1 or (next_address - first_address + named_group_sensors[next_address].count) > Constants.MAX_MODBUS_REGISTERS_PER_REQUEST:
                break
            else:
                next_address += named_group_sensors[next_address].count
        device_address = sensor.device_address
        input_type = sensor.input_type

    # Post-process groups to remove trailing ReservedSensors and empty groups
    for g_name in list(combined_groups.keys()):
        group = combined_groups[g_name]
        while group and isinstance(group[-1], ReservedSensor):
            group.pop()
        if not group:
            del combined_groups[g_name]

    # Create a single scan group for remaining non-Modbus readable sensors
    non_modbus_sensors = [s for s in combined_sensors.values() if not isinstance(s, ModbusSensorMixin) and isinstance(s, ReadableSensorMixin) and s not in all_grouped]
    if non_modbus_sensors:
        combined_groups["non_modbus_sensors"] = non_modbus_sensors

    sensors_count = len([s.unique_id for lst in combined_groups.values() for s in lst])
    groups_count = len(combined_groups)
    logging.info(f"{device.name} created {groups_count} Sensor Scan Group{'s' if groups_count != 1 else ''} containing {sensors_count} sensor{'s' if sensors_count != 1 else ''}")

    return combined_groups
