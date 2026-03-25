FROM python:3.14.3-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN bash scripts/dependencies

EXPOSE 502

CMD ["python", "/app/tests/utils/modbus_test_server.py"]
