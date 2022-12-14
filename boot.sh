#!/bin/sh
# this script is used to boot a Docker container
source venv/bin/activate
while true; do
    flask db upgrade
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo Deploy command failed, retrying in 5 secs...
    sleep 5
done
flask translate compile
exec gunicorn -b :5000 --worker-tmp-dir /dev/shm --workers=2 --threads=4 --worker-class=gthread --access-logfile - --error-logfile - gsonline:app
