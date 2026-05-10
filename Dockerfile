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
    xz_version="$(apk info -e -v xz | cut -d- -f2-)"; \
    xz_libs_version="$(apk info -e -v xz-libs | cut -d- -f2-)"; \
    apk version -t "$xz_version" "5.8.1-r0" | grep -qv '<'; \
    apk version -t "$xz_libs_version" "5.8.1-r0" | grep -qv '<'

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

CMD [ "sigenergy2mqtt" ]
