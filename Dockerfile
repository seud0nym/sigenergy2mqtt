FROM python:3.14-alpine3.23
# CVE-2026-27171 | Update zlib in-layer while keeping the pinned base image.
RUN set -eux; \
    apk update --no-cache; \
    apk upgrade --no-cache zlib; \
    zlib_version="$(apk info -e -v zlib | cut -d- -f2-)"; \
    apk version -t "$zlib_version" "1.3.1-r2" | grep -qv '<'
# SNYK-ALPINE323-XZ-10568945 | Update xz/xz-libs in-layer while keeping the pinned base image.
RUN set -eux; \
    apk update --no-cache; \
    apk upgrade --no-cache xz xz-libs; \
    xz_version="$(apk info -e -v xz | sed 's/^xz-//')"; \
    xz_libs_version="$(apk info -e -v xz-libs | sed 's/^xz-libs-//')"; \
    [ -z "$xz_version" ] || apk version -t "$xz_version" "5.8.1-r0" | grep -qv '<'; \
    [ -z "$xz_libs_version" ] || apk version -t "$xz_libs_version" "5.8.1-r0" | grep -qv '<'

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import json,time,pathlib; p=pathlib.Path('/tmp/sigenergy2mqtt-health.json'); d=json.loads(p.read_text()) if p.exists() else {}; ok=d.get('timestamp',0) >= int(time.time())-120 and d.get('mqtt_connected') is True and d.get('modbus_connected') is True; raise SystemExit(0 if ok else 1)"

CMD [ "sigenergy2mqtt" ]
