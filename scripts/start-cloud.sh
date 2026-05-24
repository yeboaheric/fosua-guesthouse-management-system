#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput

gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WEB_CONCURRENCY:-3} \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
