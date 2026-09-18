# Vendored cloud client tests

These tests were moved from `solidfox/sigenergy-cloud` version 0.1.7 and
adapted to exercise the namespaced copy maintained by sigenergy2mqtt.
The local `conftest.py` temporarily bridges the published `aioresponses`
release to the `stream_writer` argument required by aiohttp 3.14. Remove the
shim once `aioresponses` publishes support for aiohttp 3.14.

Keep these tests aligned with changes made directly under
`src/sigenergy2mqtt/cloud/vendor/solidfox/sigenergy_cloud/`.
