FROM python:3.14-alpine3.23
# CVE-2026-27171 | CVSS 5.5 – Medium
RUN apk upgrade --no-cache zlib

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN apk add --no-cache bash && \
    /app/scripts/dependencies --install-only --skip-build-deps
RUN echo "$(date +"%Y-%m-%dT%H:%M:%S%z")" > /app/build_date.txt

EXPOSE 502

CMD ["python", "/app/tests/utils/modbus_test_server.py"]
