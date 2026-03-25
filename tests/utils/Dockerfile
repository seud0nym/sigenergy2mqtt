FROM python:3.14.3-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    paho-mqtt==2.1.0 \
    psutil==7.2.2 \
    pydantic-settings==2.13.1 \
    pymodbus==3.12.1 \
    requests==2.32.5 \
    ruamel.yaml==0.19.1

COPY sigenergy2mqtt /app/sigenergy2mqtt
COPY tests/utils /app/tests/utils

EXPOSE 502

CMD ["python", "/app/tests/utils/modbus_test_server.py"]
