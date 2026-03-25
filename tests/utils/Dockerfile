FROM python:3.14.3-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    paho-mqtt==2.1.0 \
    psutil==7.2.2 \
    pydantic-settings==2.13.1 \
    pymodbus==3.12.1 \
    requests==2.32.5 \
    ruamel.yaml==0.19.1

COPY . /app/tests/utils
RUN git clone --depth 1 https://github.com/seud0nym/sigenergy2mqtt.git /tmp/sigenergy2mqtt \
    && cp -r /tmp/sigenergy2mqtt/sigenergy2mqtt /app/sigenergy2mqtt \
    && rm -rf /tmp/sigenergy2mqtt
RUN mkdir -p /app/tests && touch /app/tests/__init__.py

EXPOSE 502

CMD ["python", "/app/tests/utils/modbus_test_server.py"]
