InfluxDB integration
--------------------

Example `influxdb` configuration block for `sigenergy2mqtt`:

```yaml
influxdb:
  enabled: true
  host: 127.0.0.1
  port: 8086
  database: sigenergy
  username: user
  password: secret_or_token
  include:
    - temperature
  exclude:
    - debug_sensor
```

Notes:
- The service will try to detect and use the official `influxdb-client` when available (token-based writes).
- If the client is not available the service falls back to HTTP write endpoints for v2 and v1 (and will attempt to create DB/bucket where permitted).
- `include` and `exclude` use the same substring-matching convention as `sensor_overrides`: they match substrings against the sensor class name, `object_id`, or `unique_id`.
- Avoid running auto-discovery or long network scans when testing InfluxDB writes in CI.
