FROM python:3-alpine

RUN pip3 install kopf kubernetes ruamel.yaml
ADD . /app
WORKDIR /app
RUN pip install .
CMD kopf run --standalone -m endpoints_controller.kopf --debug