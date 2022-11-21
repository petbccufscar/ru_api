FROM python:3.9.15-slim-bullseye

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
