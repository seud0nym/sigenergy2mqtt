FROM python:3.14-alpine3.23

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --break-system-packages --no-cache-dir ./sigenergy2mqtt*.whl

CMD [ "sigenergy2mqtt" ]