# Docker Installation

`sigenergy2mqtt` is available via a Docker image from both Docker Hub and ghcr.io. 

## Configuration

The image can be configured by using [environment variables](../../README.md#environment-variables), or by placing your [configuration file](../../README.md#configuration-file) in the root of the `/data` volume.

## Execution

Running the image is straightforward:

```bash
docker run -it \
    -e SIGENERGY2MQTT_MQTT_BROKER=192.168.0.1 \
    -e SIGENERGY2MQTT_MQTT_USERNAME=user \
    -e SIGENERGY2MQTT_MQTT_PASSWORD=password \
    -v /data:/data \
    seud0nym/sigenergy2mqtt:latest
```

> [!IMPORTANT]
> You must provide persistent storage via the `-v` option to preserve the state  of calculated accumulation sensors across executions. You can also place your [configuration file](../../README.md#configuration-file) in the root of this directory, rather than configuring via environment variables.

## Docker Compose

`docker-compose` users can find an example configuration file at [`docker-compose.yaml`](docker-compose.yaml).
