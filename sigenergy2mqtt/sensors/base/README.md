# Base sensor hierarchy

This package contains the reusable sensor model used by `sigenergy2mqtt`.  A
sensor is a Home Assistant discovery dictionary as well as an object that owns
state history, MQTT topics, validation, availability, and publishing behaviour.
The hierarchy deliberately separates **entity behaviour** from the transport
that supplies or accepts values.

## Hierarchy

```text
Sensor (abstract; discovery, state, publishing, overrides)
├── AvailabilityMixin (adds MQTT availability configuration)
├── DerivedSensor (calculated state)
│   └── CrossDeviceDerivedSensor
├── ReadOnlySensor (Modbus polling)
│   ├── ReservedSensor
│   ├── TimestampSensor
│   ├── AlarmSensor
│   │   ├── Alarm1Sensor … Alarm5Sensor
│   │   └── AlarmCombinedSensor
│   ├── RunningStateSensor
│   └── AccumulationSensor
│       ├── ResettableAccumulationSensor
│       ├── EnergyLifetimeAccumulationSensor
│       └── EnergyDailyAccumulationSensor
│           └── SimpleEnergyDailyAccumulationSensor
├── WriteOnlySensor (Modbus command/button)
└── ReadWriteSensor (Modbus polling + commands)
    ├── NumericSensor
    │   └── ThreePhaseAdjustmentTargetValue
    ├── SelectSensor
    └── SwitchSensor
```

`ReadOnlySensor`, `WriteOnlySensor`, and `ReadWriteSensor` retain their public
constructors and current Modbus behaviour.  They are composed from the mixins
below; applications normally use these concrete classes for register-backed
entities.

## Foundation and transport mixins

* `SensorDebuggingMixin` supplies the `debug_logging` option.
* `TypedSensorMixin` validates and stores a `ModbusDataType`; use it only for
  Modbus-backed sensors.
* `ReadableSensorMixin` adds and validates a polling `scan_interval`.  It does
  not itself read Modbus.
* `ModbusSensorMixin` supplies register identity, register-response handling,
  and Sigenergy Local Modbus naming.  It should be used only when a sensor has
  a Modbus address.
* `WriteableSensorMixin` is transport independent.  It creates the command
  topic, validates the command through `value_is_valid`, and dispatches it to
  the required `_write_value` coroutine.  It does **not** require a Modbus
  client, address, data type, or scan interval.
* `ModbusWriteableSensorMixin` combines `WriteableSensorMixin`,
  `TypedSensorMixin`, and `ModbusSensorMixin` and implements `_write_value`
  using Modbus register writes.  It powers the existing write-only and
  read-write classes.
* `ObservableMixin` defines the interface for sensors which observe MQTT
  changes; `PVPowerSensor` is its current implementation.
* `UnpublishResetSensorMixin` removes obsolete reset entities.

## Writeable entity presentation mixins

The following mixins add the Home Assistant platform shape and value conversion
without choosing a transport:

* `NumericSensorMixin` configures a `number` entity, its step and optional
  minimum/maximum values, and converts a command through the sensor gain.
* `SelectSensorMixin` configures a `select` entity from `options` and converts
  an option name to its index.
* `SwitchSensorMixin` configures a binary `switch` entity and validates `0` or
  `1` commands.

They mirror the command-facing behaviour of `NumericSensor`, `SelectSensor`,
and `SwitchSensor`, and each inherits `WriteableSensorMixin`. Subclass the
appropriate presentation mixin directly when the backing service is not Modbus.

## Creating a non-Modbus writeable sensor

Implement `_write_value` for the target transport and `_update_internal_state`
required by `Sensor`.  A write-only service-backed numeric entity can be
created without an address, input type, Modbus data type, or client:

```python
class ApiSetpoint(NumericSensorMixin):
    async def _update_internal_state(self, **kwargs):
        return False

    async def _write_value(self, modbus_client, mqtt_client, value, source, handler):
        await api.set_setpoint(value)
        return True
```

Instantiate it with the normal `Sensor` keyword arguments (`name`, `unique_id`,
`object_id`, `unit`, `device_class`, `state_class`, `icon`, `gain`,
`precision`, and `protocol_version`) plus `minimum`/`maximum`.  Call
`configure_mqtt_topics()` before routing commands to `set_value()`.  The
`modbus_client` argument remains in the command method signature for a common
MQTT handler interface and may be `None` for non-Modbus sensors.

For a select or switch, replace `NumericSensorMixin` with `SelectSensorMixin`
(and provide `options`) or `SwitchSensorMixin`.  A custom transport can also
subclass `WriteableSensorMixin` directly when it needs no number/select/switch
presentation behaviour.
