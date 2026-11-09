#!/usr/bin/env bash
# End-to-end outage scenarios: runs the real sigenergy2mqtt app against
# tests/utils/modbus_test_server.py (Modbus + Cloud API simulator) and a local
# Mosquitto broker, and simulates outages by blocking ports with iptables.
# See README.md in this directory for requirements and details.
#
# Usage: tests/utils/e2e/run.sh <scenario>... | all
#   outage     Modbus + Cloud unreachable for 100s while running
#   coldstart  Modbus + Cloud unavailable when the app starts
#   mqtt       MQTT broker unreachable for 60s while running
#   mqttcold   MQTT broker unreachable when the app starts
#
# Exit status: 0 if every scenario passed its checks, 1 otherwise.
set -u

E2E=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$E2E/../../.." && pwd)
PY=${PYTHON:-python3}
OUTPUT_DIR=${E2E_OUTPUT_DIR:-$E2E/output}
MODBUS_PORT=${E2E_MODBUS_PORT:-15020}
CLOUD_PORT=${E2E_CLOUD_PORT:-18080}
MQTT_PORT=${E2E_MQTT_PORT:-18830}
OUTAGE_SECS=${E2E_OUTAGE_SECS:-100}        # Modbus/Cloud outage (> health check retries x interval)
MQTT_OUTAGE_SECS=${E2E_MQTT_OUTAGE_SECS:-60}
COLDSTART_SECS=${E2E_COLDSTART_SECS:-40}   # how long the simulator is absent at startup
MQTTCOLD_SECS=${E2E_MQTTCOLD_SECS:-100}    # how long the broker is unreachable at startup
RULE_TAG="sigenergy2mqtt-e2e"

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo -n"; fi
MOSQUITTO=$(command -v mosquitto || echo /usr/sbin/mosquitto)

# ---------------------------------------------------------------- prerequisites

