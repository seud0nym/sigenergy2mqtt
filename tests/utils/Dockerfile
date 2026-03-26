FROM python:3.14.3-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip --root-user-action=ignore --no-cache-dir && bash scripts/dependencies --install-only --skip-build-deps
RUN echo "$(date +"%Y-%m-%dT%H:%M:%S%z")" > /app/build_date.txt

EXPOSE 502

CMD ["python", "/app/tests/utils/modbus_test_server.py"]
