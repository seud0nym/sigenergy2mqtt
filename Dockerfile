FROM python:3-slim

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore --upgrade pip ./sigenergy2mqtt*.whl

CMD [ "sigenergy2mqtt" ]