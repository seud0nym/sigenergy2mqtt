<!-- git log [since tag]..HEAD --oneline -->
# Changelog 

## [2026.6.25b1] - 2026.06.25

### Added

- Added support for forcing sensor values in Modbus test server
- Added exception handling for derived sensor updates
- Added warning log message for read-only mode
- Implemented StateStore and MonitorService clean functionality

### Changed

- Adjusted minimum sanity check value to PV Current/Voltage sensors to allow for small negative values (#207)
- Adjusted some more logging messages to reduce noise
- Refactored application of sensor overrides to enhance debug logging
- Increased default modbus auto-discovery timeout from 0.25 to 0.5 seconds
- Simplified initialisation and removed multiple redundant configuration reads
- Removed PV power sanity check zero minimum
- Clamped negative self-consumed power values to zero

### Fixed

- Fixed sequencing of pymodbus logging configuration for suppression of Modbus "ERROR: request ask for ... Skipping." log messages
- Fixed merging of sensor overrides to prevent over-writing

---

## [2026.6.21] - 2026-06-21

### Added

- Added metrics tracking for PVOutput uploads, errors, and skipped uploads, including localized metric labels
- Added configurable log level control for PVOutput upload payload logging
- Added support for publishing Docker images for alpha releases, including tag validation logic
- Added Docker image vulnerability scanning to the CI pipeline
- Added sanity-check limits for SystemTime and SystemTimeZone Modbus entities
- Added client identifiers to connection and disconnection logging for improved diagnostics

### Changed

- Standardized client disconnection handling across all client types
- Centralized Modbus validation logic and replaced Pydantic ValidationError usage with a custom ConfigurationError
- Upgraded Docker base image to Python 3.14 on Alpine 3.24
- Upgraded `pydantic-settings` from 2.14.1 to 2.14.2
- Upgraded `pymodbus` from 3.13.0 to 3.13.1
- Reduced application log verbosity and general log noise
- Improved device discovery logging detail
- Deferred PVOutput metrics reporting and skipped-upload logging until processing completion
- Standardized default log level naming to the technical value INFO across translations
- Updated release workflow to pull the latest changes before dependency checks
- Updated checkout action from v6 to v7

### Fixed

- Fixed PV generation sensor state_class values to prevent sanity-check validation issues (#200)
- Fixed ConfigurationError raised for valid Modbus configurations with auto-discovery cache (#203)
- PV Total Generation Today and PV Total Generation Yesterday were incorrectly marked as enabled by default in Home Assistant
- Corrected unsigned integer sanity-check range validation logic
- Corrected minimum delta validation for unsigned integer values
- Improved Modbus test server unsigned integer boundary handling
- Fixed double-counting of PVOutput upload errors on HTTP failures
- Reset PVOutput skipped status when payload changes are detected
- Corrected Japanese translations affected by an unintended replacement of the term "情報"
- Improved handling of timezone retrieval failures by defaulting to UTC
- Added handling for missing timezone offset values
- Refined timezone-related logging and error reporting
- Adjusted PVCurrentSensor minimum sane value to allow for measurement errors (or potential wiring issues?) (#203)

### Documentation

- Removed an incorrect reference to InfluxDB sensor registration from the MetricsService documentation
- Clarified PVOutput upload log level behaviour in the documentation

---

## [2026.6.14] - 2026-06-14

### Added

- Added Inverter and Plant estimated self-consumed power and daily energy sensors (thanks to @swainstm https://whrl.pl/RgV4Rd)
- Added health check for Docker to MonitorService and also published it to MQTT for other potential monitoring services
- Added default suppression of Modbus "ERROR: request ask for ... Skipping." log messages and added count of skipped messages to Metrics
- Added `SIGENERGY2MQTT_MODBUS_LOG_SKIPPED` configuration setting so that Modbus "ERROR: request ask for ... Skipping." log messages can be logged if required
- Added `SIGENERGY2MQTT_LOG_FMT` configuration setting and CLI argument to allow override of the log message format
- Added `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_NETWORKS` configuration setting and CLI argument to allow scanning of specific CIDR networks during auto-discovery
- Added `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_EXCLUDE` configuration setting to exclude devices from auto-discovery
- Added `SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_MAX_DEVICE_ID` configuration setting to limit the number of device IDs (default=10) that auto-discovery will scan
- Added new sensors defined in Modbus Protocol V2.9 (sensors may not be available depending on device/firmware):
  - New PSS and PID devices, and configuration/auto-discovery changes to support them (these are commercial/enterprise products, not residential)
  - DC Charger:
    - Discharging Current
    - Current Discharging Capacity
    - Current Discharging Duration
    - Total Charging Capacity
    - Total Discharging Capacity
    - Rated Charging Power
    - Rated Discharging Power
    - Max Charging Power Limit
    - Max Discharging Power Limit
  - Plant
    - PV Total Generation Today
    - PV Total Generation Yesterday
    - Average Cell Temperature
    - PCC Power Factor Adjustment Target Value (Grid Import) - Sigen PV M1-HYB series _only_
    - PCC Power Factor Adjustment Target Value (Grid Export) - Sigen PV M1-HYB series _only_
    - Grid Power Loss Lockout Alarm Clear
    - New ESS Preheating Device - Sigen PV M1-HYA/HYB series _only_

### Changed

- Auto-discovery now prioritizes statically configured Modbus hosts and unions newly discovered Modbus device IDs with existing configurations (fixes #191)
- Improved Modbus auto-discovery with detailed per-host device ID logging and fixed stale serial number tracking during re-scans
- Improved Modbus auto-discovery with quiet connection handling and sequential device scanning
- Increased Modbus auto-discovery timeout to 5 minutes
- Reimplemented Modbus test server using Pymodbus SimDevice and custom latency tracking to support device communication failures simulation
- Removed legacy add-sensor helpers and migrated to declared derived sources
- Created `AccumulationSensor` base class and refactored `ResettableAccumulationSensor` to inherit from it
- Enabled cross-device derived sensors pattern for delayed sensor binding
- Simplified `set_source_values` method signature across sensor classes
- Restored debug guard for monitor topic update tracking
- AC Chargers not connected to backup circuit caused startup to fail during a grid outage, so they are now skipped and will be retried when the grid restores
- Upgraded `pydantic-settings` to 2.14.1 
- Upgraded `requests` to 2.34.2
- Aligned zlib remediation with targeted package patch style in Dockerfile
- Derived sensors now declare source dependencies via constructor injection
- Implemented asynchronous configuration loading and auto-discovery support to improve startup performance
- When Power Factor is calculated because the Modbus interface provides an insane value, the log message will now only be visible if debug logging is enabled for that sensor
- Metrics reads now count physical reads rather than imputing the time to read a single register 
- Simplified PlantConsumedPower when using calculated consumption method to use new CrossDeviceDerivedSensor logic rather than relying on MQTT notifications
- Modified early detection of Modbus 0x02 ILLEGAL_DATA_ADDRESS exceptions to use a pre-scan approach rather than hard-coding known problematic registers
- SystemTime, StartupTime and ShutdownTime sensors now return correct date/time adjusted to the SystemTimeZone
- Default logging level is now INFO instead or WARNING
- MonitorService now longer starts if only doing a --clean execution
- As of Modbus Protocol V2.9, power dispatch sensors require Remote EMS to be enabled and the EMS to be in PCS Remote Control Mode for them to take effect. The affected sensors are:
  - Active Power Fixed Adjustment Target Value
  - Reactive Power Fixed Adjustment Target Value
  - Active Power Percentage Adjustment Target Value
  - Q/S Adjustment Target Value
  - Power Factor Adjustment Target Value
  - Phase A/B/C Active Power Fixed Adjustment Target Value
  - Phase A/B/C Reactive Power Fixed Adjustment Target Value
  - Phase A/B/C Active Power Percentage Adjustment Target Value
  - Phase A/B/C Q/S Fixed Adjustment Target Value


### Fixed

- Fixed incorrect popping of aliased device ID keys during discovery merge which led to device config loss
- Fixed the Phase Current and Phase Voltage sensors object_id when the inverter is a single-phase inverter
- Fixed `RuntimeWarning: coroutine was never awaited` warnings during testing
- Fixed `grid_status_initial_state` lacking a default value when configured via environment variable in Modbus test server
- Fixed the implementation of the `DerivedSensor` pattern
- Fixed various type errors and test failures related to `latest_raw_state` assignments and `set_source_values` refactoring
- Fixed deadlock when running auto-discovery (#177)
- Fixed min/max for Active/Reactive Power Fixed Adjustment Target Value sensors to use total Rated Active Power of attached inverters as the base for calculation
- Fixed invalid state when a TimestampSensor had a raw value of 0
- Fixed pymodbus logging namespace
- Fixed issue where auto-discovery would attempt to restore its cache from MQTT even if MQTT persistence was disabled
- Fixed handling of missing Modbus hosts during validation
- Fixed logic for store_false MQTT persistence redundancy flag in configuration parser
- Fixed sanity check errors on daily counter resets for TOTAL_INCREASING sensors

### Removed

- BREAKING CHANGE: Removed sensors which are sourced by direct access to third-party PV generation devices (e.g. Enphase) and related "smart-port" configuration in config files, environment variables and command line options

---

## [2026.4.16] - 2026-04-16

### Fixed

- Fixed the PVOutput extended fields (V7-V12) to allow zero values to be included in the payload

---

## [2026.4.15] - 2026-04-15

### Changed

- Modified the PVOutput extended fields (V7-V12) to allow up to 4 decimal places (even though the API Specification indicates that the values are integers) so that they can be used for tariff rates

---

## [2026.4.14] - 2026-04-14

### Added

- Created `scripts/yaml_to_env.py` helper script to convert YAML configuration files into equivalent environment variables
- Added `SIGENERGY2MQTT_HASS_SENSORS_ENABLED_BY_DEFAULT` environment variable for setting initial state of Home Assistant sensors
- Added `SIGENERGY2MQTT_SENSOR_OVERRIDES_JSON` environment variable to allow complex sensor overrides via JSON strings

### Changed

- Refactored state persistence (where transient states are saved to disk and restored after a restart) to use MQTT retained messages so that state can be restored even if the app is moved to another host after, for example, a hardware failure, or to migrate more easily from one installation method to another such as a Linux install to Docker, or Docker to Home Assistant add-on, without having to find and restore the state directory
- Allow PVOutput extended v7-v12 fields and the temperature source to be backed by Home Assistant sensors when running as a Home Assistant add-on, or by explicit MQTT topics (in addition to using sensor class names or entity ids for v7-v12) ([#168](https://github.com/seud0nym/sigenergy2mqtt/discussions/168))
- Reorganised unit tests into domain-specific packages
- Upgraded `pymodbus` from 3.12.1 to 3.13.0

### Fixed

- Use zero-length payload rather than None when deleting retained MQTT messages
- The reset controls for daily accumulation sensors in Home Assistant were incorrectly marked as enabled by default (only affects new or cleaned installations)

---

## [2026.4.4] - 2026-04-04

_NOTE: Includes all changes from the 2026.3.21bx beta releases_

### Changed

- Simplified Inverter naming to use unchanged model and serial number acquired via the Modbus registers
- Set sanity check min/max values for PV string current (0-50A) and voltage (0-1000V) sensors
- Expanded DeviceClass and StateClass enums with comprehensive Home Assistant standard definitions and validation logic
- Set PYTHONUNBUFFERED=1 environment variable in Dockerfile
- Standardised logging prefixes across devices and sensors using new log_identity field
- Consolidated low-volume unit test modules by domain
- Refactored sensor base tests into scoped modules
- Renamed unit test files to behaviour-centric naming
- Docker build test added to build script
- Dockerfile updated to use python:3.14-alpine3.23 and no-cache pip install across both native Docker and Home Assistant app, with mitigation for CVE-2026-27171
- Upgraded `requests` from 2.32.5 to 2.33.1

### Fixed

- Updated and renamed several environment variables in documentation, and added unit test to verify documentation coverage for constants. (#151)
- Return None instead of 0 when no state is available for derived sensors
- Fixed naming convention for multiple Modbus host installations

## [2026.3.21b2] - 2026-03-21

### Fixed

- Dockerfile fixed to build from Python 3.12/Alpine with pre-built wheels for pydantic-core

## [2026.3.21b1] - 2026-03-21

### Added

- Internationalisation framework supporting translations of device names, sensor names, sensor attributes, enumeration sensor options, and alarm descriptions
- Translations for German, Spanish, French, Italian, Dutch, Portuguese, Japanese, Korean, and Simplified Chinese (generated by Claude Opus 4.5 LLM)
- New configuration options to automatically publish all sensor data to InfluxDB (v1/2), with the ability to import historical `sigenergy2mqtt` sensor data from an existing InfluxDB `homeassistant` database
- New options to control the interval at which repeated state publishes are sent to MQTT
- New environment variable `SIGENERGY2MQTT_STATE_DIR` to allow the persistent state directory to be configured
- New metric for Modbus physical reads percentage
- New metrics for MQTT publish failures count and physical publish percentage
- New metrics for InfluxDB activity (when enabled)
- Ability to reset metrics counters
- Automatic effective restart when a firmware upgrade is detected, to ensure firmware and protocol version dependent configuration is correctly applied
- New option to use Sigenergy-Local-Modbus naming, gain and unit conventions for mapped Modbus sensors
- New `--validate` option to validate the configuration (including configuration file, command line options and environment variables) then exit

### Changed

- On firmware SPC113 and later, ESS Max Charging/Discharging and PV Max Power limits are now globally available; the validation override option added in 2026.1.20 is ignored for these firmware versions
- Improved Modbus read sanity checking to better target the requirements of specific sensors
- PVOutput output uploads are now only verified at end-of-day upload (previously also verified when the upload was unchanged from the previous upload)
- Refactored config module to use Pydantic to reduce complexity and improve testability
- Migrated Metrics to `threading.Lock`, resolving stalls caused by cross-event-loop lock sharing
- Metrics are now updated in a worker thread to remove potential delays
- Improved readability of alarm messages by removing the numeric prefix
- Trigger Modbus auto-discovery by default when no hosts are explicitly configured via command line, environment variables or YAML
- Improved operating system signal handling
- Upgraded `psutil` from 7.2.1 to 7.2.2
- Upgraded `pymodbus` from 3.11.4 to 3.12.1

### Deprecated

- Sensors which are sourced by direct access to third-party PV generation devices (e.g. Enphase) will be removed in a future release

### Removed

- HA discovery-only option from config file and ENV (only makes sense as a CLI option)

### Fixed

- MPPT Count was misspelt
- Per-sensor scan jitter that could defeat read-ahead optimisation
- Dockerfile fixed to reduce vulnerabilities

---

## [2026.1.20] - 2026-01-20

### Fixed
- Maximum PV string assertion for new inverter models (up to 36 strings).  
- Incorrect unit for Plant Max Apparent Power (kVA vs kVar).  
- Auto‑discovery edge‑case server assumption.  
- Premature exit when serial retrieval fails.  
- Updatable sensors not publishing after failed writes.  
- Metrics publishing even when disabled.  
- Derived sensors added despite protocol mismatch.  
- Compatibility issues with older firmware (#96).  
- UI minimum scan interval mismatch (#93).

### Changed
- Minimum Python version is now 3.12.  
- Default Consumed Power source is “Total Load” for protocol ≥ V2.8.  
- Added undocumented EMSWorkMode for VPP Scheduling.  
- Increased Modbus pre‑read sizes.  
- Refactored Sensor hierarchy, Metrics service, and common classes.  
- Test coverage increased to 90%+.

### Added
- Option to disable validation blocking ESS/PV limit changes when Remote EMS enabled (#78).  
- New Monitor service for debugging MQTT publishes.

---

## [2026.1.5] - 2026-01-05

### Fixed
- Child‑device sensor attributes not published when HA discovery disabled (#89).

### Changed
- Power Factor workaround now derives Active/Reactive Power from last published states.

---

## [2026.1.4] - 2026-01-04

### Changed
- Always publish sensor attributes, including name and unit (#89).  
- Accept empty configuration file.  
- Additional MQTT debugging.

### Added
- Option to select MQTT transport (TCP/WebSockets).

---

## [2026.1.3] - 2026-01-03

### Fixed
- Individual alarm topics not published (#89).  
- `publish-raw` override not recognized (#89).  
- Float validation accepted integers (#89).  
- Cleaned sample config; removed duplicates.  
- Minor test‑revealed bugs.

### Changed
- Minor integration/unit‑test support changes.  
- Removed unused classes.  
- Dependency upgrades: psutil 7.2.0→7.2.1, scapy 2.6.1→2.7.0, ruamel‑yaml 0.18.17→0.19.1.

---

## [2025.12.29] - 2025-12-29

### Fixed
- Un‑awaited coroutine breaking PVOutput uploads (#84).  
- Sanity check for sensors missing gain=1000 (#85).  
- Occasional variable‑scope error (#84).  
- Max Modbus registers per scan corrected to 124.

### Changed
- Removed Grid Phase Current/Voltage sensors from pre‑release V2.8.

---

## [2025.12.27] - 2025-12-27

### Fixed
- Write‑only controls not working (#83).  
- AC‑Charger Total Energy Consumed state class corrected (#83).

---

## [2025.12.25] - 2025-12-25

### Fixed
- Min/max validation issues.  
- HA float‑validation error (#81).  
- Battery sensor creation issues with Hybrid + PV inverter.

### Changed
- LVRT Negative Sequence Reactive Power Compensation Factor max updated (#80).  
- Upgraded psutil 7.1.3→7.2.0.  
- Removed deprecated CLI options/env variables.

---

## [2025.12.23] - 2025-12-23

### Fixed
- Removed device cleanup on upgrade (#77).  
- Prevented scan group task start when all sensors unpublishable (#79).  
- Handling systems without battery modules (#80).

### Changed
- Further Modbus pre‑read optimizations.  
- Removed unnecessary properties.

### Added
- Option to replace sliders with number inputs in Home Assistant.

---

## [2025.12.20] - 2025-12-20

### Fixed
- DC‑Charger power missing from consumption (#74).  
- UnboundLocalError when second inverter detected.

### Changed
- Handling of ILLEGAL DATA ADDRESS sensors.  
- Upgraded ruamel‑yaml 0.18.16→0.18.17.

### Added
- Option to use new V2.8 Total/General Load Power sensors.  
- Cache‑hit percentage metric.

---

## [2025.12.18] - 2025-12-18

### Fixed
- Switch sensors not toggling.  
- Register count calculation for non‑contiguous reads.

---

## [2025.12.16] - 2025-12-16

### Fixed
- Non‑contiguous multi‑register scan performance.  
- Write performance and post‑write read/publish.  
- Missing PVOutput data (#65).  
- PVOutput period sums incorrect.  
- Incorrect decimals on max values for several Plant sensors.  
- Incorrect DC‑Charger entity IDs.  
- EMS‑mode‑dependent controls in HA.  
- Independent Phase Power Control UI logic.

### Changed
- All sensors now protocol‑version aware.  
- Write operations validated before commit.  
- Upgraded pymodbus 3.11.3→3.11.4.

### Added
- Full Modbus Protocol V2.8 support.  
- Support for new inverter models with up to 36 PV strings.

---

## [2025.11.23] - 2025-11-23

### Fixed
- Multiple Modbus decoding errors.

### Added
- Options for selecting PVOutput voltage source (#61).

---

## [2025.11.19] - 2025-11-19

### Fixed
- Invalid Power Factor values now recalculated.

### Added
- Time‑period‑based PVOutput uploads.

---

## [2025.11.11‑1] - 2025-11-11

### Fixed
- Decimal handling for PVOutput extended data (#59).

---

## [2025.11.11] - 2025-11-11

### Fixed
- Missing device class for enumerations.  
- Missing data type in derived sensors (#59).

### Changed
- PVOutput end‑of‑day verification improvements.  
- Upgraded psutil and ruamel‑yaml.

### Added
- New timeout/retry configuration options.

---

## [2025.10.21] - 2025-10-21

### Fixed
- PVOutput donation detection.  
- PVOutput error handling.  
- AC/DC charger handling during grid outage.

### Changed
- Minimum scan interval now 1s.  
- PVOutput uploads now use power over interval.  
- Entity ID allowed for PVOutput extended data.  
- Added NET_OF_BATTERY option.  
- Upgraded psutil.

### Added
- Battery data uploads for PVOutput donors.  
- Raw data publishing option.

---

## [2025.10.15] - 2025-10-15

### Fixed
- Graceful exit when auto‑discovery fails (#49).

### Changed
- Minimum scan interval now 1s.

### Added
- MQTT keepalive override (#47).

---

## [2025.10.14] - 2025-10-14

### Added
- Modbus timeout/retry overrides (#47).

---

## [2025.10.13] - 2025-10-13

### Fixed
- MQTT Client ID generation in low‑entropy environments (#47).

---

## [2025.10.12] - 2025-10-12

### Fixed
- Missing platform prefix in HA auto‑discovery (#44/#45).

### Changed
- PVOutput service refactoring.

---

## [2025.10.5] - 2025-10-05

### Known Issues
- Invalid inverter Power Factor values outside 0.0–1.0 ignored (warnings only).  
- PVOutput end‑of‑day uploads sometimes fail silently.

### Fixed
- Correct state class for Total Consumption on Smart Load ports (#39).  
- HA MQTT auto‑discovery now uses `default_entity_id`.

### Changed
- Reworked PVOutput upload logic (scheduling, drift, enabling exports/imports, mid‑day visibility).  
- Auto‑discovery improvements (latency preference, duplicate serial filtering).  
- Retry MQTT connection 3× at 30‑second intervals.  
- Upgraded `pymodbus` 3.11.2 → 3.11.3.

### Added
- Modbus packet tracing when debugging enabled.

---

## [2025.9.24] - 2025-09-24

### Fixed
- Auto‑discovery duplication when Ethernet + Wi‑Fi connected (#36).  
- AC/DC Charger Start/Stop reversed.  
- MQTT subscriptions not renewed after reconnection.  
- PVOutput status uploads only sent when sensors update.

### Added
- PVOutput extended data (up to six numeric classes).  
- Verification + retry of daily uploads.

### Changed
- Refactored Phase sensors, locking strategy, Modbus handling.  
- Added sanity checks to power factor + temperature sensors.  
- Upgraded builder + dependencies (`pymodbus`, `psutil`).  
- Dependabot bumps (#32, #33, #35).  
- Development updates (#37).

---

## [2025.8.31] - 2025-08-31

### Fixed
- Resetting calculated daily sensors on restart.  
- Incorrect AC/DC Charger button names.

### Changed
- Upgraded `requests`, `ruamel.yaml`.  
- Alarm sensor value length capped at 255 chars.  
- `.yaml` files excluded from stale cleanup.

---

## [2025.8.17] - 2025-08-17

### Added
- Auto‑discovery of Sigenergy hosts + device IDs.  
- Option to upload grid imports instead of consumption.

### Changed
- Upgraded `pymodbus` to 3.11.1.

---

## [2025.8.15] - 2025-08-15

### Fixed
- AssertionError when creating AC Charger device.

---

## [2025.8.12] - 2025-08-12

### Added
- Support for self‑signed MQTT TLS certificates (#21).

---

## [2025.8.11] - 2025-08-11

### Fixed
- Smart Load Power sensors had incorrect units + device class (#20).

### Changed
- Sensor attributes include derived‑source metadata.  
- Consumed Power includes AC/DC Charger output.  
- Alarms + charger power refresh at realtime interval.  
- Upgraded to `pymodbus` 3.11.0.

### Added
- MQTT TLS/SSL support (#19).

---

## [2025.8.5] - 2025-08-05

### Fixed
- PVOutput iteration errors (#16).  
- Infinite loop on PVOutput error (#16).  
- Incorrect device/state class for Reactive Power Adjustment Feedback.  
- Event‑loop binding error during metrics publish.  
- MQTT connection failures now logged.

### Changed
- Improved scan interval accuracy.  
- Improved exception logging.  
- PVOutput warnings limited to once per hour.

---

## [2025.8.2‑1] - 2025-08-02

### Fixed
- CLI option handling bug introduced in 2025.8.2 (#15).

---

## [2025.8.2] - 2025-08-02

### Fixed
- Max Charge/Discharge/PV Max Power limits unavailable with Remote EMS (#12).  
- Incorrect publishing of unpublishable sensors.  
- Warning logs for `None` state files.  
- Incorrect Modbus Protocol version in HA.  
- Inverter hardware version not updating.  
- Alarm list workaround.  
- Modbus connection failure handling improved.

### Changed
- Upgraded dependencies (`paho-mqtt`, `pymodbus`, `requests`, `ruamel.yaml`).  
- Cleaned debug‑only messages.  
- Removed stale state files.

### Added
- Modbus read/write metrics.  
- Online/offline status topic.  
- New inverter sensors previously returning ILLEGAL DATA ADDRESS.  
- Update topic included in updatable sensor attributes.  
- Warning if PVOutput source topics stale.

### Removed
- Deprecated PVOutput interval options.  
- Charger statistics when no chargers defined.

---

## [2025.7.26‑1] - 2025-07-26

### Fixed
- Docker build.

---

## [2025.7.26] - 2025-07-26

### Fixed
- Alarm values returned as list.  
- systemd offline behaviour.  
- Warning logs for `None` state files.  
- Removed stale persistent state files.  
- Incorrect Modbus protocol version in Plant Device Info.

### Changed
- Simplified MQTT topic structure option.  
- Upgraded paho‑mqtt, pymodbus, requests, ruamel.yaml.

---

## [2025.7.20] - 2025-07-20

### Fixed
- Write operation failures (#9).

### Added
- Average PV string voltage to PVOutput.  
- Optional temperature upload.

---

## [2025.7.13‑1] - 2025-07-13

### Fixed
- Daily energy sensors disabled at midnight.

---

## [2025.7.13] - 2025-07-13

### Fixed
- PVOutput peak‑power reporting.  
- PVOutput values off by factor of 10.

---

## [2025.7.10] - 2025-07-10

### Fixed
- Slider stepping.  
- Sanity checks for power/energy sensors.  
- Negative consumption handling.  
- Modbus protocol updates (V2.6, V2.7).  
- Many new Modbus sensors.

---

## [2025.6.14] - 2025-06-14

### Added
- EMS Work Mode “Time‑Based Control”.

### Fixed
- Inverter Device Info not updating.  
- Spurious PVOutput peak values.  
- Empty MQTT payload handling (#4).

---

## [2025.6.11] - 2025-06-11

### Added
- Scan interval override options.

### Fixed
- PVOutput peak‑power scheduling.

---

## [2025.6.5] - 2025-06-05

### Fixed
- PVOutput daily peak power loss.  
- Modbus locking improvements.

---

## [2025.6.1] - 2025-06-01

### Fixed
- PV string power calculation (#2).  
- Remote EMS availability logic.  
- Daily accumulation resets.  
- Enphase Smart‑Port daily PV energy.  
- Negative lifetime statistics (#2).

### Added
- Remote‑EMS sensor hiding.  
- Per‑sensor debug logging.

---

## [2025.5.30‑1] - 2025-05-30

### Fixed
- Fix for failed start on 3‑phase installations (#3).

---

## [2025.5.30] - 2025-05-30

### Fixed
- Multiple Modbus write, sensor applicability, precision, PVOutput config, CLI/env handling, and exit‑path bugs.  
- Logging level corrections (#2).

### Added
- Sanity‑checking limits for Modbus values.  
- Sanity check on GridSensorActivePower (±100 kW) (#1).

---

## [2025.5.24] - 2025-05-24

### Changed
- Daily Peak PV Power auto‑update at 21:45.  
- Minor bug fixes and testing improvements.  
- Improved debugging of configuration overrides.

### Added
- Documentation of MQTT topics.

---

## [2025.5.18] - 2025-05-18

### Fixed
- Device sensor publishable overrides.  
- AC‑Charger initialisation.

### Added
- `--modbus-read-only` and related environment variables.

---

## [2025.5.16‑1] - 2025-05-16
### Fixed
- Validation issues.

---

## [2025.5.16] - 2025-05-16

### Fixed
- MQTT config processed twice.

---

## [2025.5.15] - 2025-05-15

### Fixed
- Handling of overrides producing lists.

### Changed
- Added override key to exception messages.

---

## [2025.5.13] - 2025-05-13

### Fixed
- Publishing issues.

---

## [2025.5.12] - 2025-05-12

### Fixed
- Various bug fixes.

### Added
- Environment variable configuration.  
- Python & Docker build publishing.

---

## [2025.5.10] - 2025-05-11

### Note
- Installation now via `pip`.

### Bug Fixes
- Task sleep interval.  
- Smart‑port CLI option.  
- AC Charger handling.  
- MQTT initial connection handling.  
- Config filename whitespace.  
- Retry‑interval minimum.

### Improvements
- Environment variable support.  
- Modbus Protocol version shown in Plant.

---

## [2025.5.8] - 2025-05-08

### Fixed
- Retry‑on‑failure logic.

---

## [2025.5.7] - 2025-05-07

- First public release

---
