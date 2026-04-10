# Scripts

This directory contains various utility scripts for development, translation management, and build processes used in the `sigenergy2mqtt` project.

## Scripts Overview

*   **`build`**: Script for building the project.
*   **`dependencies`**: Script for managing project dependencies.
*   **`docker-test`**: Script to build and run the Docker container for testing.
*   **`release`**: Script used in the project's release process.
*   **`translations`**: Script to run the translation update and verification scripts.
*   **`update_en_translation.py`**: Python script responsible for updating the English translation base from code entities.
*   **`update_md` / `update_md.py`**: Scripts primarily used for updating markdown documentation such as `SENSORS.md` by analysing sensor definitions and fetching Modbus definitions.
*   **`verify_translations.py`**: Python script used to verify the consistency and correctness of the provided translations against the base English file.
*   **`yaml_to_env.py`**: Python script used to convert a `sigenergy2mqtt.yaml` configuration file into equivalent `SIGENERGY2MQTT_*` environment variables. This is useful for migrating to a Docker-only or environment-based configuration while maintaining the same settings.
