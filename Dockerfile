FROM python:3.14-alpine3.23
# CVE-2026-27171 | CVSS 5.5 – Medium
RUN apk upgrade --no-cache zlib

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import json,time,pathlib; p=pathlib.Path('/tmp/sigenergy2mqtt-health.json'); d=json.loads(p.read_text()) if p.exists() else {}; ok=d.get('timestamp',0) >= int(time.time())-120 and d.get('mqtt_connected') is True and d.get('modbus_connected') is True; raise SystemExit(0 if ok else 1)"

CMD [ "sigenergy2mqtt" ]
