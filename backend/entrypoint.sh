#!/bin/sh
set -e

python manage.py init_extensions
python manage.py makemigrations agent --noinput
python manage.py migrate --noinput
python manage.py collectstatic --no-input

exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2 --timeout 900
