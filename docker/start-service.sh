#!/bin/sh
# Prepare the database and say whether the GitHub App must be registered, read all
# installations regularly, then serve: nginx on $PORT in front of gunicorn on 127.0.0.1:8000.
set -e
# nginx first: while the database is prepared, it answers with docker/starting.html
sed "s/LISTEN_PORT/${PORT}/g" /app/docker/nginx.conf > /tmp/nginx.conf
nginx -c /tmp/nginx.conf
# migrates; without a GitHub App it prints where to register it, with the setup code
python manage.py prepare
# webhooks can be lost while the site is down: read every installation after the start and
# then every SYNC_HOURS hours
(sleep 30; while true; do python manage.py sync_repositories || true;
  sleep $(( ${SYNC_HOURS:-6} * 3600 )); done) &
exec gunicorn pycal_dashboard.wsgi -w "$WORKERS" --threads "$THREADS" -b "127.0.0.1:8000" --access-logfile -
