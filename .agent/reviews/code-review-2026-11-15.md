# sigenergy2mqtt code review — 2026-11-15

Reviewed at commit `881364a` (release `2026.11.15a1`). No source code was changed by this review.

## Scope and method

- **Read in full:** `__main__`, `main/*`, `modbus/*`, `mqtt/*`, `persistence/state_store.py`, `devices/base/*` (device, poller, scan groups, registry), `sensors/base/*` (sensor, readable, mixins, writeable, derived, accumulation, sanity check), `common/outage.py`, `pvoutput/` (service, status, service topics, most of output), `influxdb/` (service, base), second half of `monitor/service.py`, `config/config.py` (reload path).
- **Sampled only:** `config/` (cli, settings, merge, validation, auto-discovery), `diagnostics/`, `metrics/`, `cloud/` (including the vendored client), `influxdb/hass_history_sync.py`, `i18n.py`, and the register definition modules under `sensors/{plant,inverter,pss,pid,ev,cloud}`. Register addresses, gains and data types were **not** cross-checked against the protocol PDFs.
- **Baseline:** `pytest -n auto` → 2917 passed. `ruff check src` → 9 findings (8 auto-fixable import ordering).
- **Confirmation:** "Confirmed by execution" means a throwaway script exercised the real classes (mocking only the network edge) and reproduced the behaviour. "By reading" means the conclusion comes from the code alone.

Confidence is my estimate that the finding is a real defect (not that it is frequent).

## Summary

| ID | Finding | Severity | Confidence | Confirmed by execution |
|----|---------|----------|------------|------------------------|
| F01 | Power adjustment min/max bounds are 1000× (active) and 60 000× (reactive) too wide | High | 95% | Yes |
| F02 | A scan-group poller dies permanently and silently on any unexpected exception | High | 90% (mechanism) | Yes |
| F03 | PVOutput tasks die permanently when a response lacks rate-limit headers | High | 90% | Yes |
| F04 | A crashed worker thread (or refused MQTT CONNACK) ends the process with exit status 0 | Medium-High | 85% | Partly |
| F05 | Lifetime (`TOTAL_INCREASING`) energy sensors get no upper sanity limit | Medium | 75% unintended | Yes |
| F06 | State files are written non-atomically; a truncated file wins over the MQTT copy | Medium | 85% | Yes |
| F07 | Shutdown signals received during (re)initialisation are lost | Medium | 70% | No |
| F08 | Numeric writes truncate instead of rounding (2.01 kW is written as 2009 W) | Medium-Low | 95% | Yes |
| F09 | Daily accumulation carries the previous day's value across a restart | Medium-Low | 85% | Yes |
| F10 | Exceptions in MQTT command handlers are discarded without a log line | Medium-Low | 90% | Yes |
| F11 | InfluxDB: buffer never flushed on a timer or at shutdown; failed batches dropped; init failure is permanent | Medium-Low | 80% | No (grep) |
| F12 | No MQTT Last Will; "offline" is not flushed before the network loop stops | Medium-Low | 90% / 40% | No |
| F13 | Inconsistent error handling while creating devices at startup | Low-Medium | 70% | No |
| F14 | SIGHUP reload replaces live configuration under running threads | Low-Medium | 55% | No |
| F15 | Blocking calls on the event loop | Low | 85% | No |
| F16 | `MqttHandler._seen_mids` is never purged; `wait_for` stops waiting after MIDs wrap | Low | 95% | Yes |
| F17 | Modbus read/error metrics are double-counted | Low | 95% | Yes |
| F18 | PVOutput `l/l-avg` produces the line-to-neutral value | Low | 60% | Yes |
| F19 | `--pvoutput-voltage pv` is documented but rejected by the CLI | Low | 100% | Yes |
| F20 | Minor code defects (five items) | Low | 60–95% | No |
| D1–D8 | Documentation and log-message errors | Low | 90%+ | Partly |
| S1–S3 | Security notes (low priority, as requested) | Low | 60–90% | No |

