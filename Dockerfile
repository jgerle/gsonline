FROM python:3.9-alpine

RUN adduser -D gsonline

WORKDIR /home/gsonline

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev libffi-dev openssl-dev git

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/python -m pip install --upgrade pip
RUN venv/bin/pip install wheel
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql

RUN apk del .build-deps gcc musl-dev python3-dev libffi-dev openssl-dev git

COPY app app
COPY migrations migrations
COPY gsonline.py config.py boot.sh ./
RUN chmod a+x boot.sh

ENV FLASK_APP gsonline.py

RUN chown -R gsonline:gsonline ./
USER gsonline

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
