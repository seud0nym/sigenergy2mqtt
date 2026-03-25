FROM python:3.14.3-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --no-cache-dir ./sigenergy2mqtt*.whl

CMD [ "sigenergy2mqtt" ]