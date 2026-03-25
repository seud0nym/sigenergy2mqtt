FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir .

EXPOSE 502

CMD ["python", "tests/utils/modbus_test_server.py"]
