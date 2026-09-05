FROM python:3.14-alpine3.24

# Update all available packages to mitigate vulnerabilities
RUN apk upgrade --update --no-cache --available

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8502/health', timeout=4)"

CMD [ "sigenergy2mqtt" ]
