FROM python:3-alpine

RUN pip3 install kopf kubernetes ruamel.yaml
ADD . /app

CMD kopf run /app/endpoints_controller/svc.py