---

## Findings

### F01 — Power adjustment bounds are wrong by orders of magnitude
`main/device_setup.py:292-308`

`get_state(sensor, modbus, "inverter", raw=True)` returns `RatedActivePower` raw, in **watts** (gain 1000). The sum is passed to `NumericSensorMixin.apply_min_max()`, which takes **display units** (kW / kvar) and multiplies by gain itself. The reactive branch additionally multiplies by 60.

Reproduced with the real sensor classes and the same calls, for a 10 kW inverter (raw 10000):

- `ActivePowerFixedAdjustmentTargetValue`: min/max = ±10000.0 kW, sanity raw = ±10 000 000 (expected ±10 kW).
- `ReactivePowerFixedAdjustmentTargetValue`: constructor default ±60.0 kvar becomes ±600 000.0 kvar.

Consequences: the Home Assistant number entities advertise meaningless ranges, and `value_is_valid()` and the sanity check — the only software guard on these writable registers — accept anything. The inverter presumably clamps, but the guard the code intends does not exist.

The protocol text for register 40003 is "Range: [-60.00 * base value, 60.00 * base value]", which almost certainly means 60 % of rated power; the adjacent Q/S register is "[-60.00, 60.00] %". The intended reactive factor needs the maintainer's decision (0.6 × rated kW is my reading).

Not exercised: the full `setup_devices()` path against a Modbus server; only the two calls it makes.

### F02 — A poller dies permanently on any unexpected exception
`devices/base/poller.py:411-488`, `sensors/base/sensor.py:1027-1030, 1275-1278`, `sensors/base/readable.py:105-110`, `main/device_thread.py:167, 181-191`

`SensorGroupPoller.run()` catches `ModbusException`, the two cloud errors and `RuntimeError`. Anything else ends the coroutine. Because the tasks are gathered with `return_exceptions=True`, the exception is only logged when *every* task has finished, i.e. at shutdown. The scan group simply stops publishing.

Reproduced: `OSError`, `KeyError` and `ZeroDivisionError` raised from `sensor.publish()` each terminate the poller task.

Two concrete routes exist in the code today:

1. `ReadOnlySensor._update_internal_state` deliberately re-raises `OSError`; `Sensor.publish` does not catch it, and neither does the poller.
2. `Sensor._handle_publish_error` re-raises when `transport` is falsy or not connected. For a `SanityCheckException` (a `ValueError`) on a sensor polled without a Modbus transport (service-thread sensors, `non_modbus_sensors` groups) this kills the poller. Reproduced with `transport=None`.

The monitor's overdue-topic check would eventually report the symptom, but nothing restarts the group. How often route 1 fires with pymodbus 3.16 is uncertain (it normally wraps socket errors); the lack of a safety net is the defect.

Related, by reading: `asyncio.CancelledError` is swallowed in `readable.py:101-103`, `mixins.py:468-470` and `poller.py:503`. This works only because `device.online` is set to `False` at the same time; any other cancellation is lost.

### F03 — PVOutput tasks die when rate-limit headers are missing
`pvoutput/service.py:97-106, 134, 188`, `pvoutput/output.py:174, 195`, `pvoutput/status.py:226-236`, `pvoutput/output.py:318-324`

`get_response_headers()` indexes `response.headers[...]` and raises `KeyError` when a response has no `X-Rate-Limit-*` headers (typical of a 502/503 from a front-end proxy). `upload_payload` and `seconds_until_status_upload` catch `ValueError, OSError, AttributeError, RequestException`, not `KeyError`; the service loops catch only `CancelledError`, `TimeoutError` and `RuntimeError`.

Reproduced with a 502 response without those headers: both `upload_payload()` and `seconds_until_status_upload()` raise `KeyError('x-rate-limit-limit')`. In the running service that ends the upload task until the next restart, without a log line.

