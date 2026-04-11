# Tests

This directory contains all the testing code for the `sigenergy2mqtt` project, categorized into different testing approaches.

## Directory Structure

*   **/integration**: Contains integration tests to verify how different modules interact with each other and external systems.
*   **/unit**: Contains unit tests to verify the behavior of individual components, functions, and classes in isolation.
    * The unit test suite is divided into domain-specific subdirectories that mirror the `sigenergy2mqtt` codebase structure (e.g., `config/`, `devices/`, `sensors/`). This allows for targeted test execution (`pytest tests/unit/<domain>/`) and improves discoverability.
*   **/utils**: Contains shared utilities, fixtures, and helpers used across the test suites. See [`utils/README.md`](utils/README.md) for more details.

## Files

*   **`conftest.py`**: Shared pytest fixtures and configurations for the test suites.

## Test File Organization Guidelines

To keep the test suite maintainable, prefer these thresholds and grouping rules:

* **Soft limit:** keep test files at or below ~400 lines when practical.
* **Hard limit:** split is required once a file grows beyond ~700 lines.
* **One functional axis per file:** organize by concern (for example: type handling, bounds/validation, serialization/discovery, or integration behavior) instead of accumulating unrelated branches in one module.
* **Consolidate tiny satellites:** if a domain has many very small test files, merge related low-volume tests into a scoped sibling to avoid excessive fragmentation.

When splitting a large file, prefer sibling filenames that reflect the concern, such as `test_sensors_base_extended_validation.py` or `test_sensors_base_extended_publish_and_discovery.py`.

## Unit Test Naming Convention (`tests/unit/`)

Use behavior-centric filenames that describe the primary scenario under test (for example, config validation, device offline handling, MQTT topic generation). Avoid meta labels like `coverage`, `booster`, `extended`, `misc`, and `more` in new filenames.

| Old pattern | New pattern |
| --- | --- |
| `test_*_coverage*.py` | `test_*_<behavior>.py` |
| `test_*_booster*.py` | `test_*_<behavior>.py` |
| `test_*_extended*.py` | `test_*_<behavior>.py` |
| `test_*_misc*.py` | `test_*_<behavior>.py` |
| `test_*_more.py` | `test_*_<behavior>.py` |

Examples from this repo after consolidation/rename:

| Previous filename | Behavior-centric filename |
| --- | --- |
| `test_config_coverage_booster.py` | `test_config_environment_overrides.py` |
| `test_threading_coverage.py` | `test_threading_signal_and_shutdown.py` |
| `test_sensors_base_extended_validation.py` | `test_sensors_base_validation_rules.py` |
| `test_coverage_booster_misc.py` | `test_protocol_and_main_helpers.py` |
| `test_device_more.py` | `test_device_runtime_behaviors.py` |
