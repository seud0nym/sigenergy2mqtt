# Docker Installation

`sigenergy2mqtt` is available via a Docker image from both Docker Hub and ghcr.io. 

## Configuration

The image can be configured by using [environment variables](../../README.md#environment-variables), or by placing your [configuration file](../../README.md#configuration-file) in the root of the `/data` volume.

## Execution

> [!IMPORTANT]
> You must set the TZ variable to your local time zone, _especially_ if you are going to enable upload to PVOutput. (Thanks to @gyrex for this tip https://github.com/seud0nym/sigenergy2mqtt/discussions/22.)

Running the image is straightforward:

```bash
docker run -it \
    -e TZ=Australia/Melbourne \
    -e SIGENERGY2MQTT_MQTT_BROKER=192.168.0.1 \
    -e SIGENERGY2MQTT_MQTT_USERNAME=user \
    -e SIGENERGY2MQTT_MQTT_PASSWORD=password \
    -v /data:/data \
    seud0nym/sigenergy2mqtt:latest
```

> [!IMPORTANT]
> You must provide persistent storage via the `-v` option to preserve the state  of calculated accumulation sensors across executions. You can also place your [configuration file](../../README.md#configuration-file) in the root of this directory, rather than configuring via environment variables.


If you want to utilise the auto-discovery feature to find existing Sigenergy Modbus devices and device IDs, you _must_ specify host networking. e.g.

```bash
docker run -it \
    --network host \
    -e TZ=Australia/Melbourne \
    -e SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY=once \
    -e SIGENERGY2MQTT_MQTT_BROKER=192.168.0.1 \
    -e SIGENERGY2MQTT_MQTT_USERNAME=user \
    -e SIGENERGY2MQTT_MQTT_PASSWORD=password \
    -v /data:/data \
    seud0nym/sigenergy2mqtt:latest
```


## Docker Compose

`docker-compose` users can find an example configuration file at [`docker-compose.yaml`](docker-compose.yaml).