Same family, by reading:
- `output.py:195` `int(v[index])` raises `ValueError` on an unexpected body; not caught at either level.
- `service_topics.handle_update` takes the service lock with a 1 s timeout while `seconds_until_status_upload` holds it across an HTTP GET with a 10 s timeout, so samples arriving during the hourly refresh can raise `TimeoutError` and be dropped (silently, see F10).
- After the third failed attempt `upload_payload` still logs "Retrying in 10 seconds" and sleeps (or sleeps until the rate-limit reset) before giving up.

### F04 — A crashed thread ends the process with exit status 0
`main/device_thread.py:234-240, 297-305`, `main/main.py:116-118`, `modbus/client_factory.py:41-44`, `mqtt/client.py:214-219`, `resources/linux/sigenergy2mqtt.service`

When a worker thread raises, `run_modbus_event_loop` logs it and sets `stop_event`; `start()` takes every thread offline and returns normally; `async_main` logs "Shutdown … completed" and returns. Reproduced: `start()` returns `None` after a thread raises. The exit status of 0 follows from reading `__main__.main()`.

The shipped systemd unit uses `Restart=on-failure`, so the service stays down. (Docker Compose uses `restart: always` and is unaffected.)

Two ways into this path:
- `ModbusClientFactory.get_client` does `await client.connect(); assert client.connected`. If the host is unreachable when the thread starts (after probing succeeded), the `AssertionError` crashes the thread. Under `python -O` the assert vanishes and "Connected" is logged for a client that is not connected.
- `on_connect` with a refused CONNACK calls `_thread.interrupt_main()`. At runtime SIGINT is handled by `exit_on_signal`, so this is a clean shutdown with status 0, even for a transient refusal such as "server unavailable" while the broker restarts.

### F05 — Lifetime energy sensors have no upper sanity limit
`sensors/base/sanity_check.py:62-76`

For `StateClass.TOTAL_INCREASING` the constructor sets `self.min_raw = 0`, and the next statement returns early because "min_raw is not None … already initialised via parameters". The data-type range and the `sanity-check-default-kw` maximum are never applied.

Reproduced: a kWh / `TOTAL_INCREASING` / `UINT64` check reports `min_raw=0, max_raw=None` and accepts a jump from 1000 to 10^15. The same sensor declared `TOTAL` gets ±500 000.

The configuration reference says the default applies to "power and energy sensors". These are the sensors where one bad read permanently corrupts Home Assistant's energy statistics. The early return looks accidental (75 %), but it may be relied on; the maintainer should confirm before it changes, since applying a maximum delta could reject legitimate catch-up jumps after a long outage.

### F06 — Non-atomic state files
`persistence/state_store.py:122-131, 771-789`, `sensors/base/accumulation.py:407-413`

`_DiskBackend.save` uses `Path.write_text`, which truncates and then writes. An interruption in between leaves an empty file. On load the empty string is treated as a legacy value and accepted (no validator), so with the default disk-first order the intact MQTT copy is never consulted; `AccumulationSensor` then fails to parse it and starts from 0.

Reproduced: after truncating a saved file, `load_sync` returns `''`.

Accumulation sensors persist on every source update, so write frequency is high and the window is hit often on SD-card hosts.

### F07 — Signals during (re)initialisation are lost
`__main__.py:59-71`, `main/service_setup.py:79-85`, `main/main.py:59-101`, `mqtt/__init__.py:104-128`

Before `setup_signals()` runs, a signal only sets flags (`auto_discovery._interrupted`, the MQTT reconnection flag). Those flags are read only inside failure/retry loops (`_wait_for_modbus`, `_connect_with_retry`). If Modbus and MQTT are healthy, a SIGTERM that arrives during device probing is recorded and then ignored: threads start and run normally.

On a restart cycle it is worse: the handlers from the previous cycle are still installed, bound to the old `configs` list, and there is no second-signal force exit. `docker stop` then ends in SIGKILL with no offline availability and no persistence flush.

Not reproduced; needs an integration test with a slow probe.

### F08 — Numeric writes truncate
`sensors/base/writeable.py:188-195`, `sensors/base/mixins.py:487`, `sensors/base/sensor.py:1680-1686`

