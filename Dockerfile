FROM ubuntu:20.04

RUN apt-get update \
    && apt-get install -y wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por python3-pip google-chrome-stable \
    fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst \
    fonts-freefont-ttf libxss1 \
    && rm -rf /var/lib/apt/lists/*

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
