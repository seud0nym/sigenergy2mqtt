# Changelog

## **[2026.1.20]**
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

## **[2026.1.5]**
### Fixed
- Child‑device sensor attributes not published when HA discovery disabled (#89).

### Changed
- Power Factor workaround now derives Active/Reactive Power from last published states.

---

## **[2026.1.4]**
### Changed
- Always publish sensor attributes, including name and unit (#89).  
- Accept empty configuration file.  
- Additional MQTT debugging.

### Added
- Option to select MQTT transport (TCP/WebSockets).

---

## **[2026.1.3]**
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

## **[2025.12.29]**
### Fixed
- Un‑awaited coroutine breaking PVOutput uploads (#84).  
- Sanity check for sensors missing gain=1000 (#85).  
- Occasional variable‑scope error (#84).  
- Max Modbus registers per scan corrected to 124.

### Changed
- Removed Grid Phase Current/Voltage sensors from pre‑release V2.8.

---

## **[2025.12.27]**
### Fixed
- Write‑only controls not working (#83).  
- AC‑Charger Total Energy Consumed state class corrected (#83).

---

## **[2025.12.25]**
### Fixed
- Min/max validation issues.  
- HA float‑validation error (#81).  
- Battery sensor creation issues with Hybrid + PV inverter.

### Changed
- LVRT Negative Sequence Reactive Power Compensation Factor max updated (#80).  
- Upgraded psutil 7.1.3→7.2.0.  
- Removed deprecated CLI options/env vars.

---

## **[2025.12.23]**
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

## **[2025.12.20]**
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

## **[2025.12.18]**
### Fixed
- Switch sensors not toggling.  
- Register count calculation for non‑contiguous reads.

---

## **[2025.12.16]**
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

## **[2025.11.23]**
### Fixed
- Multiple Modbus decoding errors.

### Added
- Options for selecting PVOutput voltage source (#61).

---

## **[2025.11.19]**
### Fixed
- Invalid Power Factor values now recalculated.

### Added
- Time‑period‑based PVOutput uploads.

---

## **[2025.11.11‑1]**
### Fixed
- Decimal handling for PVOutput extended data (#59).

---

## **[2025.11.11]**
### Fixed
- Missing device class for enumerations.  
- Missing data type in derived sensors (#59).

### Changed
- PVOutput end‑of‑day verification improvements.  
- Upgraded psutil and ruamel‑yaml.

### Added
- New timeout/retry configuration options.

---

## **[2025.10.21]**
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

## **[2025.10.15]**
### Fixed
- Graceful exit when auto‑discovery fails (#49).

### Changed
- Minimum scan interval now 1s.

### Added
- MQTT keepalive override (#47).

---

## **[2025.10.14]**
### Added
- Modbus timeout/retry overrides (#47).

---

## **[2025.10.13]**
### Fixed
- MQTT Client ID generation in low‑entropy environments (#47).

---

## **[2025.10.12]**
### Fixed
- Missing platform prefix in HA auto‑discovery (#44/#45).

### Changed
- PVOutput service refactoring.

---

## **[2025.10.5]**  
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

## **[2025.9.24]**  
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

## **[2025.8.31]**
### Fixed
- Resetting calculated daily sensors on restart.  
- Incorrect AC/DC Charger button names.

### Changed
- Upgraded `requests`, `ruamel.yaml`.  
- Alarm sensor value length capped at 255 chars.  
- `.yaml` files excluded from stale cleanup.

---

## **[2025.8.17]**
### Added
- Auto‑discovery of Sigenergy hosts + device IDs.  
- Option to upload grid imports instead of consumption.

### Changed
- Upgraded `pymodbus` to 3.11.1.

---

## **[2025.8.15]**
### Fixed
- AssertionError when creating AC Charger device.

---

## **[2025.8.12]**
### Added
- Support for self‑signed MQTT TLS certificates (#21).

---

## **[2025.8.11]**
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

## **[2025.8.5]**
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

## **[2025.8.2‑1]**
### Fixed
- CLI option handling bug introduced in 2025.8.2 (#15).

---

## **[2025.8.2]**
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

## **[2025.7.26‑1]**
### Fixed
- Docker build.

---

## **[2025.7.26]**
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

## **[2025.7.20]**
### Fixed
- Write operation failures (#9).

### Added
- Average PV string voltage to PVOutput.  
- Optional temperature upload.

---

## **[2025.7.13‑1]**
### Fixed
- Daily energy sensors disabled at midnight.

---

## **[2025.7.13]**
### Fixed
- PVOutput peak‑power reporting.  
- PVOutput values off by factor of 10.

---

## **[2025.7.10]**
### Fixed
- Slider stepping.  
- Sanity checks for power/energy sensors.  
- Negative consumption handling.  
- Modbus protocol updates (V2.6, V2.7).  
- Many new Modbus sensors.

---

## **[2025.6.14]**
### Added
- EMS Work Mode “Time‑Based Control”.

### Fixed
- Inverter Device Info not updating.  
- Spurious PVOutput peak values.  
- Empty MQTT payload handling (#4).

---

## **[2025.6.11]**
### Added
- Scan interval override options.

### Fixed
- PVOutput peak‑power scheduling.

---

## **[2025.6.5]**
### Fixed
- PVOutput daily peak power loss.  
- Modbus locking improvements.

---

## **[2025.6.1]**
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

## **[2025.5.30‑1]**
### Fixed
- Fix for failed start on 3‑phase installations (#3).

---

## **[2025.5.30]**
### Fixed
- Multiple Modbus write, sensor applicability, precision, PVOutput config, CLI/env handling, and exit‑path bugs.  
- Logging level corrections (#2).

### Added
- Sanity‑checking limits for Modbus values.  
- Sanity check on GridSensorActivePower (±100 kW) (#1).

---

## **[2025.5.24]**
### Changed
- Daily Peak PV Power auto‑update at 21:45.  
- Minor bug fixes and testing improvements.  
- Improved debugging of configuration overrides.

### Added
- Documentation of MQTT topics.

---

## **[2025.5.18]**
### Fixed
- Device sensor publishable overrides.  
- AC‑Charger initialisation.

### Added
- `--modbus-read-only` and related environment variables.

---

## **[2025.5.16‑1]**
### Fixed
- Validation issues.

---

## **[2025.5.16]**
### Fixed
- MQTT config processed twice.

---

## **[2025.5.15]**
### Fixed
- Handling of overrides producing lists.

### Changed
- Added override key to exception messages.

---

## **[2025.5.13]**
### Fixed
- Publishing issues.

---

## **[2025.5.12]**
### Fixed
- Various bug fixes.

### Added
- Environment variable configuration.  
- Python & Docker build publishing.

---

## **[2025.5.10]**
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

## **[2025.5.8]**
### Fixed
- Retry‑on‑failure logic.

---

## **[2025.5.7] — First public release**

---
