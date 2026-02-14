FROM python:3.15-rc-alpine3.22

WORKDIR /usr/src/app

COPY dist/sigenergy2mqtt*.whl .
RUN pip install --root-user-action=ignore ./sigenergy2mqtt*.whl

CMD [ "sigenergy2mqtt" ]