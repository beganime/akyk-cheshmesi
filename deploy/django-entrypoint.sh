#!/usr/bin/env sh
set -e

cd /app/backend/django_app

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py warm_redis_cache || true
python manage.py check --deploy || true

case "$1" in
  gunicorn)
    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers ${GUNICORN_WORKERS:-4} \
      --timeout ${GUNICORN_TIMEOUT:-60} \
      --access-logfile - \
      --error-logfile -
    ;;
  celery)
    exec celery -A config worker --loglevel=${CELERY_LOGLEVEL:-INFO}
    ;;
  stream-saver)
    exec python manage.py consume_message_stream
    ;;
  status-saver)
    exec python manage.py consume_message_status_stream
    ;;
  *)
    exec "$@"
    ;;
esac
