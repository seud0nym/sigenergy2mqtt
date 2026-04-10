# tests/utils

This directory contains various utility scripts, configuration files, and tools used for unit and integration testing of `sigenergy2mqtt`.

## Files

### Modbus Simulation & Validation
- **`modbus_sensors.py`**: A testing utility that provides a `DummyModbusClient` which simulates Modbus register reads from in-memory data. It also contains `get_sensor_instances()`, which instantiates the entire sensor graph to aid in detecting overlapping registers or validation gaps across all sensor definitions.
- **`modbus_test_server.py`**: An async Modbus TCP test server that runs a `pymodbus` server. It provides simulated Modbus registries populated either with synthesized random values within acceptable bounds or by subscribing to live MQTT updates, allowing integration tests against a mock Sigenergy device.

### Docker Testing
- **`docker-compose.yaml`**: A Docker Compose configuration file that creates a test environment with an `emqx` MQTT broker and a `sigenergy2mqtt` instance.

### Other Utilities
- **`launch.py`**: A local test entrypoint script that simply executes the `sigenergy2mqtt.__main__` module, allowing developers to manually launch and debug the application from their IDE or terminal.
- **`__init__.py`**: Python package initialisation file.
