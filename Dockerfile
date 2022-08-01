FROM ubuntu:20.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por python3-pip

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY . /opt/ru/
WORKDIR /opt/ru

CMD python3 manage.py collectstatic --noinput \
    && python3 manage.py migrate \
    && gunicorn \
        --workers 4 \
        --log-level=debug \
        --error-logfile=/var/run/share/error.log \
        --bind=unix:/var/run/share/gunicorn.sock \
        ru_api.wsgi
