#!/bin/sh
# Prepare the database and say whether the GitHub App must be registered, then serve: nginx on $PORT in front of gunicorn on 127.0.0.1:8000.
set -e
# nginx first: while the database is prepared, it answers with docker/starting.html
sed "s/LISTEN_PORT/${PORT}/g" /app/docker/nginx.conf > /tmp/nginx.conf
nginx -c /tmp/nginx.conf
# migrates; without a GitHub App it prints where to register it, with the setup code
python manage.py prepare
# the installations of the GitHub App: a new version may need more permissions, which the
# people of each installation are told by email
(python manage.py check_installations || true) &
exec gunicorn pycal_dashboard.wsgi -w "$WORKERS" --threads "$THREADS" -b "127.0.0.1:8000" --access-logfile -