`NumericSensorMixin.set_value` computes `float(value) * gain` and `_convert_value_to_registers` applies `int()`. Reproduced: setting 2.01 kW writes raw 2009 (2.01 × 1000 = 2009.9999999999998). `Sensor.state2raw("0.29")` with gain 100 returns 28. Fix is `round()` at both sites.

### F09 — Daily accumulation survives into the next day
`sensors/base/accumulation.py:397-413, 698-723, 889-930`

- `SimpleEnergyDailyAccumulationSensor` (used by `PlantDailySelfConsumedEnergy`) restores its persisted total with no age check and `_last_day_tuple` starts as `None`, so a restart on a later day continues from the old total. Reproduced: a two-day-old total of 7777.0 was restored.
- `EnergyDailyAccumulationSensor._load_midnight_state` uses `stale_after=24h` rather than "same local day". Reproduced: a baseline written at 23:00 the previous day is restored at 22:40 today. In practice this needs a baseline written after midnight (first install, manual reset, or re-baseline) plus downtime across the following midnight.

### F10 — Command-handler exceptions are discarded
`mqtt/handler.py:139-159`

Coroutines are submitted with `run_coroutine_threadsafe` and the future is only tracked for shutdown; nobody reads its exception. Reproduced: a handler raising `ValueError` produces no log record. A malformed command payload, a lock timeout (F03) or a write failure outside the handful of logged cases disappears.

### F11 — InfluxDB buffering
`influxdb/base.py` (`_flush_buffer_internal`, `write_line`, `flush_buffer`, `async_init`), `influxdb/service.py:86-125`

- `flush_buffer()` has no callers (grep). Flushes happen only inside `write_line`, so the tail of the buffer is lost at shutdown, and `execute_write` refuses to write once the device is offline anyway.
- The buffer is cleared before the write; a failed batch is dropped, so an InfluxDB outage loses all data for its duration.
- `_batch_lock` is held across the HTTP request, contradicting the docstring's "new lines can be accepted immediately".
- If `async_init()` fails at startup the service returns and never retries, while MQTT subscriptions stay active and each message is buffered, dropped and counted as a write error. Modbus and MQTT wait indefinitely for their dependencies; InfluxDB does not.
- The connection probe writes a real point (`state value=1`) on every start.

### F12 — Availability after an unclean exit
`mqtt/client.py` (no `will_set`), `main/device_thread.py:183-191`, `mqtt/__init__.py:211-214`, `devices/base/ha_publisher.py:159`

There is no Last Will, so after a crash, SIGKILL or power loss the retained device availability stays "online" (90 %, by grep). Separately, the graceful path publishes "offline" at QoS 2 without waiting and then calls `loop_stop()`; whether the QoS 2 handshake completes is timing-dependent (40 %, not tested against a broker).

### F13 — Device creation error handling is inconsistent
`main/device_setup.py`

- `_setup_dc_chargers` (395-410) has no `try/except`; AC charger, PID and PSS creation do. A failing DC charger aborts startup.
- `_is_grid_outage` (517-533) catches only `TimeoutError`/`ModbusException`; it is called from inside `except` blocks, so a `SanityCheckException` or `OSError` there aborts startup.
- `_watch_grid_restore_and_request_restart` is started with `asyncio.create_task` and no reference is kept; an unexpected exception ends it silently and the promised restart never happens. A watcher left over from a previous cycle can also request a redundant restart.
- `_setup_ac_chargers`/`_setup_pid`/`_setup_pss` receive `protocol_version` as the maximum across plants processed so far, not this plant's version.

### F14 — SIGHUP reload under running threads
`main/service_setup.py:87-105`, `config/config.py:239-249`, `main/main.py:121`

`reload_on_signal` awaits `active_config.reload()` *before* requesting the restart. `reload()` replaces `_settings` and then awaits auto-discovery (minutes when `force`) before `finalize_modbus`, while pollers keep reading `active_config`. `async_main` then reloads a second time. Requesting the restart first and letting `async_main` do the single reload removes the window.

