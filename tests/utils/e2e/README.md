# tests/utils/e2e

End-to-end outage scenarios. `run.sh` runs the real `sigenergy2mqtt` application against
[`modbus_test_server.py`](../modbus_test_server.py) (the Modbus TCP and Cloud API simulator) and a
local Mosquitto broker. It simulates outages by blocking ports with `iptables`, then checks the
application log for the expected behaviour.

These are slow (2–5 minutes per scenario), need root, and change the host's firewall rules
temporarily, so they are **not** part of the pytest suite or CI. Run them by hand after changing
connection, reconnection, outage logging or health check/restart behaviour.

## Requirements

- **Linux** with `bash`.
- **Python environment with the project installed**, including test dependencies:
  `pip install -e ".[test]"`. The interpreter is `python3` on `PATH`, or set `PYTHON`.
- **Mosquitto**, found on `PATH` or at `/usr/sbin/mosquitto` (e.g. `apt-get install mosquitto`).
  The script starts its own instance on a private port; the system service is not used.
- **`iptables`**, run either as root or through passwordless `sudo` (`sudo -n`). Outages are
  simulated with `REJECT --reject-with tcp-reset` rules on the loopback interface. That gives the
  same "connection refused/reset" seen when a host goes away, and the simulator keeps its state
  (unlike stopping it, which regenerates random values and trips sanity checks on recovery).
  Every rule is tagged with the comment `sigenergy2mqtt-e2e` and removed when the script exits,
  including on Ctrl-C.
- **Free local ports** 15020 (Modbus), 18080 (Cloud API) and 18830 (MQTT). Override them with
  `E2E_MODBUS_PORT`, `E2E_CLOUD_PORT` and `E2E_MQTT_PORT`.

The script checks all of these before starting, and exits with status 2 if anything is missing.

## Usage

Run from the repository root:

```bash
tests/utils/e2e/run.sh all
```

```bash
tests/utils/e2e/run.sh outage mqtt
```

| Scenario    | Simulates | Checks |
|-------------|-----------|--------|
| `outage`    | Modbus and Cloud API unreachable for 100s while running | Each outage is reported once and ends once; the restart is deferred, with no restart requested; the app keeps running |
| `coldstart` | Modbus and Cloud API absent for 40s when the app starts | Startup waits (reported once) instead of exiting, then becomes healthy |
| `mqtt`      | MQTT broker unreachable for 60s while running | The broker outage is reported once and ends once; no restart is requested |
| `mqttcold`  | MQTT broker unreachable for 100s when the app starts | Threads and persistence wait instead of crashing or falling back to disk-only; no restart is requested |

Every scenario also checks that the app is still running, that no thread crashed and that nothing
was logged at CRITICAL. The exit status is 0 if every check passed, and 1 otherwise.

Durations can be changed with `E2E_OUTAGE_SECS`, `E2E_MQTT_OUTAGE_SECS`, `E2E_COLDSTART_SECS`
and `E2E_MQTTCOLD_SECS`. Keep outages longer than the health check's `retries × interval`
(30s in `config.yaml.in`). Otherwise the restart deferral is not exercised.

## Output

Each scenario writes to `tests/utils/e2e/output/<scenario>/` (ignored by git), or to
`$E2E_OUTPUT_DIR/<scenario>/`:

- `app.log`: the application log, where the checks are made
- `server.log`: the Modbus/Cloud API simulator
- `mosquitto.log`
- `timeline.log`: when the ports were blocked and unblocked
- `config.yaml`: the generated application configuration
- `state/`: the application's persistent state directory

To see the outage-related lines of a run:

```bash
grep -E "WARNING|ERROR|CRITICAL|outage|estart|HEALTHY|DEGRADED" tests/utils/e2e/output/outage/app.log
```

## Files

- `run.sh`: the scenarios and checks
- `config.yaml.in`: the application configuration template. Health checks run every 10s with 3
  retries, so the old behaviour (a restart after 30s of failures) would show within an outage.
  `InverterSelfConsumedPower` is excluded from topic monitoring because the simulator's random
  battery power makes it fail its sanity check, so it never publishes.
