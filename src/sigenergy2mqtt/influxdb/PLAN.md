# InfluxDB module — implementation plan

Source: code review of `sigenergy2mqtt/influxdb/{base,service,hass_history_sync,__init__}.py`
and their test suite (10 files). Excludes InfluxDB v3 implementation itself; includes
refactoring to make v3 easier to add later.

**How to use this across sessions:** paste only the phase you're working on into a new
chat, along with the current version of the file(s) it touches. You don't need the
original review conversation — each phase below is self-contained.

---

## Phase 1 — Crash fix (do first, smallest possible session)

**File:** `service.py` only.

- `_matches_filter`: `uid` can be `None` (from `getattr(s, "unique_id", None)`), and
  `re.search(pat, None)` raises `TypeError`. This isn't caught in `subscribe()`'s
  `except (requests.RequestException,)` clause, so it can crash the whole subscribe loop.
  Fix: `uid = uid or ""` before the regex checks.
- Add a test to `test_service_helpers.py::TestInfluxServiceMissingCoverage::test_matches_filter`
  covering `uid=None`.

## Phase 2 — Correctness fixes (line protocol + logging)

**Files:** `base.py`, `hass_history_sync.py`.

- `to_line_protocol`'s `esc()` doesn't escape `=` (required in line protocol tag
  keys/values). Add it.
- `fmt_val()` escapes `"` in string fields but not `\`. Escape backslash *first*, then quotes.
- `hass_history_sync.py` has a copy-pasted log line — `get_earliest_timestamp` and
  `copy_records_from_homeassistant` both log `"detect_homeassistant_db: base=..."`,
  which is misleading when grepping logs. Rename each to match its actual method.
- Add 2–3 tests to `TestToLineProtocolExtended` for `=` in tags and `\` in string fields.

## Phase 3 — Untested but load-bearing paths (pure test additions, no prod changes)

**Files:** `base.py` tests (new or existing test file).

- Test that `svc.online = False` calls `self._session.close()`.
- Test `_ShutdownAwareRetry.increment()` raises `MaxRetryError` when `_shutdown_event.is_set()`.
- Test the final `_init_connection` fallback branch (no token, no username → tokenless v1).
- Test `execute_write` when `_writer_type` is `None`/unrecognized while online (should
  return `False`, not raise) — this is the normal state right after `async_init()`
  succeeds with InfluxDB disabled.
- Normalize fixtures using `svc._online = True` (bypasses the real setter) to instead use
  the real `online` setter, so the session-close logic above actually gets exercised.

## Phase 4 — Refactor: probe sequence (biggest v3-readiness win, do before v3)

**File:** `base.py`, `_init_connection` only.

Replace the four repeated "try, then check shutdown" blocks with an ordered list:

```python
probes = [
    (bool(config["token"]), lambda: self._try_v2_write(config["base"], config["bucket"], config["org"], config["token"], test_line)),
    (bool(config["user"]), lambda: self._try_v1_write(config["base"], config["db"], config["auth"], test_line)),
    (True, lambda: self._try_v2_write(config["base"], config["bucket"], config["org"], None, test_line)),
    (True, lambda: self._try_v1_write(config["base"], config["db"], None, test_line)),
]
for should_try, probe in probes:
    if should_try and probe():
        return
    if self._shutdown_event.is_set():
        return
raise RuntimeError(f"{self.log_identity} Initialization failed: could not determine writable endpoint or create database/bucket")
```

Existing tests in `test_service_comprehensive.py` / `test_influx_integration.py` should
pass unchanged — this is mechanical, use the existing suite as the regression check.
Adding a v3 probe later becomes "append one tuple" instead of duplicating another block.

## Phase 5 — Refactor: pagination dedup (biggest single refactor)

**File:** `hass_history_sync.py`, `copy_records_v1` / `copy_records_v2`.

Protected by existing tests: `testcopy_records_v1_chunking`, `testcopy_records_v2_chunking`,
`test_chunking_stops_on_offline` (all in `test_service_new_features.py`).

Extract the shared while-online / fetch-page / write-lines / chunk-size-check loop into
one method; `copy_records_v1`/`copy_records_v2` become thin closures that only build/parse
their respective query format. Do this **before** v3 — the SQL-based v3 reader will be a
third implementation of the same loop, and without this refactor that's a third copy-paste.

## Phase 6 — Refactor: writer strategy extraction (v3-readiness, design-heavy)

**Files:** `base.py` (optionally split into `writers.py`).

- Introduce a minimal `Writer` interface (`probe(...) -> bool`, `write(session, data)`).
  Move the v1 and v2 write logic out of `_try_v1_write`/`_try_v2_write`/`execute_write`'s
  branches into two classes implementing it.
- Replace `execute_write`'s `if self._writer_type == "v2_http" ... elif == "v1_http"`
  with a lookup into a `{writer_type: Writer}` dict.
- Do **not** touch `query_v1`/`query_v2` in this phase — v3's SQL-vs-Flux/InfluxQL
  difference is where the real design work is, and abstracting it now without a concrete
  v3 target would likely produce the wrong abstraction. Leave a comment noting this is
  deferred.
- Treat as two sessions: propose the interface first, implement after sign-off.

## Phase 7 — Test-suite consolidation (do last, once prod code has stabilized)

**Files:** new `conftest.py`; trim `test_service_comprehensive.py`, `test_service_helpers.py`,
`test_service_new_features.py`, `test_influx_integration.py`, `test_influx_e2e.py`.

- One shared `FakeResponse` class with the full attribute set (`status_code`, `text`,
  `content`, `.json()`) — the version in `test_service_comprehensive.py` is missing
  `.text`, which would break on any test that exercises a write-failure log path.
- Shared fixtures for "disabled-init InfluxService" / "disabled-init HassHistorySync"
  (currently repeated near-verbatim in most files).

## Explicitly deferred / skip

- Flux/InfluxQL tag-value escaping (injection hardening) — real but low urgency since
  tag values come from internally generated `entity_id`/`object_id`, not user input.
- Configurable probe timeouts (`timeout=5` hardcoded in several probe methods) — cosmetic,
  fold into Phase 4 if there's room, otherwise skip.