### F15 — Blocking calls on the event loop
- `sensors/base/sensor.py:1232-1234`: `wait_for_publish(timeout=0.5)` per publish. Normally sub-millisecond; with a slow broker each sensor can stall the loop for 0.5 s.
- `mqtt/__init__.py:107`: synchronous `mqtt_client.connect()`.
- `sensors/base/sensor.py:878, 906, 917`: `delete_sync`/`load_sync`/`save_sync` during discovery block the device loop on a round trip through the main loop and executor, up to `sync_timeout` each.

### F16 — `_seen_mids` grows to 65 535 and defeats `wait_for`
`mqtt/handler.py:283-300, 430-438`

Every acknowledged publish that nobody is waiting for is added to `_seen_mids`; only `_pending_mids` is purged. Reproduced: after 65 535 acknowledgements the set holds 65 535 entries, and `wait_for` on a new, unacknowledged publish returns `True` in 0.00 s. After a few hours of running, `wait_for` (used for discovery publishes) no longer waits.

### F17 — Metrics double-counting
`modbus/client.py:180-190, 259-262`, `sensors/base/readable.py:105-110, 148-150`

Reproduced: one successful sensor read calls `Metrics.modbus_read` twice (client and sensor); a failed read-ahead and a failed sensor read each call `modbus_read_error` twice. Cache hits are also counted as reads with near-zero latency, skewing the averages.

### F18 — `l/l-avg`
`pvoutput/service_topics.py:198-207`, `pvoutput/__init__.py:184-192`

The inputs are phase (line-to-neutral) voltages and the formula is `sqrt(ΣV²)/sqrt(3)`. Reproduced: three phases at 230 V give 230.0, identical to `l/n-avg`; line-to-line would be about 398. With fewer than three topics the fixed √3 is also wrong. Intent is unclear, hence 60 %.

### F19 — `--pvoutput-voltage pv`
`config/cli.py:545-547`. `choices` omits `pv` although the help text and docs list it and `VoltageSource.PV` exists. Reproduced: argparse exits 2 with "invalid choice: 'pv'".

### F20 — Minor code defects (by reading)
1. `sensors/base/sensor.py:1501`: `isinstance(value, float) and value == 0 or value == 1` has the wrong precedence; integer 0 is not handled.
2. `modbus/lock_factory.py`: `clear()` is never called, so each restart leaves the previous `ModbusClient` and its lock referenced.
3. `devices/base/device.py:478-529`: `get_sensor(search_children=True)` searches one level; `get_all_sensors` is recursive.
4. `sensors/base/sensor.py:537`: `derived_sensors` is keyed by class name, so two derived sensors of the same class on one source overwrite each other. I did not check whether this occurs.
5. `modbus/client.py:152-159`: the read-ahead cache is keyed by address only, not input type. Harmless for Sigenergy's disjoint 30000/40000 ranges.

### Documentation and log-message errors
- **D1** `resources/configuration/README.md` (sanity-check-default-kw): states the default applies to energy sensors; see F05.
- **D2** `config/cli.py:547`, `CLI.md`, `ENV.md`: `pv` listed for `--pvoutput-voltage`; see F19.
- **D3** `config/config.py:9-13`: module docstring describes `active_config.system_initialize()`, which does not exist, and a synchronous `load()`.
- **D4** `modbus/client.py:129-131, 233-235` and `sensors/base/sensor.py:986-988, 1063-1065`: the "docstrings" follow an `import` statement, so they are bare string expressions and `__doc__` is `None`.
- **D5** `modbus/client.py:52-53`: says cache entries are invalidated when `bypass_read_ahead` is called; nothing calls it (grep).
- **D6** `sensors/base/readable.py:185`: `elapsed={(elapsed / 1000):.2f}ms` divides seconds by 1000; should multiply. `readable.py:104` and `mixins.py:472` log "failed to acquire lock" for a `TimeoutError` on paths that take no lock (reads) or misattribute it.
- **D7** `main/device_setup.py:546, 558`: grid-restore watcher messages say "AC charger" for PID and PSS as well. `common/outage.py` `clear_outage_trackers` says "intended for tests" but is used at runtime.
- **D8** `main/thread_config.py:36-37`: documents `transport_factory` as a constructor argument; `create()` does not accept it and callers assign the attribute afterwards.

