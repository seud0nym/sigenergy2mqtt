# Docker Installation

`sigenergy2mqtt` is available via a Docker image from both Docker Hub and ghcr.io. 

## Configuration

The image can be configured by using [environment variables](../configuration/ENV.md), or by placing your [configuration file](../configuration/FILE.md) in the root of the `/data` volume.

## Execution
Running the image is straightforward:

```bash
docker run -it \
    --network host \
    -p 8502:8502 \
    -e TZ=Australia/Melbourne \
    -e SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY=once \
    -e SIGENERGY2MQTT_MQTT_BROKER=192.168.0.1 \
    -e SIGENERGY2MQTT_MQTT_USERNAME=user \
    -e SIGENERGY2MQTT_MQTT_PASSWORD=password \
    -v /data:/data \
    seud0nym/sigenergy2mqtt:latest
```

> [!IMPORTANT]
> You must provide persistent storage via the `-v` option to preserve the state of some sensors across executions. You can also place your [configuration file](../configuration/FILE.md) in the root of this directory (i.e. `/data/sigenergy2mqtt.yaml`), rather than configuring via environment variables.

> [!TIP]
> You must set the TZ variable to your local time zone, _especially_ if you are going to enable upload to PVOutput. (Thanks to @gyrex for this tip(https://github.com/seud0nym/sigenergy2mqtt/discussions/22).)

### Diagnostics and Solar Dashboard

`sigenergy2mqtt` provides a simple diagnostics web server accessible on port 8502 where system metrics can be found. There is also a simple Solar & Battery dashboard available via the diagnostics Web UI.

You can control access to the diagnostics and solar dashboards by limiting the IP addresses that can access it via the [`SIGENERGY2MQTT_DIAGNOSTICS_ALLOWED_IPS`](../configuration/README.md#opt_diagnostics_allowed_ips) environment variable.

## Pre-release (beta) images

If you want to test pre-release builds, use the `beta` tag explicitly:

```bash
docker run -it \
    -e TZ=Australia/Melbourne \
    -e SIGENERGY2MQTT_MQTT_BROKER=192.168.0.1 \
    -e SIGENERGY2MQTT_MQTT_USERNAME=user \
    -e SIGENERGY2MQTT_MQTT_PASSWORD=password \
    -v /data:/data \
    seud0nym/sigenergy2mqtt:beta
```

`latest` remains reserved for stable releases.

> [!WARNING]
> Running both stable and beta versions simultaneously is not recommended. The container can _not_ detect or prevent this.
> It is up to _you_ to ensure that you do not run both the stable and beta releases simultaneously!

## Docker Compose

`docker-compose` users can find an example configuration file in [`docker-compose.yaml`](docker-compose.yaml).
