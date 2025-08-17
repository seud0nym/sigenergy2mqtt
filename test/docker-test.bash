#!/bin/bash

cd "$(cd $(dirname $0)/..; pwd)"

python3 -m build || exit
python3 -m twine check dist/* || exit
docker buildx build --platform linux/amd64 --load -t sigenergy2mqtt:latest . || exit
docker run -it \
    -e TZ=Australia/Melbourne \
    -e SIGENERGY2MQTT_LOG_LEVEL=DEBUG \
    -e SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY=once \
    -v /var/lib/sigenergy2mqtt:/data \
    --network host \
    sigenergy2mqtt:latest