check_requirements() {
  local ok=0
  "$PY" -c "import sigenergy2mqtt, pymodbus, aiohttp" 2>/dev/null || { echo "!! $PY cannot import sigenergy2mqtt (run: pip install -e \".[test]\")"; ok=1; }
  [ -x "$MOSQUITTO" ] || { echo "!! mosquitto not found (e.g. apt-get install mosquitto)"; ok=1; }
  command -v iptables >/dev/null || [ -x /usr/sbin/iptables ] || { echo "!! iptables not found"; ok=1; }
  $SUDO iptables -L INPUT -n >/dev/null 2>&1 || { echo "!! cannot run iptables (needs root or passwordless sudo)"; ok=1; }
  for p in "$MODBUS_PORT" "$CLOUD_PORT" "$MQTT_PORT"; do
    if (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null; then echo "!! port $p is already in use"; ok=1; fi
  done
  return $ok
}

# --------------------------------------------------------------------- helpers

log() { echo "$(date +%T) == $*" | tee -a "$OUT/timeline.log"; }

block_ports() {   # connection refused / reset, as when a host goes away; the simulator keeps its state
  for p in "$@"; do $SUDO iptables -I INPUT -i lo -p tcp --dport "$p" -m comment --comment "$RULE_TAG" -j REJECT --reject-with tcp-reset; done
  log "BLOCKED port(s) $*"
}
unblock_ports() {
  for p in "$@"; do
    while $SUDO iptables -D INPUT -i lo -p tcp --dport "$p" -m comment --comment "$RULE_TAG" -j REJECT --reject-with tcp-reset 2>/dev/null; do :; done
  done
}

start_broker() {
  printf 'listener %s 127.0.0.1\nallow_anonymous true\npersistence false\n' "$MQTT_PORT" >"$OUT/mosquitto.conf"
  "$MOSQUITTO" -c "$OUT/mosquitto.conf" >"$OUT/mosquitto.log" 2>&1 &
  BROKER=$!
  for _ in $(seq 1 20); do (exec 3<>"/dev/tcp/127.0.0.1/$MQTT_PORT") 2>/dev/null && return; sleep 0.5; done
  echo "!! mosquitto did not start"; return 1
}

start_server() {
  (cd "$REPO" && PYTHONPATH="$REPO/src:$REPO" \
     MODBUS_TEST_SERVER_HOST=127.0.0.1 MODBUS_TEST_SERVER_PORT="$MODBUS_PORT" MODBUS_TEST_SERVER_CLOUD_PORT="$CLOUD_PORT" \
     MODBUS_TEST_SERVER_CLOUD_USERNAME=test MODBUS_TEST_SERVER_CLOUD_PASSWORD=test \
     exec "$PY" -m tests.utils.modbus_test_server >>"$OUT/server.log" 2>&1) &
  SERVER=$!
  log "test server started (Modbus :$MODBUS_PORT, Cloud :$CLOUD_PORT)"
}

write_config() {
  sed -e "s/@MODBUS_PORT@/$MODBUS_PORT/" -e "s/@CLOUD_PORT@/$CLOUD_PORT/" -e "s/@MQTT_PORT@/$MQTT_PORT/" "$E2E/config.yaml.in" >"$OUT/config.yaml"
}

start_app() {
  (cd "$REPO" && PYTHONPATH="$REPO/src" SIGENERGY2MQTT_STATE_DIR="$OUT/state" exec "$PY" -m sigenergy2mqtt -c "$OUT/config.yaml" >"$OUT/app.log" 2>&1) &
  APP=$!
  log "app started"
}

stop_all() {
  [ -n "${APP:-}" ] && { kill -INT "$APP" 2>/dev/null; wait "$APP" 2>/dev/null; }
  [ -n "${SERVER:-}" ] && { kill "$SERVER" 2>/dev/null; wait "$SERVER" 2>/dev/null; }
  [ -n "${BROKER:-}" ] && { kill "$BROKER" 2>/dev/null; wait "$BROKER" 2>/dev/null; }
  unblock_ports "$MODBUS_PORT" "$CLOUD_PORT" "$MQTT_PORT"
  APP="" SERVER="" BROKER=""
}
trap 'stop_all' EXIT
trap 'stop_all; exit 130' INT TERM

wait_for() {   # wait_for <regex> <seconds>
  for _ in $(seq 1 "$2"); do grep -qE "$1" "$OUT/app.log" 2>/dev/null && return 0; sleep 1; done
  return 1
}
require_healthy() {   # require_healthy <seconds>: a timeout is a failed check, not just a log line
  if wait_for "Status is HEALTHY" "$1"; then return 0; fi
  log "!! app never became healthy"; echo "   FAIL  app became healthy within $1s"; FAILURES=$((FAILURES + 1)); return 1
}
wait_for_count() {   # wait_for_count <regex> <count> <seconds>
  for _ in $(seq 1 "$3"); do [ "$(grep -cE "$1" "$OUT/app.log" 2>/dev/null)" -ge "$2" ] && return 0; sleep 1; done
  return 1
}

# ---------------------------------------------------------------------- checks

FAILURES=0
expect_count() {   # expect_count <description> <regex> <expected count>
  local n; n=$(grep -cE "$2" "$OUT/app.log")
  if [ "$n" -eq "$3" ]; then echo "   PASS  $1"; else echo "   FAIL  $1 (expected $3, found $n)"; FAILURES=$((FAILURES + 1)); fi
}
expect_at_least() {   # expect_at_least <description> <regex> <minimum count>
  local n; n=$(grep -cE "$2" "$OUT/app.log")
  if [ "$n" -ge "$3" ]; then echo "   PASS  $1"; else echo "   FAIL  $1 (expected at least $3, found $n)"; FAILURES=$((FAILURES + 1)); fi
}
expect_running() {
  if kill -0 "$APP" 2>/dev/null; then echo "   PASS  app is still running"; else echo "   FAIL  app exited"; FAILURES=$((FAILURES + 1)); fi
}
common_checks() {
  expect_running
  expect_count "no thread crashed" "thread crashed" 0
  expect_count "no CRITICAL messages" "^CRITICAL|[0-9] CRITICAL " 0
}

# ------------------------------------------------------------------- scenarios

scenario_outage() {
  start_server; sleep 8; start_app
  require_healthy 90
  sleep 5; block_ports "$MODBUS_PORT" "$CLOUD_PORT"
  sleep "$OUTAGE_SECS"
  unblock_ports "$MODBUS_PORT" "$CLOUD_PORT"; log "UNBLOCKED"
  wait_for_count "outage ended" 2 300; sleep 15
  common_checks
  expect_count "Modbus outage reported once" "modbus://[^ ]+ outage started" 1
  expect_count "Cloud outage reported once" "cloud://[^ ]+ outage started" 1
  expect_count "restart deferred during the outage" "will not trigger a restart" 1
  expect_count "no restart requested" "Restart requested" 0
  expect_count "Modbus outage ended" "modbus://[^ ]+ outage ended" 1
  expect_count "Cloud outage ended" "cloud://[^ ]+ outage ended" 1
}

scenario_coldstart() {
  start_app
  sleep "$COLDSTART_SECS"; start_server
  require_healthy 180; sleep 5
  common_checks
  expect_count "startup wait reported once" "modbus://[^ ]+ outage started: unable to connect" 1
  expect_count "startup wait ended" "modbus://[^ ]+ outage ended" 1
  expect_at_least "became healthy" "Status is HEALTHY" 1
}

scenario_mqtt() {
  start_server; sleep 8; start_app
  require_healthy 90
  sleep 5; block_ports "$MQTT_PORT"
  sleep "$MQTT_OUTAGE_SECS"
  unblock_ports "$MQTT_PORT"; log "UNBLOCKED"
  wait_for "mqtt://[^ ]+ outage ended" 180; sleep 15
  common_checks
  expect_count "MQTT outage reported once" "mqtt://[^ ]+ outage started" 1
  expect_count "MQTT outage ended" "mqtt://[^ ]+ outage ended" 1
  expect_count "no restart requested" "Restart requested" 0
}

scenario_mqttcold() {
  start_server; sleep 8
  block_ports "$MQTT_PORT"; start_app
  sleep "$MQTTCOLD_SECS"
  unblock_ports "$MQTT_PORT"; log "UNBLOCKED"
  require_healthy 180; sleep 15
  common_checks
  expect_at_least "became healthy" "Status is HEALTHY" 1
  expect_count "MQTT startup wait reported once" "mqtt://[^ ]+ outage started" 1
  expect_count "MQTT startup wait ended" "mqtt://[^ ]+ outage ended" 1
  expect_count "persistence kept MQTT redundancy" "disk only" 0
  expect_count "no restart requested" "Restart requested" 0
}

# ------------------------------------------------------------------------ main

[ $# -ge 1 ] || { sed -n '7,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
SCENARIOS=("$@"); [ "$1" = all ] && SCENARIOS=(outage coldstart mqtt mqttcold)
for s in "${SCENARIOS[@]}"; do
  declare -F "scenario_$s" >/dev/null || { echo "unknown scenario: $s"; exit 2; }
done
check_requirements || exit 2

SUMMARY=()
for s in "${SCENARIOS[@]}"; do
  OUT="$OUTPUT_DIR/$s"; rm -rf "$OUT"; mkdir -p "$OUT/state"
  echo "=== $s  (logs: $OUT)"
  before=$FAILURES
  write_config; start_broker || exit 1
  "scenario_$s"
  stop_all
  if [ "$FAILURES" -eq "$before" ]; then SUMMARY+=("PASS $s"); else SUMMARY+=("FAIL $s"); fi
done
echo "=== summary"; printf '   %s\n' "${SUMMARY[@]}"
[ "$FAILURES" -eq 0 ]
