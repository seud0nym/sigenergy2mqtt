FROM python:3.14-alpine3.24

# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257375
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257376
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257380
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257381
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257382
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257384
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257388
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257390
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257391
# https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-19257392
RUN apk add --update --no-cache openssl

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8502/health', timeout=4)"

CMD [ "sigenergy2mqtt" ]
