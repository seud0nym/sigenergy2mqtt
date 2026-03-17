# Installation

* [Home Assistant](homeassistant/README.md)
* [Docker](docker/README.md)
* [Linux](linux/README.md)

# Configuration

* [Combined reference for CLI flags, environment variables, and YAML configuration keys.](configuration/README.md)

When parsing configuration options, `sigenergy2mqtt` looks at the configuration sources in the following order:

1. [Configuration File](configuration/FILE.md)
1. [Environment Variables](configuration/ENV.md)
1. [Command Line Options](configuration/CLI.md)

This means, for example, that the options specified in the configuration file can be overridden by environment variables and command line options.

# MQTT Publish and Subscribe Topics

The topics that are published and subscribed to by `sigenergy2mqtt` can be found [here](sensors/TOPICS.md).

# Sensor Conversion Map for [TypQxQ Sigenergy-Local-Modbus](https://github.com/TypQxQ/Sigenergy-Local-Modbus)

The list of the Modbus sensors published by the <a href='https://github.com/TypQxQ/Sigenergy-Local-Modbus'>TypQxQ Sigenergy-Local-Modbus</a> HACS integration,
and the corresponding sensor in `sigenergy2mqtt` can be found [here](sensors/SENSORS.md).
