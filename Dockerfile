FROM python:3.15-alpine3.24

# Update all available packages to mitigate vulnerabilities
RUN apk upgrade --update --no-cache --available

# Mitigate Snyk findings for Alpine 3.24 and Python 3.15
# - https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-22602641
# - https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-22602642
# - https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-22602643
# - https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-22602645
# - https://security.snyk.io/vuln/SNYK-ALPINE324-OPENSSL-22602647
RUN apk update && \
    apk add --no-cache 'openssl>=3.5.9-r1' 'libcrypto3>=3.5.9-r1' 'libssl3>=3.5.9-r1'


ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8502/health', timeout=4)"

CMD [ "sigenergy2mqtt" ]