### Security notes (low priority)
Given that the Modbus interface itself is unauthenticated, these add little attack surface for anyone already on the LAN.
- **S1** MQTT command topics write to the inverter for any client that can publish to the broker. `--modbus-readonly` is the existing mitigation. F01 removes the range check that would otherwise bound two of those writes.
- **S2** `diagnostics/server.py:74, 76`: the POST endpoints have no authentication and no `Origin`/CSRF check; protection is the loopback default bind plus the optional IP allow-list.
- **S3** `influxdb/base.py`: the base URL is always `http://`, so tokens and passwords travel in clear text.

---

## Implementation plans

None of these has been actioned. Each plan is independent; A and B are the ones that matter.

### Plan A — Runtime resilience and lifecycle (F02, F03, F04, F07, F10, F12, F13, F14)
**Suggested model: Claude Opus 5.5.** The changes cross threads, event loops and signal handling, and several need a judgement about what "safe" means on shutdown. Use Claude Fable 5.2 instead if F07 and F14 are to be redesigned rather than patched.

1. **Poller safety net (F02).** In `SensorGroupPoller.run`, add a final `except Exception` that logs with traceback (rate-limited through the transport's `OutageTracker` where one exists), calls `_reschedule_unpublished`, and continues. Let `asyncio.CancelledError` propagate. In `Sensor._handle_publish_error`, do not re-raise `SanityCheckException` when there is no transport: count the failure and return `False`. Catch `OSError` alongside `ModbusException` in `Sensor.publish` and the poller's reconnect branch.
2. **Surface dead tasks early (F02).** In `read_and_publish_device_sensors`, attach a done-callback to each task that logs an unexpected exception immediately instead of at shutdown.
3. **PVOutput (F03).** Make `get_response_headers` tolerant (`.get` with defaults, return `None`s) and adjust the three callers. Add a logged catch-all to both `publish_updates` loops with a 60 s back-off. Catch `ValueError`/`IndexError` in `_verify`. Do not sleep after the final attempt. Raise the `handle_update` lock timeout or stop holding the lock across the HTTP GET.
4. **Exit status (F04).** Have `start()` report whether a thread crashed; propagate through `async_main` so `main()` exits non-zero. Replace the `assert` in `ModbusClientFactory.get_client` with a retry using the same back-off as `_wait_for_modbus`. In `on_connect`, treat a refused CONNACK after a previously successful connection as an outage (let paho retry) and only abort on the first connection, with a non-zero exit.
5. **Signals (F07).** Install the runtime handlers before `initialize_async()` on every cycle, backed by a process-wide `threading.Event` that `setup_devices`, `_wait_for_modbus`, `mqtt_setup` and `start()` all check. Keep the second-signal force exit for the whole lifetime.
6. **Handler exceptions (F10).** In `MqttHandler._schedule_coroutine`, add a done-callback that logs `future.exception()` with the handler label.
7. **Availability (F12).** Set a Last Will per client (decide the topic layout: one will per MQTT client means per-thread, not per-device, so a per-thread availability topic added to each device's availability list is the likely shape). In `mqtt_teardown`, wait for outstanding publishes before `loop_stop()`.
8. **Startup consistency (F13).** Wrap DC charger creation like the others; broaden `_is_grid_outage`; keep a reference to the watcher task, log its failure, cancel it at the start of each cycle; pass the plant's own protocol version.
9. **SIGHUP (F14).** Request the restart only; let `async_main` perform the single reload.

Tests: one unit test per item above (the reproductions described in each finding translate directly), plus an integration test for item 5 using the existing Modbus test server with an artificially slow probe.

### Plan B — Data correctness (F01, F05, F06, F08, F09, F18)
**Suggested model: Claude Opus 5.5.** The edits are small, but F01, F05 and F18 need domain reasoning and a decision recorded in the change.

Decisions needed from the maintainer first:
- F01: reactive limit = 0.6 × rated power (my reading) or another factor.
- F05: whether lifetime counters should get a maximum delta, and if so whether it scales with elapsed time.
- F18: whether `l/l-avg` should report true line-to-line voltage.

Steps:
1. **F01.** In `setup_devices`, convert the summed raw value with the sensor's gain (or read with `raw=False`) before `apply_min_max`; apply the agreed reactive factor. Add a test that builds a plant with a known rated power and asserts min/max and sanity bounds in display units.
2. **F08.** Use `round()` in `NumericSensorMixin.set_value` / `_convert_value_to_registers` and in `Sensor.state2raw`. Parametrised test over values such as 2.01, 0.29, 4.35 with gains 100 and 1000.
3. **F05.** Make the "already initialised via parameters" early return depend on the constructor arguments, not on `self.min_raw` after the `TOTAL_INCREASING` assignment. Regenerate `SENSORS.md` and check the diff of sanity descriptions before merging; expect many lines to change.
4. **F06.** Write to a temp file in the same directory, `fsync`, then `os.replace`. Treat an empty or unparseable file as absent so the other backend is consulted. Consider throttling accumulation persistence (for example at most once per minute per key, plus on shutdown).
5. **F09.** Give `SimpleEnergyDailyAccumulationSensor` a same-local-day check on restore (the envelope `ts` is available; expose it from `StateStore.load` or add a `validator`). Replace the 24 h window in `EnergyDailyAccumulationSensor._load_midnight_state` with the same check.
6. **F18.** Implement the agreed formula, or remove the option and document it.

### Plan C — Housekeeping (F11, F15, F16, F17, F20, ruff)
**Suggested model: Claude Sonnet 5.5.** Localised changes with clear expected behaviour.

1. **F16.** Stop parking MIDs nobody waits for: record a timestamp with each entry and purge with the same expiry as `_pending_mids`, or only park MIDs while a `wait_for` is in flight.
2. **F17.** Count Modbus reads and errors in one place (the client); remove the calls in `readable.py` and the extra one in `read_ahead_registers`; do not count cache hits as reads.
3. **F11.** Add a periodic flush to `_keep_running` and a final flush before the device goes offline; re-queue a failed batch into a bounded buffer; release `_batch_lock` before the HTTP call; retry `async_init` with back-off; make the probe side-effect free if the API allows.
4. **F15.** Move `wait_for_publish` off the hot path (publish without waiting at QoS 0 and rely on the existing health registry), run `connect()` in a thread, and use the async state-store API in discovery.
5. **F20.** Fix the precedence in `set_debug_logging`; call `ModbusLockFactory.clear()` in the restart loop; make `get_sensor` recursive; key `derived_sensors` by `unique_id` (check the handful of places that look up by class name first).
6. `ruff check --fix src`.

### Plan D — Documentation, CLI and log text (F19, D1–D8)
**Suggested model: Claude Haiku 5.5.** Mechanical edits; no behavioural risk beyond F19.

1. Add `"pv"` to the `--pvoutput-voltage` choices; regenerate `CLI.md` with `scripts/update_md.py`.
2. Fix the `ms` calculation and the two "failed to acquire lock" messages.
3. Move the misplaced docstrings above the imports in `modbus/client.py` and `sensors/base/sensor.py`.
4. Correct the `config/config.py` module docstring, the `ModbusClient` class docstring (or wire up `bypass_read_ahead` after writes, which belongs in Plan C), the `ThreadConfig` docstring, `clear_outage_trackers`, and the watcher log text.
5. Update the sanity-check paragraph in the configuration reference once Plan B step 3 is decided.
