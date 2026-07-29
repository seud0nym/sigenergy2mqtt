FROM python:3.14-alpine3.24

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import json,sys,urllib.request as u; sys.exit(0 if json.loads(u.urlopen('http://127.0.0.1:8083/health', timeout=4).read()).get('status') == 'healthy' else 1)"

CMD [ "sigenergy2mqtt" ]
